"""Pi-Star data coordinator."""
import logging
from datetime import timedelta

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class PiStarCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch and parse Pi-Star dashboard data."""

    def __init__(self, hass, host, username, password, scan_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="Pi-Star",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.username = username
        self.password = password
        self._base_url = f"http://{host}"

    async def _fetch(self, session, path):
        """Fetch a Pi-Star URL and return the text, or None on failure."""
        auth = aiohttp.BasicAuth(self.username, self.password)
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with session.get(
                f"{self._base_url}{path}",
                auth=auth,
                timeout=timeout,
            ) as response:
                if response.status == 200:
                    return await response.text()
                _LOGGER.warning("Pi-Star %s returned HTTP %s", path, response.status)
                return None
        except aiohttp.ClientError as err:
            _LOGGER.warning("Pi-Star %s fetch error: %s", path, err)
            return None

    async def _async_update_data(self):
        """Fetch all Pi-Star sub-pages and merge into one data dict."""
        try:
            async with aiohttp.ClientSession() as session:
                lh_html = await self._fetch(session, "/mmdvmhost/lh.php")
                info_html = await self._fetch(session, "/mmdvmhost/repeaterinfo.php")
                local_html = await self._fetch(session, "/mmdvmhost/localtx.php")

            if lh_html is None and info_html is None:
                raise UpdateFailed("Could not reach Pi-Star — all endpoints failed")

            data = {"status": "online"}
            if lh_html:
                data.update(self._parse_last_heard(lh_html))
            if info_html:
                data.update(self._parse_repeater_info(info_html))
            if local_html:
                data.update(self._parse_local_rf(local_html))
            return data

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _parse_last_heard(self, html: str) -> dict:
        """Parse /mmdvmhost/lh.php gateway activity."""
        result = {
            "last_time": None,
            "last_callsign": None,
            "last_tg": None,
            "last_mode": None,
            "last_source": None,
            "last_ber": None,
            "last_loss": None,
            "last_duration": None,
            "currently_tx": False,
        }

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")
        data_rows = [row for row in rows if row.find("td")]
        if not data_rows:
            return result

        row = data_rows[0]
        cells = row.find_all("td")
        if len(cells) < 5:
            return result

        result["last_time"] = cells[0].get_text(strip=True)
        result["last_mode"] = cells[1].get_text(strip=True)

        call_a = cells[2].find("a")
        if call_a:
            result["last_callsign"] = call_a.get_text(strip=True)
        else:
            result["last_callsign"] = cells[2].get_text(strip=True)

        result["last_tg"] = cells[3].get_text(strip=True).replace("\xa0", " ")
        result["last_source"] = cells[4].get_text(strip=True)

        if len(cells) == 6:
            tx_text = cells[5].get_text(strip=True)
            if "TX" in tx_text:
                result["currently_tx"] = True
                result["last_duration"] = tx_text
        elif len(cells) >= 8:
            result["last_duration"] = cells[5].get_text(strip=True)
            result["last_loss"] = cells[6].get_text(strip=True)
            result["last_ber"] = cells[7].get_text(strip=True)

        return result

    def _parse_repeater_info(self, html: str) -> dict:
        """Parse /mmdvmhost/repeaterinfo.php radio and network information."""
        result = {
            "dmr_network": "unknown",
            "tx_frequency": None,
            "rx_frequency": None,
            "firmware": None,
            "trx_status": None,
            "dmr_id": None,
            "dmr_cc": None,
            "ts1_status": None,
            "ts2_status": None,
            "dmr_master": None,
        }

        soup = BeautifulSoup(html, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            if len(cells) == 2 and cells[0].name == "th":
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if label == "Trx":
                    result["trx_status"] = value
                elif label == "Tx":
                    result["tx_frequency"] = value
                elif label == "Rx":
                    result["rx_frequency"] = value
                elif label == "FW":
                    result["firmware"] = value
                elif label == "DMR ID":
                    result["dmr_id"] = value
                elif label == "DMR CC":
                    result["dmr_cc"] = value
                elif label == "TS1":
                    result["ts1_status"] = value
                elif label == "TS2":
                    result["ts2_status"] = value

            if len(cells) == 1 and cells[0].get("colspan"):
                text = cells[0].get_text(strip=True)
                skip = {
                    "DMR Repeater",
                    "DMR Master",
                    "Modes Enabled",
                    "Network Status",
                    "Radio Info",
                }
                if text and text not in skip:
                    result["dmr_master"] = text

        for td in soup.find_all("td"):
            if td.get_text(strip=True) == "DMR Net":
                style = td.get("style", "")
                if "#0b0" in style:
                    result["dmr_network"] = "connected"
                elif "#606060" in style:
                    result["dmr_network"] = "disconnected"
                break

        return result

    def _parse_local_rf(self, html: str) -> dict:
        """Parse /mmdvmhost/localtx.php local RF activity."""
        result = {
            "local_last_callsign": None,
            "local_last_tg": None,
            "local_last_mode": None,
            "local_last_ber": None,
            "local_last_rssi": None,
            "local_last_duration": None,
        }

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")
        data_rows = [row for row in rows if row.find("td")]
        if not data_rows:
            return result

        row = data_rows[0]
        cells = row.find_all("td")
        if len(cells) < 5:
            return result

        result["local_last_mode"] = cells[1].get_text(strip=True)

        call_a = cells[2].find("a")
        if call_a:
            result["local_last_callsign"] = call_a.get_text(strip=True)
        else:
            result["local_last_callsign"] = cells[2].get_text(strip=True)

        result["local_last_tg"] = cells[3].get_text(strip=True).replace("\xa0", " ")

        if len(cells) >= 8:
            result["local_last_duration"] = cells[5].get_text(strip=True)
            result["local_last_ber"] = cells[6].get_text(strip=True)
            result["local_last_rssi"] = cells[7].get_text(strip=True)

        return result
