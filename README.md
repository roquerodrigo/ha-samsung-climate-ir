# Samsung Climate IR

<!-- ha-marketplace:exclude-start -->
[![CI](https://github.com/roquerodrigo/ha-samsung-climate-ir/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-samsung-climate-ir/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/roquerodrigo/ha-samsung-climate-ir)](https://github.com/roquerodrigo/ha-samsung-climate-ir/releases/latest)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-samsung-climate-ir&category=integration)
<!-- ha-marketplace:exclude-end -->

Control a Samsung air conditioner from Home Assistant as a regular thermostat:
set the mode, the temperature, the fan speed, swing and WindFree, and turn the
panel light on or off. Commands go out through an infrared blaster that Home
Assistant already knows, such as an ESPHome or Zigbee IR blaster, so
everything stays on your local network.

## Supported devices

Samsung air conditioners that respond to Samsung's standard AC remote, the one
that sends the whole setting (mode, temperature, fan, swing) with every button
press. The commands match those of a Samsung wall unit remote, byte for byte.
A Samsung unit that ignores that remote does not respond to this integration
either.

WindFree only works on units that have it.

## Features

- Turn the AC on and off, pick the mode and set the temperature from a
  thermostat card, voice assistants and automations.
- Choose the fan speed, from Low to Turbo, turn swing on or off and switch to
  WindFree for cooling without a direct draft.
- Turn the panel light of the indoor unit on or off.
- Keep Home Assistant in step with the physical remote, if your blaster can
  also receive infrared.
- Hide the modes your unit does not have, so nobody picks one by mistake.

## Requirements

- Home Assistant 2026.8.0 or newer.
- An infrared emitter entity in Home Assistant that can reach the AC, for
  example from an ESPHome or Zigbee IR blaster. The blaster needs a clear line
  of sight to the indoor unit.
- Optional: an infrared receiver entity near the AC, to follow the physical
  remote.

<!-- ha-marketplace:exclude-start -->
## Installation

### Home Assistant Marketplace (recommended)

1. Select the **Open your Home Assistant instance** button above, or go to
   **Settings → Marketplace**, select **Add from link** in the upper right
   corner, enter `roquerodrigo/ha-samsung-climate-ir` and select **Add**.
2. Select **Install**.
3. Restart Home Assistant.

The Marketplace comes with Home Assistant 2026.11 and later. On older
versions, add this repository to HACS as a custom repository of type
**Integration** and install it from there.

### Manual

1. Download `samsung_climate_ir.zip` from the
   [latest release](https://github.com/roquerodrigo/ha-samsung-climate-ir/releases/latest).
2. Extract it into `config/custom_components/samsung_climate_ir/`.
3. Restart Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Configuration

Set up the IR blaster first. Then go to
**Settings → Devices & services → Add integration**, search for
**Samsung Climate IR** and fill in the form.

| Field                        | What to enter                                                     | Default                    |
|------------------------------|-------------------------------------------------------------------|----------------------------|
| Infrared emitter             | The infrared entity that sends the commands to the AC             |                            |
| Infrared receiver (optional) | An infrared receiver that hears the physical remote               | None                       |
| Supported HVAC modes         | The modes your AC has, out of Auto, Cool, Dry, Fan only and Heat. Pick at least one | Cool, Dry, Fan only, Heat |

Off is always available. Each emitter can control one AC. For a second AC,
add the integration again with another emitter.

To change any of these later, open the integration and select
**Reconfigure**. Leave the receiver empty to stop following the remote.

## Entities

Each AC appears as a device named **Samsung AC IR**, with these entities.

| Entity        | Type    | Shows                                                         |
|---------------|---------|---------------------------------------------------------------|
| Samsung AC IR | Climate | Mode, target temperature, fan speed, swing and preset          |
| Display       | Switch  | Whether the panel light is on. Configuration entity            |

The climate entity offers:

| Setting            | Values                                                    |
|--------------------|-----------------------------------------------------------|
| Mode               | Off and the modes picked in Supported HVAC modes          |
| Target temperature | 16 to 30 °C, in steps of 1 °C. Starts at 22 °C             |
| Fan mode           | Auto, Low, Medium, High, Turbo                            |
| Swing mode         | Off, On                                                   |
| Preset             | None, WindFree                                            |

Selecting WindFree sets the fan to Auto and swing to Off. Picking another fan
speed, turning swing on, or switching to Heat or Fan only turns WindFree off.
This is how the Samsung remote behaves.

The Display switch starts off. Turn it on if you want the panel light to stay
lit when Home Assistant controls the AC.

## How it works

Infrared only goes one way: the AC never tells Home Assistant what it is
doing. Home Assistant shows the last setting it sent, and keeps it across
restarts.

Every command carries the complete setting, as the Samsung remote does. When
you change the fan, swing, preset, temperature or display while the AC is
off, nothing is sent. The change goes out with the next command that turns
the AC on. Turning it on without picking a mode returns to the last mode
used.

With a receiver, Home Assistant decodes what the physical remote sends and
updates the climate entity and the Display switch to match. Without one,
anything done with the remote is invisible to Home Assistant until the next
change made from Home Assistant overwrites it.

Both entities become unavailable while the emitter is unavailable. When a
receiver is set, the climate entity also follows the receiver's
availability.

## Troubleshooting

**The setup says no infrared emitter entities were found.** The integration
needs an infrared emitter entity to send through. Set up the IR blaster in
Home Assistant first, then add this integration.

**The AC does not react.** Check that the blaster faces the indoor unit with
nothing in between, and that the AC responds to the Samsung remote described
in Supported devices.

**Home Assistant shows a different state from the AC.** Someone used the
physical remote, or a command did not reach the unit. Send the setting again
from Home Assistant, or add a receiver with **Reconfigure** to follow the
remote.

**A change made on the remote does not show up, even with a receiver.** The
remote selected a mode that is not in Supported HVAC modes. Home Assistant
ignores those presses. Add the mode with **Reconfigure**.

**The climate entity is unavailable.** The emitter, or the receiver if you
set one, is unavailable. Fix the IR blaster and the entity comes back on its
own. If only the receiver is gone for good, remove it with **Reconfigure**.

**Something else is wrong.** Download the diagnostics from the integration's
menu and attach them to an
[issue](https://github.com/roquerodrigo/ha-samsung-climate-ir/issues). The
file holds the integration's settings and the current state of its entities.

## Known limitations

- The AC cannot report its state, so Home Assistant cannot confirm that a
  command arrived. The receiver only hears the physical remote, not the AC.
- The room temperature is not available, because the AC does not send it.
  Use a separate temperature sensor if you need it.
- Swing is on or off. Choosing only vertical or only horizontal swing is not
  supported.
- Temperatures are in whole degrees Celsius.

## Support

This integration is built and maintained on personal time, on hardware bought
for the purpose. If it is useful to you, consider
[sponsoring the work](https://github.com/sponsors/roquerodrigo). It keeps the
devices, the testing and the releases coming.

<!-- ha-marketplace:exclude-start -->
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and
workflow, and [CODE_STYLE.md](CODE_STYLE.md) for the code conventions.

## License

[MIT](LICENSE)
<!-- ha-marketplace:exclude-end -->
