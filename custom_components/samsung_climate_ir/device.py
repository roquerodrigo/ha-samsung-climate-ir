"""Device registry information shared by every entity of a config entry."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def build_device_info(entry_id: str) -> DeviceInfo:
    """
    Build the device every entity of the entry attaches to.

    Each platform registers concurrently, so all of them must carry the full
    device description — an identifiers-only DeviceInfo registered first would
    name entities without the device prefix.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Samsung AC",
        manufacturer="Samsung",
    )
