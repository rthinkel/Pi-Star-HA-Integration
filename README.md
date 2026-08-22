# Pi-Star Home Assistant Integration

A custom Home Assistant integration for monitoring a Pi-Star digital voice hotspot. It polls the local Pi-Star dashboard and exposes hotspot health, radio/DMR status, gateway activity, and local RF activity as Home Assistant sensors. No cloud service is required.

## Features

- Hotspot, firmware, TRX, TX/RX frequency, DMR network, ID, color code, timeslot, and master status
- Gateway and local-RF last-heard callsign, talkgroup, mode, duration, BER, loss, and RSSI where available
- Current transmit state
- Structured Pi-Star last-heard API support with automatic legacy HTML fallback
- Automatic reauthentication, connection reconfiguration, configurable polling, and Home Assistant diagnostics
- Partial-failure handling that preserves the last valid data when only one Pi-Star endpoint is unavailable

## Install with HACS

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/rthinkel/Pi-Star-HA-Integration` as an **Integration**.
3. Open **Pi-Star** in HACS and select **Download**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**, search for **Pi-Star**, and enter the dashboard address and credentials.

Default Pi-Star values are `pi-star.local`, username `pi-star`, and password `raspberry`. Use your configured values if they differ.

After setup, use the integration's **Configure** action to change the polling interval (default 30 seconds; supported range 10–3600 seconds). Connection details can be changed with **Reconfigure**.

## Manual installation

Copy `custom_components/pistar` to `/config/custom_components/pistar/`, restart Home Assistant, then add **Pi-Star** from **Settings → Devices & services**.

## Notes

This project is independent and is not affiliated with Pi-Star or Home Assistant Core. Report compatibility problems through GitHub Issues with your Home Assistant version, Pi-Star version, and relevant log output.

## License

MIT
