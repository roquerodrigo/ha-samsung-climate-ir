"""Swing field of the Samsung AC protocol."""

from __future__ import annotations

from enum import IntEnum


class SamsungAcSwing(IntEnum):
    """Louver swing; value goes in frame byte 9 bits 6-4."""

    VERTICAL = 0b010
    HORIZONTAL = 0b011
    BOTH = 0b100
    OFF = 0b111
