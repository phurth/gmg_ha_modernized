# Green Mountain Grill — Home Assistant HACS Integration

Local control and monitoring of Wi-Fi Green Mountain Grill pellet smokers in Home Assistant, over the grill's local UDP protocol. No cloud, no account.

> **Disclaimer:** This is an unofficial, community-maintained integration and is not affiliated with or endorsed by Green Mountain Grills. It builds on the original work of [@jwhitby91](https://github.com/jwhitby91) and the community fork lineage.

## Features

| Entity | Type | Description |
|--------|------|-------------|
| Grill | `climate` | Current temperature, target temperature (settable), and power on/off (heat/off). Range 150–500 °F. |
| Food Probe 1 | `sensor` | Probe 1 temperature (read-only). |
| Food Probe 2 | `sensor` | Probe 2 temperature (read-only). |

All entities are grouped under a single device identified by the grill's serial number.

## Requirements

- Home Assistant 2025.1 or newer.
- The grill and Home Assistant on the same network, with UDP port 8080 reachable between them.
- A stable IP for the grill (a DHCP reservation is recommended so the configured host stays valid).

## Installation (HACS)

1. In HACS, open the three-dot menu (top right) → **Custom repositories**.
2. Add `https://github.com/phurth/gmg_ha_modernized` with category **Integration**, then **Add**.
3. Search for **GMG Grill**, open it, and click **Download**.
4. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **GMG Grill**.
3. Enter the grill's IP address.

The integration reads the grill's serial number on first setup and uses it as the stable device identity.

## Notes & Limitations

- **Local polling only.** The grill is polled every 30 seconds over UDP; there is no cloud dependency.
- **Availability tracks reachability.** When the grill can't be reached (commonly because it's unplugged or powered off at the mains), all entities report `unavailable` and recover automatically once it's back. Polls fail fast so an unreachable grill never blocks Home Assistant.
- **Probe state.** A probe that isn't plugged in reads `unknown` while the grill itself is reachable — distinct from the grill being `unavailable`.
- **Temperatures are in °F**, matching the values the grill reports on the wire.

## Credits

Original integration by [@jwhitby91](https://github.com/jwhitby91); climate-API modernization from the community fork lineage. This fork adds a UI config flow, coordinator-based polling with proper availability handling, and stable serial-based device identity.
