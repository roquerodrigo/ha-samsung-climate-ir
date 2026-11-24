# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/roquerodrigo/ha-samsung-climate-ir/issues/new/choose)
with:

- the Home Assistant version, the integration version, the AC model and the
  IR blaster you use;
- what you did, what you expected and what happened;
- the diagnostics downloaded from the integration's menu and the relevant log
  lines.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
scripts/setup      # install the dependencies into .venv
scripts/develop    # run Home Assistant at http://localhost:8123 with this integration loaded
```

`scripts/develop` uses the configuration in [`config/`](config/), which turns
on debug logging for the integration. The integration needs an infrared
emitter entity, so set one up in that instance before adding it.

## Checks

Run these before opening a pull request. CI runs the same ones, and
`pre-commit install` runs the first three on every commit.

```bash
uv run ruff format .                                # format
uv run ruff check . --fix                           # lint
uv run mypy custom_components/samsung_climate_ir    # type-check
uv run pytest                                       # tests, coverage must stay at 90 % or more
```

Read [CODE_STYLE.md](CODE_STYLE.md) before adding or restructuring code.

## Infrared protocol

The encoder and decoder live in
[`protocol/samsung_ac_command.py`](custom_components/samsung_climate_ir/protocol/samsung_ac_command.py),
whose module docstring documents the frame layout. In short:

- A command is a 14-byte frame in two 7-byte sections, sent LSB first.
- Power sits in byte 6 and again in byte 13. Both copies must agree when
  decoding. Swing is in byte 9, the special fan feature (WindFree, Powerful,
  Econo) and the display bit in byte 10, the temperature in byte 11, mode and
  fan speed in byte 12.
- Each section carries a checksum built from the inverted count of set bits.
- The signal is a 550/17550 µs header, then for each section a 3000/9000 µs
  section header and 56 bits (500 µs mark, 500 µs space for 0, 1500 µs space
  for 1), with a 3000 µs gap between sections.
- The decoder tolerates the timing skew of real receivers and accepts captures
  that start without the leading header.

The template frame, field offsets, checksum and timings were validated byte
for byte against captures from a physical Samsung remote. The golden tests in
[`tests/protocol/test_samsung_ac_command.py`](tests/protocol/test_samsung_ac_command.py)
and the captured timings in [`tests/protocol_fixtures.py`](tests/protocol_fixtures.py)
guard them. Do not change any of them without new captures that prove the
change.

## Pull requests

1. Fork the repository and branch from `main`.
2. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/).
   Releases and their notes are generated from them. Mark breaking changes
   with `!` or a `BREAKING CHANGE:` footer.
3. Update `translations/en.json` and `translations/pt-BR.json` together when
   you change user-facing strings. `tests/test_translations.py` fails when
   their keys differ.
4. Update the README when behaviour, configuration or entities change.
5. Fill in the pull request template.

## License

Contributions are released under the project's [MIT License](LICENSE).
