import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse

from store import store

load_dotenv()

PORT = int(os.environ.get("PORT", 8000))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(title="BrandCrucible API")

# Enable CORS so your frontend can call these routes without errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IdeaInput(BaseModel):
    idea: str

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "BrandCrucible API"}

@app.get("/health")
def health():
    return {"status": "ok"}

# H2-8: Interviewer input route (Mock data for Frontend)
@app.post("/api/interview/start")
def start_interview(payload: IdeaInput):
    session = store.create(idea=payload.idea)
    return {
        "sessionId": session.session_id,
        "question": f"Interesting idea: '{payload.idea}'. Who is your primary target customer?"
    }

# H2-8: Mock Brand Kit deliverable route
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

STAGES = ["Interviewer", "Discover", "Position", "Shape", "Visualize", "Challenge", "Deliver"]

async def run_stage(stage: str, session: BaseModel):
    # Mock AI call placeholder
    await asyncio.sleep(1)
    
    # Save mock output
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

@app.get("/api/pipeline/stream/{session_id}")
async def stream_pipeline(session_id: str, request: Request):
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    store.set_status(session_id, "running")

    async def event_generator():
        try:
            total = len(STAGES)
            for i, stage in enumerate(STAGES):
                if await request.is_disconnected():
                    break
                    
                # Emit stage_start
                yield {
                    "event": "stage_start",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "stage": stage,
                        "index": i,
                        "total": total
                    })
                }
                
                # Run stage logic
                output = await run_stage(stage, session)
                
                # Emit stage_complete
                yield {
                    "event": "stage_complete",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "stage": stage,
                        "index": i,
                        "total": total,
                        "output": output
                    })
                }
                
            store.set_status(session_id, "complete")
            
            # After last stage emit done
            yield {
                "event": "done",
                "data": json.dumps(store.get(session_id).stage_outputs.get("Deliver", {}))
            }
            
        except Exception as e:
            store.set_status(session_id, "error")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }
            
    return EventSourceResponse(
        event_generator(),
        ping=15
    )