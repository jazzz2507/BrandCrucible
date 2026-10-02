import pytest
from schemas import ChallengeSchema, ChallengeScores
from main import needs_revision

def make_challenge(cliche=7.0, distinctiveness=7.0, audience=7.0, positioning=7.0, verdict="pass"):
    return ChallengeSchema(
        item="TestBrand",
        scores=ChallengeScores(
            cliche_risk=cliche,
            distinctiveness=distinctiveness,
            audience_fit=audience,
            consistency_with_positioning=positioning,
        ),
        verdict=verdict,
        feedback="Test evaluation"
    )

def test_all_7s_with_pass():
    # all 7s with pass -> False
    item = make_challenge(7.0, 7.0, 7.0, 7.0, verdict="pass")
    assert needs_revision(item) is False

def test_average_5_5_with_pass():
    # average 5.5 with pass -> True
    item = make_challenge(5.5, 5.5, 5.5, 5.5, verdict="pass")
    assert needs_revision(item) is True

def test_average_7_5_but_one_dimension_3():
    # average 7.5 (9+9+9+3 = 30 / 4 = 7.5) but one dimension 3 -> True
    item = make_challenge(9.0, 9.0, 9.0, 3.0, verdict="pass")
    assert needs_revision(item) is True

def test_good_scores_with_verdict_revise():
    # good scores with verdict "revise" -> True
    item = make_challenge(8.0, 8.5, 9.0, 8.5, verdict="revise")
    assert needs_revision(item) is True

def test_boundary_average_exactly_6_with_pass():
    # boundaries: average exactly 6.0 with all dimensions >= 4 and pass -> False
    item = make_challenge(6.0, 6.0, 6.0, 6.0, verdict="pass")
    assert needs_revision(item) is False

def test_boundary_dimension_exactly_4():
    # a dimension of exactly 4 with average >= 6.0 and pass -> False
    # (4 + 8 + 8 + 8) / 4 = 7.0 average, dimension of 4.0
    item = make_challenge(4.0, 8.0, 8.0, 8.0, verdict="pass")
    assert needs_revision(item) is False

    # (4 + 6 + 7 + 7) / 4 = 6.0 average, dimension of 4.0
    item2 = make_challenge(4.0, 6.0, 7.0, 7.0, verdict="pass")
    assert needs_revision(item2) is False

def test_verdict_reject_with_high_scores():
    # verdict "reject" even with high scores -> True
    item = make_challenge(10.0, 10.0, 10.0, 10.0, verdict="reject")
    assert needs_revision(item) is True
