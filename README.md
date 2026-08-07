# Samsung Climate IR

[![CI](https://github.com/roquerodrigo/ha-samsung-climate-ir/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-samsung-climate-ir/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open the repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-samsung-climate-ir&category=integration)

---

Home Assistant custom integration that controls **Samsung air conditioners over
infrared**, through any entity of Home Assistant's native `infrared` domain —
a Zigbee IR blaster exposed by Zigbee2MQTT, an ESPHome remote transmitter, or
any other integration that provides an infrared **emitter** entity.

It encodes the Samsung AC protocol (the 14-byte, two-section frame used by
Samsung wall units) directly, so the climate entity offers real state control
instead of a handful of pre-learned codes.

## Features

- **`climate` entity** with the full Samsung AC surface:
  - HVAC modes: off, auto, cool, dry, fan only, heat (configurable subset)
  - Target temperature, 16–30 °C
  - Fan speeds: auto, low, medium, high, turbo
  - Swing on/off
  - **WindFree** preset (vane-closed diffuse airflow on supported units)
- **Display switch**: a `switch` entity on the same device toggles the panel
  light; the bit rides along in every frame, so the preference sticks across
  mode changes and power cycles.
- **Optional infrared receiver**: if the blaster also exposes a receiver
  entity, signals from the physical remote are decoded and mirrored into the
  entity state, keeping Home Assistant in sync.
- **Assumed state with restore**: IR is one-way; the entity restores its last
  state across restarts.

## Requirements

- Home Assistant **2026.8.0** or newer (the `infrared` domain).
- An infrared **emitter** entity that reaches the AC.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → *Custom repositories*.
2. Add `https://github.com/roquerodrigo/ha-samsung-climate-ir` as type
   *Integration*.
3. Install **Samsung Climate IR** and restart Home Assistant.

### Manual

Copy `custom_components/samsung_climate_ir/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

Settings → Devices & Services → Add Integration → **Samsung Climate IR**.

| Field | Description |
| --- | --- |
| Infrared emitter | The `infrared` entity that transmits towards the AC (required) |
| Infrared receiver | Optional `infrared` receiver used to track the physical remote |
| Supported HVAC modes | Which modes the entity exposes besides *off* |

All three settings can be changed later without recreating the entry:
open the integration entry menu and pick **Reconfigure**.

## Protocol notes

Frames are generated from a template captured from a physical Samsung remote:
power (bytes 6/13), swing (byte 9), special fan features such as WindFree
(byte 10), temperature (byte 11), mode and fan speed (byte 12), plus a
per-section bit-count checksum. Signals encode as a 550/17550 µs header and two
3000/9000 µs sections of 56 LSB-first bits.

The decoder tolerates receiver skew, so captures from real remotes decode back
into typed commands — that is what powers the receiver-based state sync.
