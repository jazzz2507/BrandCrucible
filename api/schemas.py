from pydantic import BaseModel, Field, AliasChoices
from typing import List, Literal, Optional

class Audience(BaseModel):
    primary: str
    secondary: str

class DiscoverSchema(BaseModel):
    audience: Audience
    problem_statement: str
    constraints: List[str]
    assumptions: List[str]
    open_questions: List[str]

class PositionSchema(BaseModel):
    value_proposition: str
    differentiators: List[str]
    competitive_angle: str
    positioning_statement: str

class ShapeCandidate(BaseModel):
    name: str
    rationale: str
    risk: str

class ShapeSchema(BaseModel):
    candidates: List[ShapeCandidate]
    personality_traits: List[str]
    tagline_options: List[str]
    voice_description: str

class ColorSwatch(BaseModel):
    name: str
    hex: str

class VisualizeSchema(BaseModel):
    color_direction: str
    typography_direction: str
    imagery_direction: str
    rationale: str
    palette: Optional[List[ColorSwatch]] = None


class ChallengeScores(BaseModel):
    cliche_risk: float
    distinctiveness: float
    audience_fit: float
    consistency_with_positioning: float

class ChallengeSchema(BaseModel):
    item: str = Field(validation_alias=AliasChoices('item', 'target', 'candidate'))
    scores: ChallengeScores
    verdict: Literal['pass', 'revise', 'reject']
    feedback: str = Field(validation_alias=AliasChoices('feedback', 'explanation', 'critique'))

class DeliverDiscovery(BaseModel):
    audience: Audience
    problem_statement: str
    constraints: List[str]
    assumptions: List[str]
    open_questions: List[str]

class DeliverPositioning(BaseModel):
    value_proposition: str
    differentiators: List[str]
    competitive_angle: str
    positioning_statement: str

class DeliverBrandShape(BaseModel):
    personality_traits: List[str]
    voice_description: str

class DeliverVisualIdentity(BaseModel):
    color_direction: str
    typography_direction: str
    imagery_direction: str
    rationale: str
    palette: Optional[List[ColorSwatch]] = None

class DeliverSchema(BaseModel):
    brand_name: str
    tagline: str
    discovery: DeliverDiscovery
    positioning: DeliverPositioning
    brand_shape: DeliverBrandShape
    visual_identity: DeliverVisualIdentity
    rationale: str
    palette: Optional[List[ColorSwatch]] = None

class ConsistencyIssue(BaseModel):
    area: str
    description: str
    severity: Literal['minor', 'major']

class ConsistencySchema(BaseModel):
    is_consistent: bool
    overall_score: float
    issues: List[ConsistencyIssue]
    summary: str
