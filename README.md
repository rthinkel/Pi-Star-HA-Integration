# Pi-Star Home Assistant Integration

A custom Home Assistant integration for monitoring a Pi-Star digital voice hotspot. It polls the local Pi-Star dashboard and exposes hotspot, DMR network, radio, last-heard, and local RF activity as Home Assistant sensors.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Open the menu in the upper-right and choose **Custom repositories**.
3. Add `https://github.com/rthinkel/Pi-Star-HA-Integration` as an **Integration** repository.
4. Open **Pi-Star** in HACS and choose **Download**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration** and search for **Pi-Star**.
7. Enter the Pi-Star hostname or IP address and dashboard credentials.

The default values are `pi-star.local`, username `pi-star`, and password `raspberry`. Use the credentials configured on your hotspot if they differ.

## Manual installation

Copy `custom_components/pistar` into your Home Assistant configuration directory so the final path is:

```text
/config/custom_components/pistar/
```

Restart Home Assistant, then add **Pi-Star** from **Settings > Devices & services**.

## Sensors

The integration currently exposes sensors for:

- Hotspot status, firmware, and transceiver status
- DMR network status, DMR ID, color code, timeslot status, and master
- TX and RX frequency
- Gateway last-heard callsign, talkgroup, mode, source, duration, loss, and BER
- Current transmit state
- Local RF last-heard callsign, talkgroup, mode, duration, BER, and RSSI

## Notes

- This integration uses local polling over HTTP and does not require a cloud service.
- Pi-Star dashboard HTML can vary between versions. If a Pi-Star update changes the dashboard markup, some parsed sensors may need to be updated.
- This project is an independent Home Assistant integration and is not part of the Pi-Star project or Home Assistant Core.

## Issues

Report bugs or compatibility problems in the repository's GitHub Issues section. Include your Home Assistant version, Pi-Star version, and relevant Home Assistant log output when possible.
