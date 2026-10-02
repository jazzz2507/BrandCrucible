import pytest
from main import rank_by_score, select_candidate

def test_pass_beats_higher_scoring_revise():
    # a "pass" beats a higher-scoring "revise"
    pass_item = {
        "value": "PassedItem",
        "verdict": "pass",
        "scores": {"cliche_risk": 6.0, "distinctiveness": 6.0, "audience_fit": 6.0, "consistency_with_positioning": 6.0}
    }
    revise_item = {
        "value": "ReviseItem",
        "verdict": "revise",
        "scores": {"cliche_risk": 9.5, "distinctiveness": 9.0, "audience_fit": 9.0, "consistency_with_positioning": 9.5}
    }
    ranked = rank_by_score([revise_item, pass_item])
    assert ranked[0]["value"] == "PassedItem"
    assert ranked[1]["value"] == "ReviseItem"

def test_among_passes_higher_mean_wins():
    # among passes the higher mean wins
    pass_lower = {
        "value": "PassLower",
        "verdict": "pass",
        "scores": {"cliche_risk": 6.0, "distinctiveness": 7.0, "audience_fit": 6.0, "consistency_with_positioning": 7.0}  # mean 6.5
    }
    pass_higher = {
        "value": "PassHigher",
        "verdict": "pass",
        "scores": {"cliche_risk": 8.0, "distinctiveness": 8.0, "audience_fit": 8.0, "consistency_with_positioning": 8.0}  # mean 8.0
    }
    ranked = rank_by_score([pass_lower, pass_higher])
    assert ranked[0]["value"] == "PassHigher"
    assert ranked[1]["value"] == "PassLower"

def test_among_non_pass_higher_mean_wins():
    # among non-pass the higher mean wins
    revise_lower = {
        "value": "ReviseLower",
        "verdict": "revise",
        "scores": {"cliche_risk": 4.0, "distinctiveness": 4.0, "audience_fit": 4.0, "consistency_with_positioning": 4.0}  # mean 4.0
    }
    revise_higher = {
        "value": "ReviseHigher",
        "verdict": "revise",
        "scores": {"cliche_risk": 5.5, "distinctiveness": 6.0, "audience_fit": 5.5, "consistency_with_positioning": 5.0}  # mean 5.5
    }
    ranked = rank_by_score([revise_lower, revise_higher])
    assert ranked[0]["value"] == "ReviseHigher"
    assert ranked[1]["value"] == "ReviseLower"

def test_item_with_missing_scores_ranks_last():
    # an item with missing scores ranks last
    normal_item = {
        "value": "NormalItem",
        "verdict": "revise",
        "scores": {"cliche_risk": 3.0, "distinctiveness": 3.0, "audience_fit": 3.0, "consistency_with_positioning": 3.0}  # mean 3.0
    }
    missing_dict_item = {
        "value": "EmptyScoresItem",
        "verdict": "revise",
        "scores": {}
    }
    none_scores_item = {
        "value": "NoneScoresItem",
        "verdict": "revise",
        "scores": None
    }
    no_key_item = {
        "value": "NoKeyItem",
        "verdict": "revise"
    }

    ranked = rank_by_score([missing_dict_item, normal_item, none_scores_item, no_key_item])
    assert ranked[0]["value"] == "NormalItem"
    # All items with missing/empty/None scores have mean -1 and rank after normal_item
    assert set(item["value"] for item in ranked[1:]) == {"EmptyScoresItem", "NoneScoresItem", "NoKeyItem"}

def test_empty_list_falls_back_to_first_shape_candidate():
    # an empty list falls back to the first shape candidate
    fallback_names = [
        {"name": "FirstCandidateName", "rationale": "Strong fit", "risk": "Low"},
        {"name": "SecondCandidateName", "rationale": "Secondary", "risk": "Medium"}
    ]
    fallback_taglines = [
        "First Tagline Option",
        "Second Tagline Option"
    ]

    # Name fallback when ranked list is empty
    chosen_name = select_candidate([], fallback_names, fallback_key="name")
    assert chosen_name == "FirstCandidateName"

    # Tagline fallback when ranked list is empty
    chosen_tagline = select_candidate([], fallback_taglines, fallback_key="")
    assert chosen_tagline == "First Tagline Option"

    # When ranked items are present, the ranked item wins over fallback
    ranked_names = [{"value": "RankedWinner"}]
    chosen_from_ranked = select_candidate(ranked_names, fallback_names, fallback_key="name")
    assert chosen_from_ranked == "RankedWinner"
