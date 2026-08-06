"""Runtime state shared between the entities of a config entry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass
class SamsungClimateIrRuntime:
    """
    State shared between the climate entity and the display switch.

    Every IR frame carries the whole AC state, so the display switch cannot
    transmit on its own: it flips ``display_on`` and asks the climate entity
    to re-send its current state via ``resend_state_when_on`` (registered by
    the climate entity while it is added to hass; it only transmits while the
    AC is assumed on).
    """

    display_on: bool = False
    resend_state_when_on: Callable[[], Awaitable[None]] | None = None
