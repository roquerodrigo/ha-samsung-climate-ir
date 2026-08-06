"""Operating mode field of the Samsung AC protocol."""

from __future__ import annotations

from enum import IntEnum


class SamsungAcMode(IntEnum):
    """AC operating mode; value goes in frame byte 12 bits 6-4."""

    AUTO = 0
    COOL = 1
    DRY = 2
    FAN = 3
    HEAT = 4
