# Code Style Guide

Style conventions for the `ha-samsung-climate-ir` project. Before committing,
run `uv run ruff format --check .`, `uv run ruff check .` and
`uv run mypy custom_components/samsung_climate_ir` — all must exit cleanly.
`uv run pytest` (with the 90 % coverage gate) follows.

**Always read this file before adding or restructuring code.**

## Language

- Code is written in **English**: file names, class names, function names,
  variable names, dictionary keys, identifier strings.
- The conversation language with the user can be Portuguese or anything else;
  what is committed to disk stays English.
- User-facing strings live in `custom_components/samsung_climate_ir/translations/{en,pt-BR}.json`
  only — never hardcoded in Python.

## Architecture in one paragraph

This integration has **no API client, no coordinator, no polling, no
authentication, no options flow and no repairs** — deliberately. It consumes
Home Assistant's native `infrared` domain (HA ≥ 2026.8): the climate entity
encodes its whole state into one IR frame and hands it to an emitter entity.
State is **assumed** (IR is one-way) and restored across restarts. Do not add
coordinator/API scaffolding here; there is no upstream to poll or authenticate
against.

## File organization

- `__init__.py` wires `async_setup_entry` and `async_unload_entry` and nothing
  else.
- `config_flow.py` carries the `user` and `reconfigure` steps, both sharing the
  `_schema()` builder. The flow sets **no unique ID**: duplicates are blocked by
  `_async_abort_entries_match` on the emitter entity id.
- `const.py` holds `DOMAIN`, the `CONF_*` keys, the package `LOGGER` and the
  dispatcher-signal factory `signal_display_updated`.
- `device.py` builds the shared `DeviceInfo` (`build_device_info`).
- `entity.py` holds `SamsungClimateIrEntity`, the base class every platform
  entity extends.
- `climate.py` and `switch.py` hold one entity class per concrete entity
  (`SamsungClimateIrClimate`, `SamsungClimateIrClimateWithReceiver`,
  `SamsungClimateIrDisplaySwitch`).
- `diagnostics.py` returns the `SamsungClimateIrDiagnosticsPayload`.
- **`data/` is a package, one class per submodule**: `config_data.py`
  (`SamsungClimateIrConfigData`), `runtime.py` (`SamsungClimateIrRuntime`),
  `diagnostics_payload.py` (`SamsungClimateIrDiagnosticsPayload`). A flat
  multi-class `data.py` is migration debt, not a valid layout.
- **`type` aliases are the exception: they live in `data/__init__.py`**
  alongside the re-exports (`JsonPrimitive`, `JsonValue`, `JsonObject`,
  `SamsungClimateIrConfigEntry`), not in their own files.
- **`protocol/` is a package, one class per submodule**: `SamsungAcCommand`,
  `SamsungAcMode`, `SamsungAcFanSpeed`, `SamsungAcFanSpecial`,
  `SamsungAcSwing`. `protocol/__init__.py` re-exports the public symbols plus
  `MIN_TEMPERATURE`/`MAX_TEMPERATURE`.
- **Helper functions** may live in the same file as the single class that uses
  them; module-level lookup tables (`_HA_MODE_TO_PROTOCOL` and friends) stay in
  the platform module that uses them.

## Entities

- **One class per entity.** Encode each entity's behaviour directly in its
  class — never a generic class parameterized by an `EntityDescription`
  subclass with callable fields like `value_fn` or `action_fn`.
- **Every platform entity extends `SamsungClimateIrEntity`** (`entity.py`),
  which centralizes what the entry's entities share: the emitter entity id, the
  `SamsungClimateIrRuntime`, `_attr_has_entity_name`, `_attr_assumed_state`,
  and the entity identity.
- **Identity is computed, state is stored.** `unique_id` and `device_info` are
  `@property` methods on the base class, derived from the config entry
  (`<entry_id>_<suffix>` via the class-level `_unique_id_suffix`, and
  `build_device_info`). The **mutable assumed state**, on the other hand, is
  deliberately kept in `_attr_*` fields written in `__init__` and by the
  service handlers (`_attr_hvac_mode`, `_attr_fan_mode`, …): this is an
  assumed-state integration, the entity itself *is* the source of truth, and
  properties would have nothing to compute the state from. That documented
  exception applies to state only — never to identity.
- Every service handler validates its input before mutating state:
  `async_set_hvac_mode` rejects modes excluded from the config entry via
  `_valid_mode_or_raise`, which raises `ServiceValidationError` with the HA
  translation. `_mode_for_frame` is initialized from the first configured mode
  and only ever holds configured modes, so `turn_on` cannot power the AC into a
  mode the user excluded.

## Naming

- Public classes are prefixed with `SamsungClimateIr`; protocol classes with
  `SamsungAc`.
- Concrete platform entities end with the entity type:
  `SamsungClimateIrClimate`, `SamsungClimateIrDisplaySwitch`.
- Private attributes / functions are prefixed with `_`.
- Avoid abbreviations; spell names out.

## Typing

**Strict typing. No generics, no `Any`.** Mypy (`uv run mypy custom_components/samsung_climate_ir`) enforces this.

Banned: `typing.Any`, `object` as a value type, bare `dict` / `list` / `tuple` /
`set`, `dict[str, Any]`, `Mapping[str, Any]`.

Required:

- `TypedDict` for known dict / JSON shapes (see the `data/` package:
  `SamsungClimateIrConfigData`, `SamsungClimateIrDiagnosticsPayload` — one per
  file).
- `@dataclass` for structured records (`SamsungClimateIrRuntime` in
  `data/runtime.py`).
- Named `type` aliases for recursive / shared shapes — `JsonPrimitive`,
  `JsonValue`, `JsonObject` in `data/__init__.py`.
- `frozenset[str]` / `tuple[str, ...]` for fixed string collections.
- `cast("TypedDictName", value)` at HA framework boundaries that hand us a
  permissive type (e.g. `entry.data` is a read-only mapping typed
  `Mapping[str, Any]`; the platforms cast it to
  `SamsungClimateIrConfigData`).
- HA callback signatures that require `**kwargs` we do not consume are typed
  `**_kwargs: object` (see `switch.py`) — the one place `object` is acceptable,
  because the values are never read.

## Properties and `__init__`

- **Prefer `@property` for anything derived from stable backing fields** —
  entity identity (`unique_id`, `device_info` in `entity.py`) and views over
  shared runtime state (`is_on` in `switch.py` reads
  `self._runtime.display_on`).
- Mutable assumed state is the documented exception and lives in `_attr_*`
  fields (see the Entities section).
- When the body of `__init__` would only call `super().__init__(...)`, omit
  `__init__` entirely and let Python inherit the parent —
  `SamsungClimateIrDisplaySwitch` has no `__init__` for exactly that reason.
- Class-level constants like `_attr_has_entity_name = True` are fine — they
  don't depend on instance state.

## Imports

- Always start every module with `from __future__ import annotations` so type
  hints become lazy strings and the runtime cost of `if TYPE_CHECKING` imports
  is zero.
- Same-package relative imports (`from .module import …`) are the default.
- Move type-only imports into a `TYPE_CHECKING` block (Ruff `TC001`/`TC003`):

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from homeassistant.core import HomeAssistant

      from .data import SamsungClimateIrConfigData
  ```

- `noqa` comments are reserved for unavoidable framework constraints (e.g.
  `# noqa: ARG001` on the unused `hass` parameter that HA's platform-setup
  signature requires). Document the reason inline if non-obvious. Never silence
  to "make ruff happy" — fix the underlying code.

## Docstrings

- Every public class, function, method (including `@property`) and `__init__`
  has a docstring. Ruff enforces this via `D102`/`D107`.
- A single sentence is usually enough. Describe the *contract* or the *why*,
  not the obvious implementation.
- Module-level docstring at the top of every `.py` file.
- Avoid restating the type — the signature already does that.

## Comments

- Default to **no comments**. Add one only when the *why* is not obvious from
  the code: a hidden constraint, a workaround, a subtle invariant (the WindFree
  incompatibility table in `climate.py` is the canonical example).
- Never describe *what* the code does — well-named identifiers handle that.
- **No section dividers** like `# --- helpers ---`. If a file needs visual
  separators, split it into multiple files instead.

## Logging

- Any module that logs uses the package-level `LOGGER` from `const.py`
  (`LOGGER: Logger = getLogger(__package__)`); never call
  `logging.getLogger(...)` ad-hoc.
- Use **lazy `%`-formatting**, never f-strings:

  ```python
  LOGGER.warning("Failed to decode signal: %s", exception)   # ✓
  LOGGER.warning(f"Failed to decode signal: {exception}")    # ✗
  ```

- Message format: `"Failed to <verb> <object>: <cause>"` — short and grep-able.

## Runtime data

- All cross-entity state flows through
  `entry.runtime_data: SamsungClimateIrRuntime` (`data/runtime.py`). Never
  store integration state in `hass.data` — `runtime_data` is auto-discarded on
  unload, the legacy `hass.data[DOMAIN][entry_id]` pattern is not.
- The runtime couples the display switch to the climate entity: the IR
  protocol has no display-only command, so the switch flips
  `runtime.display_on` and asks the climate entity to re-send its whole state
  through the `resend_state_when_on` callback. Receiver-decoded display
  changes flow the other way through the `signal_display_updated` dispatcher
  signal.

## Config flow / diagnostics

- `config_flow.py` carries the `user` and `reconfigure` steps sharing one
  `_schema()` builder; `reconfigure` prefills the current entry data via
  `add_suggested_values_to_schema` and finishes with
  `async_update_reload_and_abort`, so changing the emitter, receiver or HVAC
  modes never requires deleting the entry.
- There is no options flow: every setting the integration has belongs to the
  device's identity and is edited through reconfigure.
- `diagnostics.py` returns `SamsungClimateIrDiagnosticsPayload` (entry data
  plus the entry's entity states). The config carries no secrets, so nothing
  is redacted — add a `TO_REDACT` constant the day a sensitive key appears.

## Protocol invariants

`protocol/samsung_ac_command.py` was validated byte-for-byte against codes
captured from a physical Samsung remote (golden tests in
`tests/protocol/test_samsung_ac_command.py`, captured timing arrays in
`tests/protocol_fixtures.py`). Do **not** change the template frame, field
offsets, checksum algorithm or timing constants without new physical captures
proving the change.

## Translations

- Two locales: `en.json` and `pt-BR.json`. `tests/test_translations.py`
  parametrizes over every locale and fails if their nested key sets diverge.
- Flow strings live under `config.step.<step_id>`; abort reasons under
  `config.abort`; selector labels under `selector.<key>.options`; entity names
  under `entity.<platform>.<key>.name`.

## HACS publishing requirements

[HACS](https://www.hacs.xyz/docs/publish/integration/) validates the repository
shape on every push (and HA itself runs `hassfest`). Both gates must stay
green:

- **One integration per repository**, located in `custom_components/<domain>/`.
- `manifest.json` must declare `domain`, `name`, `version`, `documentation`,
  `issue_tracker`, `codeowners`. The `version` key is **mandatory for custom
  integrations** and must parse as `AwesomeVersion` — CalVer or SemVer.
- `hacs.json` at the repo root pins the minimum HA core via the
  `homeassistant` key — **2026.8.0** here, because of the `infrared` domain;
  do not lower it. This is one of the three HA pins (see `CLAUDE.md`).
- Brand assets live under `custom_components/samsung_climate_ir/brand/` —
  `icon.png`, `logo.png` (+ `@2x` variants) and `icon.svg` — and are also
  registered in
  [home-assistant/brands](https://github.com/home-assistant/brands).
- A `README.md` at the repo root is required; HACS surfaces it as the
  integration description.

Release-please tags releases on every merge to `main`; HACS surfaces the five
most recent GitHub releases to users, so keep the changelog grep-able.

## Pre-commit hooks

`pre-commit` is a dev dependency (`pyproject.toml`) and
`.pre-commit-config.yaml` runs the same ruff gates as CI on every commit.
Install once per clone:

```bash
pre-commit install
```

Skip it only on emergency `git commit --no-verify` and immediately re-run
`uv run ruff format --check .` and `uv run ruff check .`.

## Conventional commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/),
which `release-please` parses to bump the version and generate `CHANGELOG.md`:

| Type | Meaning | Bump |
|---|---|---|
| `feat` | New feature | minor |
| `fix` | Bug fix | patch |
| `perf` | Performance improvement | patch |
| `deps` | Dependency bump | patch |
| `docs` | Documentation only | none |
| `refactor` | Refactor without behavior change | none |
| `test` | Test-only change | none |
| `ci` | CI / tooling change | none |
| `chore` | Anything else (rarely) | none |

- Subject line: imperative mood, lowercase, no trailing period.
- Use scopes when useful: `fix(climate): reject unconfigured hvac modes`.
- A `BREAKING CHANGE:` footer (or `!` after type) bumps the major version.

## Linting and verification

- Ruff configuration lives in `pyproject.toml` (`[tool.ruff]`) with `select = ["ALL"]`.
- Mypy configuration lives in `pyproject.toml` (`[tool.mypy]`).
- After every change run `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy custom_components/samsung_climate_ir` and `uv run pytest`.
  Both gates mirror CI.
- Tests live in `tests/`, mirroring the production layout. The 90 % coverage
  gate (`pyproject.toml`, `[tool.pytest.ini_options]`) prevents untested code
  from sneaking in. When a test exercises a state that is impossible under the
  new types, update or remove it — never weaken the type to satisfy the test.
