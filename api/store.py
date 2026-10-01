import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class Session(BaseModel):
    session_id: str
    idea: str
    status: str = "created"  # created | running | complete | error
    current_stage: Optional[str] = None
    stage_outputs: Dict[str, Any] = Field(default_factory=dict)
    trace: list[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class SessionStore:
    def __init__(self):
        self._store: Dict[str, Session] = {}

    def create(self, idea: str) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, idea=idea)
        self._store[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._store.get(session_id)

    def update_stage(self, session_id: str, stage: str, output: Any) -> Optional[Session]:
        session = self.get(session_id)
        if session:
            session.current_stage = stage
            session.stage_outputs[stage] = output
        return session

    def set_status(self, session_id: str, status: str) -> Optional[Session]:
        session = self.get(session_id)
        if session:
            session.status = status
        return session

store = SessionStore()

# Preloaded reference session used by demos and as a reliable fallback deliverable.
GOLDEN_STAGE_OUTPUTS = {
    "Interviewer": {"customer": "Independent home cooks aged 25–45", "need": "Confident weeknight cooking without recipe hunting", "insight": "They want a trusted sous-chef, not another recipe feed."},
    "Discover": {"audience": "Time-poor, curious home cooks", "category": "Personalized cooking companion", "tension": "Inspiration is abundant; confidence at 6 p.m. is scarce."},
    "Position": {"positioning": "A calm, capable cooking companion that turns what you have into dinner you are proud to serve.", "promise": "Make tonight's dinner feel easy and entirely yours.", "proof": ["Adapts to pantry and time", "Explains each recommendation", "Learns household preferences"]},
    "Shape": {"name": "Supperwise", "tagline": "A little more yes to dinner.", "voice": ["Warm", "Resourceful", "Unshowy"], "principles": ["Useful before clever", "Encourage without judgment", "Make good food feel achievable"]},
    "Visualize": {"palette": [{"name": "Ink", "hex": "#24352F"}, {"name": "Sage", "hex": "#9DB6A0"}, {"name": "Apricot", "hex": "#F2A76F"}, {"name": "Cream", "hex": "#FAF5EA"}], "typography": {"heading": "Fraunces", "body": "DM Sans"}, "direction": "Editorial warmth with fresh, ingredient-inspired accents."},
    "Challenge": {"clicheScore": 12, "distinctivenessScore": 91, "risks": ["Avoid generic food photography", "Do not imply professional-chef complexity"], "verdict": "Distinctive and credible; keep the language grounded in real weeknights."},
    "Deliver": {"sessionId": "golden-demo", "stage": "Deliver", "brand": {"name": "Supperwise", "tagline": "A little more yes to dinner.", "positioning": "A calm, capable cooking companion that turns what you have into dinner you are proud to serve.", "audience": "Time-poor, curious home cooks", "palette": ["#24352F", "#9DB6A0", "#F2A76F", "#FAF5EA"], "typography": {"heading": "Fraunces", "body": "DM Sans"}, "voice": ["Warm", "Resourceful", "Unshowy"]}, "challengeReport": {"clicheScore": 12, "distinctivenessScore": 91, "verdict": "Distinctive and credible; keep the language grounded in real weeknights."}}
}
golden_demo = Session(session_id="golden-demo", idea="A personalized cooking companion for confident weeknight dinners", status="complete", current_stage="Deliver", stage_outputs=GOLDEN_STAGE_OUTPUTS, trace=[
    {"stage": "Discover", "attempt": 1, "prompt": "Identify the unmet need for weeknight home cooks.", "rawResponse": "People need confidence and relevance at dinner time.", "timestamp": "2026-09-25T00:00:00Z"},
    {"stage": "Position", "attempt": 1, "prompt": "Develop a differentiated positioning statement.", "rawResponse": "A calm, capable cooking companion...", "timestamp": "2026-09-25T00:00:01Z"},
    {"stage": "Deliver", "attempt": 1, "prompt": "Assemble the final brand kit.", "rawResponse": "Supperwise — A little more yes to dinner.", "timestamp": "2026-09-25T00:00:02Z"}
])
store._store[golden_demo.session_id] = golden_demo
