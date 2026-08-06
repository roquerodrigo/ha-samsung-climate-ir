"""Samsung AC infrared protocol encoder and decoder."""

from __future__ import annotations

from .samsung_ac_command import MAX_TEMPERATURE, MIN_TEMPERATURE, SamsungAcCommand
from .samsung_ac_fan_special import SamsungAcFanSpecial
from .samsung_ac_fan_speed import SamsungAcFanSpeed
from .samsung_ac_mode import SamsungAcMode
from .samsung_ac_swing import SamsungAcSwing

__all__ = [
    "MAX_TEMPERATURE",
    "MIN_TEMPERATURE",
    "SamsungAcCommand",
    "SamsungAcFanSpecial",
    "SamsungAcFanSpeed",
    "SamsungAcMode",
    "SamsungAcSwing",
]
