# Troubleshooting WWIVD Integration

## Cannot connect during setup

- **Check host and port**: Ensure the WWIVD server is reachable from your Home Assistant host (e.g. `http://<host>:<port>/instances` returns JSON in a browser or with `curl`).
- **Enhanced endpoints**: You must be using the latest WWIVD with **enhanced status endpoints** enabled. If they are disabled, the integration will not be able to connect.
- **Firewall/network**: Ensure no firewall or network rule is blocking HTTP from Home Assistant to the WWIVD host and port.

## Sensors show "unavailable"

- **Server down or unreachable**: Verify WWIVD is running and that the host/port are correct.
- **Wrong URL**: The integration uses `http://` (not HTTPS). Ensure your WWIVD status server is listening on the configured port.
- **Refresh interval**: If the server is slow, try increasing the refresh interval in the integration options.

## Modem Manager cannot connect

- **Separate host/port/refresh**: Modem Manager is a separate service and may be on a different node (e.g. StarDoc 134). Use its actual host, port, and refresh interval; these are independent of the main WWIVD settings.
- **Endpoint**: The integration expects a `/modem_status` endpoint that returns JSON. Ensure that endpoint is enabled and returns valid JSON.

## Changing settings

- Go to **Settings** > **Devices & Services** > find your WWIVD integration > **Configure**.
- You can change host, port, refresh interval, and which endpoints are enabled. Changes take effect after saving; the integration will reload.

## Logs

To see detailed logs:

1. In Home Assistant, go to **Settings** > **System** > **Logging**.
2. Add a logger for `custom_components.wwivd` with level **Debug**.
3. Reproduce the issue and check the log file or **Developer Tools** > **Logs**.

## Getting help

If the problem persists, open an issue on the [GitHub repository](https://github.com/dotelpenguin/ha-integration-wwivd/issues) and include:

- Home Assistant version
- Integration version (in manifest or HACS)
- What you did and what you expected
- Relevant log lines from `custom_components.wwivd`
