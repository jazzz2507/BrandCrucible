import os
import json
import asyncio
import time
import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse
from collections import defaultdict

from store import store
from llm import call_stage_llm, LLMError
from schemas import (
    DiscoverSchema, PositionSchema, ShapeSchema, VisualizeSchema,
    ChallengeSchema, DeliverSchema, ConsistencySchema, DeliverDiscovery, DeliverPositioning, DeliverBrandShape, DeliverVisualIdentity
)

load_dotenv()

PORT = int(os.environ.get("PORT", 8000))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(title="BrandCrucible API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IdeaInput(BaseModel):
    idea: str

class StagePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "BrandCrucible API"}

@app.get("/health")
def health():
    return {"status": "ok"}

RATE_LIMIT_SESSIONS_PER_HOUR = int(os.environ.get("RATE_LIMIT_SESSIONS_PER_HOUR", 5))
ip_sessions = defaultdict(list)

def check_rate_limit(request: Request):
    ip = request.headers.get("x-forwarded-for")
    if ip:
        ip = ip.split(",")[0].strip()
    else:
        ip = request.client.host
        
    now = time.time()
    hour_ago = now - 3600
    
    # cleanup old
    ip_sessions[ip] = [t for t in ip_sessions[ip] if t > hour_ago]
    
    if len(ip_sessions[ip]) >= RATE_LIMIT_SESSIONS_PER_HOUR:
        oldest = ip_sessions[ip][0]
        retry_after = int(3600 - (now - oldest))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after)}
        )
    
    ip_sessions[ip].append(now)

MAX_CONCURRENT_PIPELINES = int(os.environ.get("MAX_CONCURRENT_PIPELINES", 2))
MAX_QUEUE_LENGTH = int(os.environ.get("MAX_QUEUE_LENGTH", 5))
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", 24))

pipeline_semaphore = None
queue_waiters = 0

def get_pipeline_semaphore():
    global pipeline_semaphore
    if pipeline_semaphore is None:
        pipeline_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PIPELINES)
    return pipeline_semaphore

async def cleanup_sessions_task():
    while True:
        await asyncio.sleep(3600)
        now = datetime.datetime.utcnow()
        ttl_delta = datetime.timedelta(hours=SESSION_TTL_HOURS)
        to_delete = []
        for sid, sess in store._store.items():
            if sid == "golden-demo": continue
            if sess.status in ("complete", "error") and now - sess.created_at > ttl_delta:
                to_delete.append(sid)
        for sid in to_delete:
            del store._store[sid]
            store._conditions.pop(sid, None)
            store._tasks.pop(sid, None)

@app.on_event("startup")
async def startup_event():
    get_pipeline_semaphore()
    asyncio.create_task(cleanup_sessions_task())

@app.post("/api/interview/start")
def start_interview(payload: IdeaInput, request: Request):
    idea = payload.idea.strip()
    if len(idea) < 10:
        raise HTTPException(status_code=422, detail="Idea must be at least 10 characters.")
    if len(idea) > int(os.environ.get("MAX_IDEA_CHARS", 500)):
        raise HTTPException(status_code=422, detail="Idea must be less than MAX_IDEA_CHARS characters.")
        
    check_rate_limit(request)
    
    session = store.create(idea=idea)
    return {
        "sessionId": session.session_id,
        "question": f"Interesting idea: '{idea}'. Who is your primary target customer?"
    }

@app.get("/api/brand-kit/{session_id}")
def get_brand_kit(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.status == "complete" and "Deliver" in session.stage_outputs:
        return session.stage_outputs["Deliver"]
        
    return {
        "sessionId": session_id,
        "stage": "Deliver",
        "brand": {
            "name": "BrandCrucible",
            "tagline": "Forge distinct identities, incinerate clichés",
            "positioning": "The adversarial branding engine for ambitious founders",
            "palette": ["#0F172A", "#38BDF8", "#F43F5E"],
            "typography": {
                "heading": "Space Grotesk",
                "body": "Inter"
            }
        },
        "challengeReport": {
            "clicheScore": 14,
            "distinctivenessScore": 92,
            "verdict": "Passed challenger review"
        }
    }

STAGES = ["Discover", "Position", "Shape", "Visualize", "Challenge", "Deliver", "ConsistencyCheck"]

prompts = {
    "Discover": "You are the Discover agent. Identify the startup idea's likely primary and secondary audiences, the core problem, constraints, assumptions, and unanswered questions. This stage is research framing only: do not propose names, taglines, brand voice, positioning, or visual identity. Be specific to the supplied idea and distinguish known facts from assumptions. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nIdea: {idea}",
    "Position": "You are the Position agent. Define a clear value proposition, differentiators, competitive angle, and positioning statement using the idea and discovery context. This stage is strategic positioning only: do not generate names, taglines, personality, voice, or visual directions. Be specific to this idea and audience, avoiding generic claims. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nIdea: {idea}\nDiscovery: {discovery}",
    "Shape": "You are the Shape agent. Create candidate brand names with rationale and risk, personality traits, tagline options, and a concise voice description using the positioning context. This stage handles verbal identity only: do not revisit discovery, rewrite positioning, or suggest colors, typography, or imagery. Make ideas memorable and specific to this startup, not generic. If revision guidance is supplied, address it directly. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nIdea: {idea}\nPositioning: {positioning}\n{revision_guidance}",
    "Visualize": "You are the Visualize agent. Propose a cohesive color, typography, and imagery direction, with rationale grounded in the brand strategy and personality. This stage is visual direction only: do not invent names, taglines, or revise the positioning. Be concrete and specific to this brand rather than relying on generic design adjectives. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nIdea: {idea}\nPositioning: {positioning}\nShape: {shape}",
    "Challenge": "You are the Challenge agent. Critically assess one supplied brand item against its positioning context. Score cliche risk, distinctiveness, audience fit, and consistency with positioning from 0 to 10; for cliche risk, a higher score means lower risk / more original. Give actionable feedback and a pass, revise, or reject verdict. Do not generate a replacement or change the strategy. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nItem: {item}\nPositioning: {positioning}",
    "Deliver": "You are the Deliver agent. Compile the validated prior-stage decisions into one clean, exportable brand kit using the supplied chosen name, tagline, discovery, positioning, verbal identity, and visual direction. This stage compiles only: do not invent missing strategy or add new creative directions. Keep every field specific and faithful to supplied outputs. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nName: {name}\nTagline: {tagline}\nDiscovery: {discovery}\nPositioning: {positioning}\nShape: {shape}\nVisual: {visual}",
    "ConsistencyCheck": "You are the Consistency Check agent. Critically evaluate the final compiled brand kit as a whole against the original idea and prior stage decisions. Check specifically:\n1. Does the final brand name match the original idea?\n2. Does the tagline directly support the positioning?\n3. Do the brand personality traits match the discovered audience and problem?\n4. Does the visual identity fit the brand personality and positioning?\n5. Is there overall coherence across name, tagline, positioning, voice, and visual identity?\n6. Has the brand drifted from the core problem and audience of the original idea?\n\nEvaluate issues (if any) with area, description, and severity (\"minor\" | \"major\"). Provide an overall_score from 0 to 10, a boolean is_consistent (true if score >= 7 and no unaddressed major disconnects), and a concise summary (one or two sentences). Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nIdea: {idea}\nBrand Kit: {brand_kit}"
}

schemas = {
    "Discover": DiscoverSchema,
    "Position": PositionSchema,
    "Shape": ShapeSchema,
    "Visualize": VisualizeSchema,
    "Challenge": ChallengeSchema,
    "Deliver": DeliverSchema,
    "ConsistencyCheck": ConsistencySchema
}

def average(scores: Dict[str, float]) -> float:
    return sum(scores.values()) / len(scores)

def needs_revision(result: ChallengeSchema) -> bool:
    scores = result.scores.model_dump()
    avg = average(scores)
    return avg < 6.0 or any(v < 4.0 for v in scores.values()) or result.verdict != 'pass'

def rank_by_score(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def mean(scores):
        if not scores: return -1
        return sum(scores.values()) / len(scores)
        
    def cmp(a, b):
        is_pass_a = 1 if a.get("verdict") == 'pass' else 0
        is_pass_b = 1 if b.get("verdict") == 'pass' else 0
        if is_pass_a != is_pass_b:
            return is_pass_b - is_pass_a
        return mean(b.get("scores", {})) - mean(a.get("scores", {}))

    import functools
    return sorted(items, key=functools.cmp_to_key(cmp))

def select_candidate(ranked_items: List[Dict[str, Any]], fallback_candidates: List[Any], fallback_key: str = "name") -> str:
    if ranked_items:
        return ranked_items[0].get("value", "")
    if fallback_candidates:
        cand = fallback_candidates[0]
        if isinstance(cand, dict):
            return cand.get(fallback_key, "Unknown")
        elif isinstance(cand, str):
            return cand
        elif hasattr(cand, fallback_key):
            return getattr(cand, fallback_key, "Unknown")
    return "Unknown"

MAX_REVISIONS = 2

async def run_challenger_item(
    cand: Dict[str, str],
    idea: str,
    positioning: str,
    session: Optional[BaseModel] = None,
    call_llm_fn=None,
    sleep_fn=None
) -> Dict[str, Any]:
    if call_llm_fn is None:
        call_llm_fn = call_stage_llm
    if sleep_fn is None:
        sleep_fn = asyncio.sleep
    item_val = cand["value"]
    history = []
    best = None
    revision = 0
    
    while revision <= MAX_REVISIONS:
        prompt = prompts["Challenge"].format(item=item_val, positioning=positioning)
        res = await call_llm_fn("Challenge", prompt, ChallengeSchema, session)
        
        res_dump = res.model_dump()
        history.append(res_dump)
        
        scores_dump = res.scores.model_dump()
        current_avg = average(scores_dump)
        
        if best is None or current_avg > average(best["result"]["scores"]):
            best = {"value": item_val, "result": res_dump, "attempt": revision}
            
        if not needs_revision(res):
            break
            
        if revision < MAX_REVISIONS:
            # Generate replacement
            rev_guide = f"Revision guidance: The previous candidate '{item_val}' failed. Feedback: {res.feedback}. Provide a better alternative."
            shape_prompt = prompts["Shape"].format(idea=idea, positioning=positioning, revision_guidance=rev_guide)
            new_shape = await call_llm_fn("Shape", shape_prompt, ShapeSchema, session)
            if cand["type"] == "name":
                item_val = new_shape.candidates[0].name
            else:
                item_val = new_shape.tagline_options[0]
            await sleep_fn(4.5)
        revision += 1
        
    exhausted = False
    best_res = ChallengeSchema.model_validate(best["result"])
    if needs_revision(best_res) and len(history) == MAX_REVISIONS + 1:
        exhausted = True
        
    final_verdict = 'revise' if needs_revision(best_res) else 'pass'
    best["result"]["verdict"] = final_verdict
    
    return {
        "type": cand["type"],
        "value": best["value"],
        "scores": best["result"]["scores"],
        "verdict": final_verdict,
        "feedback": best["result"]["feedback"],
        "history": history,
        "exhausted_revisions": exhausted
    }

async def run_stage(stage: str, session: BaseModel):
    use_mock = os.environ.get("USE_MOCK_LLM", "true").lower() not in ("0", "false", "no")
    if use_mock:
        await asyncio.sleep(1)
        mock_output = {"mock": f"data for {stage}"}
        if stage == "Deliver":
            mock_output = {
                "sessionId": session.session_id,
                "stage": "Deliver",
                "brand": {
                    "name": "BrandCrucible",
                    "tagline": "Forge distinct identities, incinerate clichés",
                    "positioning": "The adversarial branding engine for ambitious founders",
                    "palette": ["#0F172A", "#38BDF8", "#F43F5E"],
                    "typography": {
                        "heading": "Space Grotesk",
                        "body": "Inter"
                    }
                },
                "challengeReport": {
                    "clicheScore": 14,
                    "distinctivenessScore": 92,
                    "verdict": "Passed challenger review"
                }
            }
        store.update_stage(session.session_id, stage, mock_output)
        return mock_output

    idea = session.idea
    output = None
    
    if stage == "Discover":
        prompt = prompts["Discover"].format(idea=idea)
        res = await call_stage_llm(stage, prompt, DiscoverSchema, session)
        output = res.model_dump()
    elif stage == "Position":
        discovery = json.dumps(session.stage_outputs.get("Discover", {}))
        prompt = prompts["Position"].format(idea=idea, discovery=discovery)
        res = await call_stage_llm(stage, prompt, PositionSchema, session)
        output = res.model_dump()
    elif stage == "Shape":
        positioning = json.dumps(session.stage_outputs.get("Position", {}))
        prompt = prompts["Shape"].format(idea=idea, positioning=positioning, revision_guidance="")
        res = await call_stage_llm(stage, prompt, ShapeSchema, session)
        output = res.model_dump()
    elif stage == "Visualize":
        positioning = json.dumps(session.stage_outputs.get("Position", {}))
        shape = json.dumps(session.stage_outputs.get("Shape", {}))
        prompt = prompts["Visualize"].format(idea=idea, positioning=positioning, shape=shape)
        res = await call_stage_llm(stage, prompt, VisualizeSchema, session)
        output = res.model_dump()
    elif stage == "Challenge":
        positioning = json.dumps(session.stage_outputs.get("Position", {}))
        shape_output = session.stage_outputs.get("Shape", {})
        
        candidates = []
        for c in shape_output.get("candidates", []):
            candidates.append({"type": "name", "value": c["name"]})
        for t in shape_output.get("tagline_options", []):
            candidates.append({"type": "tagline", "value": t})
        challenge_results = []
        for cand in candidates:
            res_item = await run_challenger_item(cand, idea, positioning, session)
            challenge_results.append(res_item)
            await asyncio.sleep(4.5)
            
        output = {"items": challenge_results}
        
    elif stage == "Deliver":
        challenge_output = session.stage_outputs.get("Challenge", {})
        shape_output = session.stage_outputs.get("Shape", {})
        
        items = challenge_output.get("items", [])
        names = [i for i in items if i["type"] == "name"]
        taglines = [i for i in items if i["type"] == "tagline"]
        
        ranked_names = rank_by_score(names)
        ranked_taglines = rank_by_score(taglines)
        
        chosen_name = select_candidate(ranked_names, shape_output.get("candidates", []), fallback_key="name")
        chosen_tagline = select_candidate(ranked_taglines, shape_output.get("tagline_options", []), fallback_key="")
        
        discovery = json.dumps(session.stage_outputs.get("Discover", {}))
        positioning = json.dumps(session.stage_outputs.get("Position", {}))
        shape = json.dumps(session.stage_outputs.get("Shape", {}))
        visual = json.dumps(session.stage_outputs.get("Visualize", {}))
        
        prompt = prompts["Deliver"].format(name=chosen_name, tagline=chosen_tagline, discovery=discovery, positioning=positioning, shape=shape, visual=visual)
        res = await call_stage_llm(stage, prompt, DeliverSchema, session)
        output = res.model_dump()
        
    elif stage == "ConsistencyCheck":
        brand_kit = json.dumps(session.stage_outputs.get("Deliver", {}))
        prompt = prompts["ConsistencyCheck"].format(idea=idea, brand_kit=brand_kit)
        res = await call_stage_llm(stage, prompt, ConsistencySchema, session)
        output = res.model_dump()

    store.update_stage(session.session_id, stage, output)
    return output

async def run_pipeline_task(session_id: str):
    session = store.get(session_id)
    if not session:
        return
        
    is_golden = session_id == "golden-demo"
    timeout = int(os.environ.get("PIPELINE_TIMEOUT_SECONDS", 600))
    
    async def _execute():
        global queue_waiters
        if not is_golden:
            sem = get_pipeline_semaphore()
            if sem.locked():
                if queue_waiters >= MAX_QUEUE_LENGTH:
                    await store.add_event(session_id, {
                        "event": "error",
                        "data": json.dumps({"message": "Server is busy. Try the demo session."})
                    })
                    store.set_status(session_id, "error")
                    return
                
                queue_waiters += 1
                await store.add_event(session_id, {
                    "event": "queued",
                    "data": json.dumps({"sessionId": session_id, "position": queue_waiters})
                })
                async with sem:
                    queue_waiters -= 1
                    await _do_run()
            else:
                async with sem:
                    await _do_run()
        else:
            await _do_run()

    async def _do_run():
        try:
            total = len(STAGES)
            for i, stage in enumerate(STAGES):
                await store.add_event(session_id, {
                    "event": "stage_start",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "stage": stage,
                        "index": i,
                        "total": total
                    })
                })
                
                if is_golden:
                    await asyncio.sleep(0.4)
                    output = session.stage_outputs.get(stage, {})
                else:
                    output = await run_stage(stage, session)
                
                await store.add_event(session_id, {
                    "event": "stage_complete",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "stage": stage,
                        "index": i,
                        "total": total,
                        "output": output
                    })
                })
                
            store.set_status(session_id, "complete")
            
            await store.add_event(session_id, {
                "event": "done",
                "data": json.dumps({
                    "brandKit": session.stage_outputs.get("Deliver", {}),
                    "consistencyCheck": session.stage_outputs.get("ConsistencyCheck", {}),
                    "trace": session.trace
                })
            })
            
        except Exception as e:
            store.set_status(session_id, "error")
            await store.add_event(session_id, {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            })

    try:
        if is_golden:
            await _execute()
        else:
            await asyncio.wait_for(_execute(), timeout=timeout)
    except asyncio.TimeoutError:
        store.set_status(session_id, "error")
        await store.add_event(session_id, {
            "event": "error",
            "data": json.dumps({"message": "Pipeline timed out"})
        })
    except Exception as e:
        store.set_status(session_id, "error")
        await store.add_event(session_id, {
            "event": "error",
            "data": json.dumps({"message": str(e)})
        })


@app.get("/api/pipeline/stream/{session_id}")
async def stream_pipeline(session_id: str, request: Request):
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.status == "created":
        store.set_status(session_id, "running")
        task = asyncio.create_task(run_pipeline_task(session_id))
        store._tasks[session_id] = task
        
    last_event_id = request.headers.get("Last-Event-ID")
    start_index = int(last_event_id) + 1 if last_event_id and last_event_id.isdigit() else 0

    async def event_generator():
        idx = start_index
        cond = store.get_condition(session_id)
        
        while True:
            if await request.is_disconnected():
                break
                
            while idx < len(session.events):
                ev = session.events[idx]
                yield {
                    "event": ev["event"],
                    "data": ev["data"],
                    "id": str(idx)
                }
                if ev["event"] in ("done", "error"):
                    return
                idx += 1
                
            if session.status in ("complete", "error") and idx >= len(session.events):
                return
                
            async with cond:
                await cond.wait()

    return EventSourceResponse(
        event_generator(),
        ping=15
    )

@app.get("/api/trace/{session_id}")
def get_trace(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"sessionId": session_id, "trace": session.trace}

@app.get("/api/export/{session_id}")
def export_brand_kit(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "complete":
        raise HTTPException(status_code=409, detail="Session is not complete")
    kit = session.stage_outputs.get("Deliver", {})
    brand_name = kit.get("brand_name", "Brand Kit")
    tagline = kit.get("tagline", "")
    pos = kit.get("positioning", {})
    
    lines = [f"# {brand_name}", "", f"> {tagline}", "",
             "## Positioning", "", pos.get("positioning_statement", ""), ""]
             
    if kit.get("discovery") and kit["discovery"].get("audience"):
        lines += ["## Audience", "", f"Primary: {kit['discovery']['audience'].get('primary', '')}", ""]
        
    visual = kit.get("visual_identity", {})
    if visual.get("color_direction"):
        lines += ["## Visual Identity", "", f"Colors: {visual['color_direction']}", ""]
        
    return Response("\n".join(lines), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="brand-kit-{session_id}.md"'})
