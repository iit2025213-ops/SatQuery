"""Timelapse generation tool (stub)."""

from __future__ import annotations


def generate_timelapse_frames(image_uris: list[str]) -> list[str]:
    """Generate timelapse frames from a sequence of images.  Stub."""
    return [f"frame_{i}.png" for i in range(len(image_uris))]
