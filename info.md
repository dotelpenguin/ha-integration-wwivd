# WWIVD

A Home Assistant integration that connects to a WWIV BBS (WWIVD) server's enhanced status endpoints and exposes node status, blocking, sysop stats, and last-on users as sensors.

## Features

- Connect to WWIVD via host and port
- Configurable refresh interval (default 30 seconds)
- Enable/disable endpoints: /instances, /blocking, /sysop, /laston
- Optional Modem Manager (separate host, port, and refresh interval; may be on a different node, e.g. StarDoc 134)
- Sensors: used_instances, auto_blocked_count, calls_today, email_today, feedback_today, feedback_waiting, laston_count
- Manual refresh service per connection

## Requirements

You must be using the latest WWIVD with **enhanced status endpoints** enabled.

## Installation

1. Install this integration via HACS
2. Restart Home Assistant
3. Add the integration via **Settings** > **Devices & Services** > **Add Integration** > search for "WWIVD"

## Configuration

Enter your WWIVD host and port (e.g. `192.168.1.100` and `8080`), set the refresh interval, and choose which endpoints to enable. Optionally enable Modem Manager with its own host, port, and refresh interval (it may be on a different node).
