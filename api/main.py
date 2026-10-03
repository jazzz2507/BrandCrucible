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
from contextlib import asynccontextmanager

import re
import difflib
from store import store
from llm import call_stage_llm, LLMError
from schemas import (
    DiscoverSchema, PositionSchema, ShapeSchema, VisualizeSchema,
    ChallengeSchema, DeliverSchema, ConsistencySchema, DeliverDiscovery, DeliverPositioning, DeliverBrandShape, DeliverVisualIdentity, ColorSwatch
)

load_dotenv()

PORT = int(os.environ.get("PORT", 8000))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    use_mock = os.environ.get("USE_MOCK_LLM", "true").lower() not in ("0", "false", "no")
    if not use_mock and not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY must be set when USE_MOCK_LLM=false")
    get_pipeline_semaphore()
    task = asyncio.create_task(cleanup_sessions_task())
    yield
    task.cancel()

app = FastAPI(title="BrandCrucible API", lifespan=lifespan)

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
    sem = get_pipeline_semaphore()
    running_pipelines = MAX_CONCURRENT_PIPELINES - sem._value if hasattr(sem, "_value") else 0
    if running_pipelines < 0: running_pipelines = 0
    return {"status": "ok", "running": running_pipelines, "queued": queue_waiters}

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
        now = datetime.datetime.now(datetime.timezone.utc)
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

@app.post("/api/interview/start")
def start_interview(payload: IdeaInput, request: Request):
    idea = payload.idea.strip()
    if len(idea) < 10:
        raise HTTPException(status_code=422, detail="Idea must be at least 10 characters.")
    if len(idea) > int(os.environ.get("MAX_IDEA_CHARS", 500)):
        raise HTTPException(status_code=422, detail="Idea must be less than MAX_IDEA_CHARS characters.")
        
    check_rate_limit(request)
    
    ip = request.headers.get("x-forwarded-for")
    if ip:
        ip = ip.split(",")[0].strip()
    else:
        ip = request.client.host
        
    # Cancel any running task for this IP
    for sid, sess in store._store.items():
        if sess.ip == ip and sess.status == "running":
            if sid in store._tasks:
                store._tasks[sid].cancel()
            store.set_status(sid, "error")
    
    session = store.create(idea=idea)
    session.ip = ip
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
    "Visualize": "You are the Visualize agent. Propose a cohesive color, typography, and imagery direction, with rationale grounded in the brand strategy and personality. In color_direction, explicitly define the palette naming 3 core brand colors (Primary, Secondary, Accent) alongside their exact 6-digit hex codes (e.g. 'Primary: Electric Lime (#39FF14), Secondary: Obsidian Slate (#18181B), Accent: Warm Alabaster (#F4F4F5)'). This stage is visual direction only: do not invent names, taglines, or revise the positioning. Be concrete and specific to this brand rather than relying on generic design adjectives. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nIdea: {idea}\nPositioning: {positioning}\nShape: {shape}",
    "Challenge": "You are the Challenge agent. Critically assess one supplied brand item against its positioning context. You are evaluating ONLY this exact candidate: '{item}'. Do NOT reference, compare, or critique any other candidate from earlier turns in your feedback. The 'item' (target/candidate) field in your output MUST be copied verbatim (exact character match) from this supplied item string, and your 'feedback' / explanation text must critique that exact candidate string without inventing, substituting, or hallucinating a different name or tagline. Score cliche risk, distinctiveness, audience fit, and consistency with positioning from 0 to 10; for cliche risk, a higher score means lower risk / more original. Give actionable feedback and a pass, revise, or reject verdict. Do not generate a replacement or change the strategy. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.\nItem: {item}\nPositioning: {positioning}",
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

def is_clean_pass(item: Dict[str, Any]) -> bool:
    if item.get("verdict") != "pass":
        return False
    # If it underwent revision cycles or had revise in history
    history = item.get("history", [])
    if len(history) > 1:
        return False
    if any(h.get("verdict") in ("revise", "reject") for h in history):
        return False
    if item.get("has_revision_remarks"):
        return False
    # Check feedback text for mild revision remarks
    feedback = (item.get("feedback") or "").lower()
    revision_cues = [
        "minor revision", "mild revision", "slight revision", "needs revision",
        "suggest revision", "consider revising", "revise to", "recommend revision",
        "requires revision", "needs a slight", "needs minor", "small tweak", "minor tweak"
    ]
    if any(cue in feedback for cue in revision_cues):
        return False
    return True

def rank_by_score(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def mean(scores):
        if not scores: return -1.0
        return sum(scores.values()) / len(scores)
        
    def cmp(a, b):
        is_pass_a = 1 if a.get("verdict") == 'pass' else 0
        is_pass_b = 1 if b.get("verdict") == 'pass' else 0
        if is_pass_a != is_pass_b:
            return is_pass_b - is_pass_a
            
        # Tie-breaker / prioritization: clean pass with zero revision remarks beats one with revision remarks
        clean_a = 1 if is_clean_pass(a) else 0
        clean_b = 1 if is_clean_pass(b) else 0
        if clean_a != clean_b:
            return clean_b - clean_a
            
        mean_a = mean(a.get("scores", {}))
        mean_b = mean(b.get("scores", {}))
        if mean_a != mean_b:
            return 1 if mean_b > mean_a else -1
            
        return 0

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

MAX_REVISIONS = 1

async def run_challenger_item(
    cand: Dict[str, str],
    idea: str,
    positioning: str,
    session: Optional[BaseModel] = None,
    call_llm_fn=None,
    sleep_fn=None,
    all_candidates: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    if call_llm_fn is None:
        call_llm_fn = call_stage_llm
    if sleep_fn is None:
        sleep_fn = asyncio.sleep
    item_val = cand["value"]
    results = []
    revision = 0
    
    while revision <= MAX_REVISIONS:
        prompt = prompts["Challenge"].format(item=item_val, positioning=positioning)
        res = await call_llm_fn("Challenge", prompt, ChallengeSchema, session)
        
        current_item = item_val.strip()
        feedback_text = res.feedback or ""
        
        verdict = 'revise' if needs_revision(res) else 'pass'
        if revision == MAX_REVISIONS and verdict == 'revise':
            verdict = 'reject'
            
        record = {
            "type": cand["type"],
            "value": current_item,
            "item": current_item,
            "scores": res.scores.model_dump(),
            "verdict": verdict,
            "decision": verdict,
            "feedback": feedback_text,
            "history": [{
                "item": current_item,
                "feedback": feedback_text,
                "verdict": verdict,
                "scores": res.scores.model_dump()
            }]
        }
        
        results.append(record)
        
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
            if all_candidates is not None and item_val not in all_candidates:
                all_candidates.append(item_val)
            await sleep_fn(4.5)
        revision += 1
        
    return results

def extract_palette_from_prose(color_direction: str) -> List[Dict[str, str]]:
    if not color_direction:
        return [
            {"name": "Obsidian Base", "hex": "#121318"},
            {"name": "Forge Ember", "hex": "#FF6B2B"},
            {"name": "Warm Stone", "hex": "#2A2D37"}
        ]
    
    colors: List[Dict[str, str]] = []
    seen_hex = set()
    
    # 1. Look for explicit name and hex patterns: e.g. "Primary: Electric Lime (#39FF14)" or "Electric Lime (#39FF14)" or "Electric Lime: #39FF14"
    pattern = re.compile(
        r'([A-Za-z0-9\s\-]+?)\s*[:\(]\s*(#[0-9A-Fa-f]{6})\)?',
        re.IGNORECASE
    )
    for match in pattern.finditer(color_direction):
        raw_name, hex_code = match.group(1).strip(), match.group(2).upper()
        parts = re.split(r'[,;:\.\n]|(?:\b(?:featuring|with|and|by|of|the|is|in|palette|primary|secondary|accent|base|neutral|hero)\b)', raw_name, flags=re.IGNORECASE)
        candidate = parts[-1].strip() if parts else raw_name.strip()
        candidate = re.sub(r'^(?:a|an|the|as|for|deep|bright|dark|light)\s+', '', candidate, flags=re.IGNORECASE).strip()
        words = candidate.split()
        if len(words) > 3:
            words = words[-3:]
        cleaned_name = ' '.join(w.capitalize() for w in words)
        if len(cleaned_name) > 1 and hex_code not in seen_hex:
            colors.append({"name": cleaned_name, "hex": hex_code})
            seen_hex.add(hex_code)
            if len(colors) >= 3:
                return colors

    # 2. Curated rule matches in order of mention in text
    known_rules = [
        (["electric lime", "lime", "neon green"], {"name": "Electric Lime", "hex": "#39FF14"}),
        (["electric cyan", "cyan", "neon blue"], {"name": "Electric Cyan", "hex": "#00F0FF"}),
        (["hot coral", "coral", "crimson", "burgundy"], {"name": "Hot Coral", "hex": "#FF6F61"}),
        (["galvanized steel", "steel gray", "steel grey", "steel"], {"name": "Galvanized Steel", "hex": "#4A5568"}),
        (["timber brown", "workbench timber", "workbench", "wood"], {"name": "Workbench Timber", "hex": "#7C4A27"}),
        (["hazard yellow", "safety yellow", "solar yellow", "yellow"], {"name": "Hazard Yellow", "hex": "#FACC15"}),
        (["terracotta", "forge ember", "ember", "rust"], {"name": "Forge Ember", "hex": "#F97316"}),
        (["forest sage", "forest", "sage", "emerald", "green"], {"name": "Forest Sage", "hex": "#15803D"}),
        (["deep navy", "navy", "cobalt", "indigo"], {"name": "Deep Navy", "hex": "#1E3A8A"}),
        (["warm ivory", "ivory", "alabaster", "cream", "sand"], {"name": "Warm Ivory", "hex": "#F5F5F4"}),
        (["matte obsidian", "charcoal", "obsidian", "matte black", "black"], {"name": "Matte Obsidian", "hex": "#18181B"}),
        (["slate grey", "slate gray", "slate"], {"name": "Slate Grey", "hex": "#334155"}),
        (["industrial teal", "teal"], {"name": "Industrial Teal", "hex": "#0D9488"}),
    ]
    
    lower_text = color_direction.lower()
    rule_hits = []
    for keywords, color_item in known_rules:
        earliest_pos = -1
        for kw in keywords:
            pos = lower_text.find(kw)
            if pos != -1 and (earliest_pos == -1 or pos < earliest_pos):
                earliest_pos = pos
        if earliest_pos != -1:
            rule_hits.append((earliest_pos, color_item))
    
    rule_hits.sort(key=lambda x: x[0])
    for _, item in rule_hits:
        hex_code = item["hex"].upper()
        if hex_code not in seen_hex:
            colors.append({"name": item["name"], "hex": hex_code})
            seen_hex.add(hex_code)
            if len(colors) >= 3:
                return colors

    # 3. Any raw hex codes found in text
    raw_hexes = re.findall(r'#[0-9A-Fa-f]{6}', color_direction)
    for h in raw_hexes:
        hex_code = h.upper()
        if hex_code not in seen_hex:
            colors.append({"name": f"Hex {hex_code}", "hex": hex_code})
            seen_hex.add(hex_code)
            if len(colors) >= 3:
                return colors

    # 4. Fill defaults up to 3
    defaults = [
        {"name": "Obsidian Base", "hex": "#121318"},
        {"name": "Forge Ember", "hex": "#FF6B2B"},
        {"name": "Warm Stone", "hex": "#2A2D37"}
    ]
    for d in defaults:
        if len(colors) < 3 and d["hex"].upper() not in seen_hex:
            colors.append(d)
            seen_hex.add(d["hex"].upper())

    return colors[:3]

async def run_stage(stage: str, session: BaseModel):
    use_mock = os.environ.get("USE_MOCK_LLM", "true").lower() not in ("0", "false", "no")
    if use_mock:
        await asyncio.sleep(1)
        mock_output = {"mock": f"data for {stage}"}
        if stage == "Deliver":
            mock_palette = [
                {"name": "Obsidian Slate", "hex": "#0F172A"},
                {"name": "Sky Cyan", "hex": "#38BDF8"},
                {"name": "Crimson Ember", "hex": "#F43F5E"}
            ]
            mock_output = {
                "sessionId": session.session_id,
                "stage": "Deliver",
                "brand": {
                    "name": "BrandCrucible",
                    "tagline": "Forge distinct identities, incinerate clichés",
                    "positioning": "The adversarial branding engine for ambitious founders",
                    "palette": mock_palette,
                    "typography": {
                        "heading": "Space Grotesk",
                        "body": "Inter"
                    }
                },
                "palette": mock_palette,
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
        
        # Ensure palette is strictly bound to color_direction text
        output["palette"] = extract_palette_from_prose(output.get("color_direction", "") or "")
    elif stage == "Challenge":
        positioning = json.dumps(session.stage_outputs.get("Position", {}))
        shape_output = session.stage_outputs.get("Shape", {})
        
        candidate_names = [c["name"] for c in (shape_output.get("candidates") or []) if "name" in c]
        candidate_taglines = [t for t in (shape_output.get("tagline_options") or [])]
        
        candidates = []
        for name in candidate_names:
            candidates.append({"type": "name", "value": name})
        for tag in candidate_taglines:
            candidates.append({"type": "tagline", "value": tag})
            
        challenge_results = []
        seen_values = set()
        
        async def evaluate_candidate(cand):
            pool = list(candidate_names if cand["type"] == "name" else candidate_taglines)
            res_items = await run_challenger_item(cand, idea, positioning, session, all_candidates=pool)
            
            for res_item in res_items:
                # Emit live event
                await store.add_event(session.session_id, {
                    "event": "challenger_eval",
                    "data": json.dumps({
                        "sessionId": session.session_id,
                        "item": res_item
                    })
                })
            return res_items

        tasks = [evaluate_candidate(cand) for cand in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res_items in results:
            if isinstance(res_items, Exception):
                print(f"Candidate evaluation failed: {res_items}")
                continue
            for res_item in res_items:
                val_norm = res_item["value"].strip().lower()
                if val_norm in seen_values:
                    continue
                seen_values.add(val_norm)
                challenge_results.append(res_item)
            
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
        
        # Carry forward and strictly bind palette from Visualize
        visualize_output = session.stage_outputs.get("Visualize", {})
        visual_palette = visualize_output.get("palette") or extract_palette_from_prose(
            ((output.get("visual_identity") or {}).get("color_direction", "")) or (visualize_output.get("color_direction", "")) or ""
        )
        if visual_palette:
            if "visual_identity" in output and isinstance(output["visual_identity"], dict):
                output["visual_identity"]["palette"] = visual_palette
            output["palette"] = visual_palette
        
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
    sem = None if is_golden else get_pipeline_semaphore()
    
    global queue_waiters
    acquired_sem = False
    
    try:
        if sem:
            if sem.locked():
                if queue_waiters >= MAX_QUEUE_LENGTH:
                    await store.add_event(session_id, {
                        "event": "error",
                        "data": json.dumps({"message": "Server is busy. Try the demo session."})
                    })
                    store.set_status(session_id, "error")
                    return
                queue_waiters += 1
                try:
                    await store.add_event(session_id, {
                        "event": "queued",
                        "data": json.dumps({"sessionId": session_id, "position": queue_waiters})
                    })
                    await asyncio.wait_for(sem.acquire(), timeout=timeout)
                    acquired_sem = True
                finally:
                    queue_waiters -= 1
            else:
                await asyncio.wait_for(sem.acquire(), timeout=timeout)
                acquired_sem = True

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
                await asyncio.sleep(0.08)
                output = session.stage_outputs.get(stage, {})
            else:
                output = await asyncio.wait_for(run_stage(stage, session), timeout=timeout)
            
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
                "challengeOutput": session.stage_outputs.get("Challenge", {}),
                "trace": session.trace
            })
        })
            
    except asyncio.CancelledError:
        store.set_status(session_id, "error")
        await store.add_event(session_id, {
            "event": "error",
            "data": json.dumps({"message": "Pipeline cancelled"})
        })
        raise
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
    finally:
        if acquired_sem and sem:
            sem.release()
            acquired_sem = False


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
        
        try:
            while True:
                if await request.is_disconnected():
                    if session_id in store._tasks:
                        store._tasks[session_id].cancel()
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
        finally:
            if await request.is_disconnected():
                if session_id in store._tasks:
                    store._tasks[session_id].cancel()

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
