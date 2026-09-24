from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="BrandCrucible API")

# Enable CORS so your frontend can call these routes without errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IdeaInput(BaseModel):
    idea: str

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "BrandCrucible API"}

# H2-8: Interviewer input route (Mock data for Frontend)
@app.post("/api/interview/start")
def start_interview(payload: IdeaInput):
    return {
        "sessionId": "session-101",
        "question": f"Interesting idea: '{payload.idea}'. Who is your primary target customer?",
        "stage": "Interviewer"
    }

# H2-8: Mock Brand Kit deliverable route
@app.get("/api/brand-kit/{session_id}")
def get_brand_kit(session_id: str):
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