"""Google Earth Engine data retrieval tool (stub)."""

from __future__ import annotations


def search_imagery(aoi: dict, date_range: tuple[str, str]) -> list[dict]:
    """Search for imagery covering *aoi* within *date_range*.  Stub."""
    return [
        {
            "id": "mock_scene_001",
            "date": date_range[0],
            "cloud_cover": 5.0,
            "uri": "mock://scenes/001.tif",
        }
    ]
