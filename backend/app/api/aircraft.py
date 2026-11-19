import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/aircraft", tags=["aircraft"])

_specs = None

def get_specs():
    global _specs
    if _specs is None:
        with open(Path(__file__).parent.parent / "data" / "aircraft_specs.json") as f:
            _specs = json.load(f)
    return _specs


@router.get("/specs")
def list_all_specs():
    """Return all aircraft specs."""
    return get_specs()


@router.get("/specs/{aircraft_type}")
def get_aircraft_spec(aircraft_type: str):
    """Return specs for a specific aircraft type."""
    specs = get_specs()
    if aircraft_type in specs:
        return specs[aircraft_type]
    return {"name": aircraft_type, "description": "No data available for this aircraft type."}
