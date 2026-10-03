import pytest
import asyncio
from schemas import ChallengeSchema, ChallengeScores, ShapeSchema, ShapeCandidate
from main import run_challenger_item, MAX_REVISIONS

def make_challenge_result(item: str, score_val: float, verdict: str = "pass", feedback: str = "ok"):
    return ChallengeSchema(
        item=item,
        scores=ChallengeScores(
            cliche_risk=score_val,
            distinctiveness=score_val,
            audience_fit=score_val,
            consistency_with_positioning=score_val,
        ),
        verdict=verdict,
        feedback=feedback,
    )

def make_shape_result(name: str, tagline: str):
    return ShapeSchema(
        candidates=[ShapeCandidate(name=name, rationale="good", risk="low")],
        personality_traits=["Bold"],
        tagline_options=[tagline],
        voice_description="Direct"
    )

@pytest.mark.asyncio
async def test_challenger_stops_early_on_pass():
    call_counts = {"Challenge": 0, "Shape": 0}

    async def fake_llm(stage, prompt, schema, session=None):
        call_counts[stage] += 1
        if stage == "Challenge":
            return make_challenge_result("InitialName", 7.5, verdict="pass", feedback="Great name")
        raise RuntimeError("Shape should not be called when candidate passes immediately")

    cand = {"type": "name", "value": "InitialName"}
    res = await run_challenger_item(cand, idea="startup idea", positioning="positioning text", call_llm_fn=fake_llm)

    assert call_counts["Challenge"] == 1
    assert call_counts["Shape"] == 0
    assert res["verdict"] == "pass"
    assert res["value"] == "InitialName"
    assert res["exhausted_revisions"] is False
    assert len(res["history"]) == 1

@pytest.mark.asyncio
async def test_challenger_makes_at_most_3_attempts():
    challenge_calls = 0
    shape_calls = 0

    async def fake_llm(stage, prompt, schema, session=None):
        nonlocal challenge_calls, shape_calls
        if stage == "Challenge":
            challenge_calls += 1
            return make_challenge_result(f"Candidate_{challenge_calls}", 4.5, verdict="revise", feedback="Too generic")
        elif stage == "Shape":
            shape_calls += 1
            return make_shape_result(f"Replacement_{shape_calls}", f"Tagline_{shape_calls}")
        raise RuntimeError(f"Unexpected stage {stage}")

    cand = {"type": "name", "value": "InitialCandidate"}
    res = await run_challenger_item(cand, idea="startup idea", positioning="positioning text", call_llm_fn=fake_llm)

    # MAX_REVISIONS = 2 -> Initial (0) + Revision 1 (1) + Revision 2 (2) = 3 total attempts
    assert challenge_calls == 3
    assert shape_calls == 2
    assert len(res["history"]) == 3
    assert res["exhausted_revisions"] is True
    assert res["verdict"] == "revise"

@pytest.mark.asyncio
async def test_challenger_tracks_best_scoring_attempt():
    attempts_scores = [4.0, 5.8, 4.5]  # Attempt 1 (5.8) is highest, though still revising
    current_attempt = 0

    async def fake_llm(stage, prompt, schema, session=None):
        nonlocal current_attempt
        if stage == "Challenge":
            score = attempts_scores[current_attempt]
            name = f"Cand_v{current_attempt}"
            current_attempt += 1
            return make_challenge_result(name, score, verdict="revise", feedback=f"Score {score}")
        elif stage == "Shape":
            return make_shape_result(f"Cand_v{current_attempt}", f"Tag_v{current_attempt}")

    cand = {"type": "name", "value": "Cand_v0"}
    res = await run_challenger_item(cand, idea="startup idea", positioning="positioning text", call_llm_fn=fake_llm)

    # Candidate from attempt 1 (highest score 5.8) should be chosen as best
    assert res["value"] == "Cand_v1"
    assert res["scores"]["cliche_risk"] == 5.8
    assert res["verdict"] == "revise"
    assert res["exhausted_revisions"] is True

@pytest.mark.asyncio
async def test_challenger_passes_on_second_attempt():
    current_attempt = 0

    async def fake_llm(stage, prompt, schema, session=None):
        nonlocal current_attempt
        if stage == "Challenge":
            if current_attempt == 0:
                current_attempt += 1
                return make_challenge_result("FirstTry", 4.0, verdict="revise", feedback="Needs work")
            else:
                return make_challenge_result("SecondTry", 8.0, verdict="pass", feedback="Excellent")
        elif stage == "Shape":
            return make_shape_result("SecondTry", "SecondTagline")

    cand = {"type": "name", "value": "FirstTry"}
    res = await run_challenger_item(cand, idea="startup idea", positioning="positioning text", call_llm_fn=fake_llm)

    assert res["value"] == "SecondTry"
    assert res["verdict"] == "pass"
    assert res["exhausted_revisions"] is False
    assert len(res["history"]) == 2

@pytest.mark.asyncio
async def test_challenger_history_is_recorded():
    current_attempt = 0

    async def fake_llm(stage, prompt, schema, session=None):
        nonlocal current_attempt
        if stage == "Challenge":
            idx = current_attempt
            current_attempt += 1
            return make_challenge_result(f"Name_{idx}", float(idx + 4), verdict="revise", feedback=f"Feedback {idx}")
        elif stage == "Shape":
            return make_shape_result(f"Name_{current_attempt}", f"Tagline_{current_attempt}")

    cand = {"type": "name", "value": "Name_0"}
    res = await run_challenger_item(cand, idea="startup idea", positioning="positioning text", call_llm_fn=fake_llm)

    assert "history" in res
    assert len(res["history"]) == 3
    assert res["history"][0]["item"] == "Name_0"
    assert res["history"][0]["feedback"] == "Feedback 0"
    assert res["history"][1]["item"] == "Name_1"
    assert res["history"][1]["feedback"] == "Feedback 1"
    assert res["history"][2]["item"] == "Name_2"
    assert res["history"][2]["feedback"] == "Feedback 2"


def test_challenge_schema_aliases():
    payload = {
        "target": "AliasCandidate",
        "scores": {
            "cliche_risk": 8.0,
            "distinctiveness": 8.0,
            "audience_fit": 8.0,
            "consistency_with_positioning": 8.0
        },
        "verdict": "pass",
        "explanation": "Valid critique via explanation alias"
    }
    schema = ChallengeSchema.model_validate(payload)
    assert schema.item == "AliasCandidate"
    assert schema.feedback == "Valid critique via explanation alias"

