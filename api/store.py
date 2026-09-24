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
