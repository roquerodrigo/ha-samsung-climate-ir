"""Special fan feature field of the Samsung AC protocol."""

from __future__ import annotations

from enum import IntEnum


class SamsungAcFanSpecial(IntEnum):
    """Special fan feature; value goes in frame byte 10 bits 3-1."""

    OFF = 0b000
    POWERFUL = 0b011
    WIND_FREE = 0b101
    ECONO = 0b111
