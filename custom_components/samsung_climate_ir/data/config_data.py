"""Typed shape of the data persisted on the config entry."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class SamsungClimateIrConfigData(TypedDict):
    """Shape of the data persisted on the config entry."""

    emitter_entity_id: str
    receiver_entity_id: NotRequired[str]
    hvac_modes: list[str]
