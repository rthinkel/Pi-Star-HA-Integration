# Pi-Star Home Assistant Integration

A custom Home Assistant integration for monitoring a Pi-Star digital voice hotspot. It polls the local Pi-Star dashboard and exposes hotspot, DMR network, radio, last-heard, and local RF activity as Home Assistant sensors. No cloud service is required.

## What it provides

- Hotspot status, firmware, and transceiver status
- DMR network status, ID, color code, timeslots, and master
- TX/RX frequencies
- Gateway last-heard callsign, talkgroup, mode, source, duration, loss, and BER
- Current transmit state
- Local RF callsign, talkgroup, mode, duration, BER, and RSSI

## Install with HACS

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/rthinkel/Pi-Star-HA-Integration` as an **Integration**.
3. Open **Pi-Star** in HACS and select **Download**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **Pi-Star**.
6. Enter the Pi-Star hostname/IP address, dashboard username and password, and desired polling interval.

Pi-Star commonly uses `pi-star.local`, username `pi-star`, and password `raspberry` by default. Use your hotspot's configured values if they differ.

## Manual installation

Copy `custom_components/pistar` into your Home Assistant configuration directory so the integration is located at:

```text
/config/custom_components/pistar/
```

Restart Home Assistant, then add **Pi-Star** from **Settings → Devices & services → Add integration**.

## Notes

The integration prefers Pi-Star's structured last-heard JSON API for activity data and automatically falls back to the legacy dashboard HTML endpoints when the API is unavailable. Partial endpoint failures retain the last valid data instead of dropping every sensor at once.

This project is independent and is not affiliated with Pi-Star or Home Assistant Core. Report problems through the repository's **Issues** page and include your Home Assistant version, Pi-Star version, and relevant log output when possible.

## License

MIT
