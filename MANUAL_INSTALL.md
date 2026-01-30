# Manual Installation Guide

If you cannot install via HACS, you can install the WWIVD integration manually.

## Method 1: Git clone

1. On your Home Assistant server, go to the `custom_components` directory (e.g. `/config/custom_components`).
2. Clone the repository and copy the integration into place:

   ```bash
   cd /config/custom_components
   git clone https://github.com/dotelpenguin/ha-integration-wwivd.git _wwivd_repo
   cp -r _wwivd_repo/custom_components/wwivd .
   rm -rf _wwivd_repo
   ```

3. Restart Home Assistant.

## Method 2: Download ZIP

1. Download the repository as a ZIP from GitHub (Code > Download ZIP).
2. Extract the archive.
3. Copy the folder `custom_components/wwivd` to your Home Assistant `custom_components` directory (e.g. `/config/custom_components/wwivd`).
4. Restart Home Assistant.

## Verify installation

Ensure these files exist under `custom_components/wwivd/`:

- `__init__.py`
- `config_flow.py`
- `const.py`
- `manifest.json`
- `sensor.py`
- `strings.json`
- `services.yaml`
- `translations/en.json`

## Add the integration

1. Go to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for **WWIVD** and complete the setup wizard.
