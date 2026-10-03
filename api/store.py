import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

import json
import os

class Session(BaseModel):
    session_id: str
    idea: str
    status: str = "created"  # created | running | complete | error
    current_stage: Optional[str] = None
    stage_outputs: Dict[str, Any] = Field(default_factory=dict)
    trace: list[Dict[str, Any]] = Field(default_factory=list)
    events: list[Dict[str, Any]] = Field(default_factory=list)
    ip: str = ""
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class SessionStore:
    def __init__(self):
        self._store: Dict[str, Session] = {}
        self._conditions: Dict[str, asyncio.Condition] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

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
        
    def get_condition(self, session_id: str) -> 'asyncio.Condition':
        if session_id not in self._conditions:
            import asyncio
            self._conditions[session_id] = asyncio.Condition()
        return self._conditions[session_id]

    async def add_event(self, session_id: str, event_data: Dict[str, Any]):
        session = self.get(session_id)
        if session:
            session.events.append(event_data)
            cond = self.get_condition(session_id)
            async with cond:
                cond.notify_all()

store = SessionStore()

def load_golden_demo():
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'golden_data.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        session = Session(
            session_id=data["session_id"],
            idea=data["idea"],
            status="created",
            current_stage=data["current_stage"],
            stage_outputs=data["stage_outputs"],
            trace=data["trace"]
        )
        
        # Validate golden demo schemas at startup
        from schemas import DiscoverSchema, PositionSchema, ShapeSchema, VisualizeSchema, ChallengeSchema, DeliverSchema, ConsistencySchema
        
        schemas = {
            "Discover": DiscoverSchema,
            "Position": PositionSchema,
            "Shape": ShapeSchema,
            "Visualize": VisualizeSchema,
            "Challenge": ChallengeSchema,
            "Deliver": DeliverSchema,
            "ConsistencyCheck": ConsistencySchema
        }
        
        for stage_name, schema_cls in schemas.items():
            if stage_name not in session.stage_outputs:
                raise ValueError(f"Missing {stage_name} in stage_outputs")
            try:
                schema_cls.model_validate(session.stage_outputs[stage_name])
            except Exception as e:
                raise ValueError(f"Validation failed for stage '{stage_name}': {e}")
                
        store._store[session.session_id] = session
    except Exception as e:
        raise RuntimeError(f"Startup error: failed to load and validate golden demo: {e}")

load_golden_demo()

