"""Fan speed field of the Samsung AC protocol."""

from __future__ import annotations

from enum import IntEnum


class SamsungAcFanSpeed(IntEnum):
    """Fan speed; value goes in frame byte 12 bits 3-1."""

    AUTO = 0
    LOW = 2
    MEDIUM = 4
    HIGH = 5
    # Some units report this value instead of AUTO while running in auto mode.
    AUTO_ALTERNATE = 6
    TURBO = 7
