# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read
[`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for
conventions: language, file organisation, naming, typing, properties vs
`__init__`, imports, docstrings, comments, translations, lint workflow.

## Verification workflow

**After every code change, always run lint then tests, in that order, before
declaring the task done:**

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/samsung_climate_ir
uv run pytest
```

## Architecture

This integration has **no API client, no coordinator, no polling and no
authentication**. It is a consumer of Home Assistant's native `infrared`
domain (HA ≥ 2026.8):

```
config_flow.py   → picks an infrared emitter (+ optional receiver) via
                   async_get_emitters()/async_get_receivers(); no unique_id,
                   duplicates are blocked by _async_abort_entries_match on the
                   emitter entity_id
__init__.py      → creates the shared SamsungClimateIrRuntime on runtime_data
                   and forwards the entry to the climate + switch platforms
climate.py       → SamsungClimateIrClimate extends InfraredEmitterConsumerEntity
                   (availability tracks the emitter; _send_command() delivers an
                   InfraredCommand). SamsungClimateIrClimateWithReceiver also
                   extends InfraredReceiverConsumerEntity and decodes signals
                   from the physical remote back into entity state
switch.py        → the panel-display switch. The protocol has no display-only
                   command, so the switch flips runtime_data.display_on and
                   asks the climate entity to re-send its state via the
                   resend_state_when_on callback; receiver-decoded display
                   changes flow back through the signal_display_updated
                   dispatcher signal
protocol/        → the Samsung AC IR protocol, one class per file.
                   SamsungAcCommand extends infrared_protocols.commands.Command
                   (already shipped with HA core as a dependency of the
                   infrared component — the manifest declares no requirements)
```

The entity state is **assumed** (IR is one-way) and restored via
`RestoreEntity`. Every service call re-encodes the *entire* entity state into
one frame — the Samsung protocol has no incremental commands. `_mode_for_frame`
keeps the last non-off mode so power-off/power-on frames carry a valid mode.

### Protocol invariants (validated against a physical remote)

`protocol/samsung_ac_command.py` was validated byte-for-byte against codes
captured from the real remote (see the golden tests in
`tests/protocol/test_samsung_ac_command.py`, including full captured timing
arrays in `tests/protocol_fixtures.py`). Do **not** change the template frame,
field offsets, checksum algorithm or timing constants without new physical
captures proving the change. Power lives at byte 6 bits 7-6 **and** byte 13
bits 5-4 (both copies must agree when decoding).

### WindFree/turbo interplay

WindFree (preset) forces fan auto + swing off; picking a non-auto fan or swing
on drops the preset; heat/fan-only modes drop it too. Fan "turbo" rides with
`SamsungAcFanSpecial.POWERFUL`. These rules mirror how the physical remote
behaves and are covered by tests — keep them in sync with `climate.py`.

## Tests

`tests/` mirrors the production layout; fixtures live in `tests/conftest.py`.
The infrared domain is **not** faked at the MQTT level: tests patch
`homeassistant.components.infrared.helpers.async_send_command` (captures the
typed command) and `...async_subscribe_receiver` (captures the signal
callback). Emitter availability is driven by `hass.states.async_set` on the
emitter entity id.

## Three Home Assistant version pins

1. `pyproject.toml` dev dependency `homeassistant==X` (with the matching
   `pytest-homeassistant-custom-component`).
2. `hacs.json` `homeassistant` minimum — **2026.8.0** because of the
   `infrared` domain; do not lower it.
3. CI runs against the pinned dev dependency.
