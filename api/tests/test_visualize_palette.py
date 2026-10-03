import pytest
from main import extract_palette_from_prose
from schemas import VisualizeSchema, DeliverSchema, ColorSwatch

def test_extract_palette_with_explicit_name_and_hex():
    prose = "An energetic palette featuring Electric Lime (#39FF14) as the hero accent, Obsidian Slate (#18181B) for the background, and Warm Cream (#FFFDD0) for text."
    palette = extract_palette_from_prose(prose)
    assert len(palette) == 3
    names = [c["name"] for c in palette]
    hexes = [c["hex"] for c in palette]
    assert "Electric Lime" in names
    assert "#39FF14" in hexes
    assert "#18181B" in hexes
    assert "#FFFDD0" in hexes

def test_extract_palette_with_electric_lime_keyword():
    prose = "A bold direction built around Electric Lime and deep charcoal."
    palette = extract_palette_from_prose(prose)
    assert len(palette) == 3
    assert palette[0]["name"] == "Electric Lime"
    assert palette[0]["hex"] == "#39FF14"

def test_extract_palette_golden_data_order():
    prose = "A grounded, utilitarian palette featuring deep galvanized steel gray, weathered workbench timber brown, and a high-visibility hazard yellow accent to signal readiness and safety."
    palette = extract_palette_from_prose(prose)
    assert len(palette) == 3
    assert palette[0]["name"] == "Galvanized Steel"
    assert palette[0]["hex"] == "#4A5568"
    assert palette[1]["name"] == "Workbench Timber"
    assert palette[1]["hex"] == "#7C4A27"
    assert palette[2]["name"] == "Hazard Yellow"
    assert palette[2]["hex"] == "#FACC15"

def test_schema_optional_palette_backwards_compatibility():
    # Without palette
    data_without = {
        "color_direction": "Utilitarian palette",
        "typography_direction": "Sturdy sans",
        "imagery_direction": "Honest photography",
        "rationale": "Direct reflection"
    }
    schema = VisualizeSchema.model_validate(data_without)
    assert schema.palette is None

    # With palette
    data_with = {
        **data_without,
        "palette": [
            {"name": "Electric Lime", "hex": "#39FF14"},
            {"name": "Obsidian Slate", "hex": "#18181B"},
            {"name": "Pure White", "hex": "#FFFFFF"}
        ]
    }
    schema_with = VisualizeSchema.model_validate(data_with)
    assert schema_with.palette is not None
    assert len(schema_with.palette) == 3
    assert schema_with.palette[0].name == "Electric Lime"
