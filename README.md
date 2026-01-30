# WWIVD Home Assistant Integration

A Home Assistant integration that connects to a WWIV BBS (WWIVD) server's enhanced status endpoints and exposes node status, blocking, sysop stats, and last-on users as sensors.

## Requirements

- **WWIVD**: You must be using the latest WWIVD with **enhanced status endpoints** enabled. Enable these in your WWIVD configuration.

## Features

- Connect to WWIVD via host and port (HTTP, unauthenticated)
- Configurable refresh interval (default 30 seconds)
- Enable or disable each endpoint:
  - **/instances** – Enhanced node status → `used_instances` sensor
  - **/blocking** – IP whitelist/blacklist management → `auto_blocked_count` sensor
  - **/sysop** – Sysop and system status → `calls_today`, `email_today`, `feedback_today`, `feedback_waiting` sensors
  - **/laston** – Last users who logged on → `laston_count` sensor and list in attributes
- Optional **Modem Manager** (e.g. StarDoc 134): separate host/port, `/modem_status` (default disabled)
- Manual refresh service per connection
- Options flow to change host, port, refresh interval, and endpoint toggles without re-adding the integration

## Installation

### Via HACS (recommended)

1. Add this repository to HACS as a custom repository.
2. Install "WWIVD" from HACS.
3. Restart Home Assistant.
4. Add the integration via **Settings** > **Devices & Services** > **Add Integration** > search for "WWIVD".

### Manual installation

See [MANUAL_INSTALL.md](MANUAL_INSTALL.md).

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for **WWIVD**.
3. Enter:
   - **Host**: WWIVD server hostname or IP (e.g. `192.168.1.100` or `bbs.example.com`)
   - **Port**: Port (default `8080`)
   - **Refresh interval**: Seconds between updates (default `30`, minimum `5`)
   - Enable/disable each endpoint as needed.
   - Optionally enable **Modem Manager** and enter its host/port (e.g. for StarDoc 134).
4. Complete the setup. Sensors will be created for each enabled endpoint.

To change settings later: select the WWIVD integration and click **Configure**.

## Entities

| Endpoint   | Sensor(s)           | Description                    |
|-----------|---------------------|--------------------------------|
| /instances | Used instances      | Node usage count               |
| /blocking  | Auto blocked count  | Auto-blocked IP count          |
| /sysop     | Calls today         | Calls today                    |
| /sysop     | Email today         | Email today                    |
| /sysop     | Feedback today      | Feedback today                 |
| /sysop     | Feedback waiting    | Feedback waiting               |
| /laston    | Last on count       | Number of users in laston list |

The **Last on count** sensor also exposes a `laston` attribute with the list of recent users (capped in attributes).

## Services

Each integration instance registers a refresh service:

- **Service**: `wwivd.refresh_<connection_name>`
- **Description**: Manually refresh WWIVD data for that connection.

Example (if the integration title is "WWIVD - 192.168.1.100:8080"):

```yaml
service: wwivd.refresh_192_168_1_100_8080
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## License

MIT License. See [LICENSE](LICENSE).
