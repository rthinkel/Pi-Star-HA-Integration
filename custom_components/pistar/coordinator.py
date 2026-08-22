"""Pi-Star data coordinator."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

from bs4 import BeautifulSoup
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    PiStarAuthenticationError,
    PiStarClient,
    PiStarError,
    PiStarNotFoundError,
    PiStarResponseError,
)

_LOGGER = logging.getLogger(__name__)

REPEATER_INFO_PATH = "/mmdvmhost/repeaterinfo.php"
LAST_HEARD_API_PATH = "/api/last_heard.php"
LAST_HEARD_HTML_PATH = "/mmdvmhost/lh.php"
LOCAL_TX_HTML_PATH = "/mmdvmhost/localtx.php"

LAST_HEARD_DEFAULTS = {
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

LOCAL_RF_DEFAULTS = {
    "local_last_callsign": None,
    "local_last_tg": None,
    "local_last_mode": None,
    "local_last_ber": None,
    "local_last_rssi": None,
    "local_last_duration": None,
}

REPEATER_INFO_DEFAULTS = {
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

LOCAL_RF_MODES = {"D-Star", "YSF", "P25", "NXDN", "M17"}


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
        self._client = PiStarClient(
            async_get_clientsession(hass),
            host,
            username,
            password,
        )
        self._last_heard_api_supported: bool | None = None

    async def _async_update_data(self):
        """Fetch Pi-Star information and activity data."""
        info_result, activity_result = await asyncio.gather(
            self._client.async_get_text(REPEATER_INFO_PATH),
            self._async_fetch_activity(),
            return_exceptions=True,
        )

        for result in (info_result, activity_result):
            if isinstance(result, PiStarAuthenticationError):
                raise UpdateFailed(
                    "Pi-Star rejected the configured credentials"
                ) from result

        data = dict(self.data or {})
        successful_groups = 0
        failures: list[str] = []

        if isinstance(info_result, str):
            try:
                data.update(self._parse_repeater_info(info_result))
                successful_groups += 1
            except Exception as err:
                failures.append(f"repeater info parse failed: {err}")
                _LOGGER.warning("Could not parse Pi-Star repeater info: %s", err)
        else:
            failures.append(f"repeater info failed: {info_result}")
            _LOGGER.warning("Could not fetch Pi-Star repeater info: %s", info_result)

        if isinstance(activity_result, dict):
            data.update(activity_result)
            successful_groups += 1
        else:
            failures.append(f"activity failed: {activity_result}")
            _LOGGER.warning("Could not fetch Pi-Star activity: %s", activity_result)

        if successful_groups == 0:
            raise UpdateFailed("; ".join(failures) or "Could not reach Pi-Star")

        data["status"] = "online" if successful_groups == 2 else "degraded"
        return data

    async def _async_fetch_activity(self) -> dict[str, Any]:
        """Fetch structured activity, with HTML fallback for older dashboards."""
        if self._last_heard_api_supported is not False:
            try:
                payload = await self._client.async_get_json(LAST_HEARD_API_PATH)
            except PiStarNotFoundError:
                self._last_heard_api_supported = False
                _LOGGER.debug(
                    "Pi-Star last-heard JSON API is unavailable; using HTML fallback"
                )
            except PiStarAuthenticationError:
                raise
            except PiStarError as err:
                _LOGGER.debug(
                    "Pi-Star last-heard JSON API failed; using HTML fallback: %s",
                    err,
                )
            else:
                if isinstance(payload, list):
                    self._last_heard_api_supported = True
                    return self._parse_api_activity(payload)
                _LOGGER.warning(
                    "Pi-Star last-heard API returned an unexpected response; "
                    "using HTML fallback"
                )

        lh_result, local_result = await asyncio.gather(
            self._client.async_get_text(LAST_HEARD_HTML_PATH),
            self._client.async_get_text(LOCAL_TX_HTML_PATH),
            return_exceptions=True,
        )

        for result in (lh_result, local_result):
            if isinstance(result, PiStarAuthenticationError):
                raise result

        activity: dict[str, Any] = {}
        endpoint_success = False
        errors: list[str] = []

        if isinstance(lh_result, str):
            activity.update(self._parse_last_heard(lh_result))
            endpoint_success = True
        else:
            errors.append(f"last heard: {lh_result}")

        if isinstance(local_result, str):
            activity.update(self._parse_local_rf(local_result))
            endpoint_success = True
        else:
            errors.append(f"local TX: {local_result}")

        if not endpoint_success:
            raise PiStarResponseError(
                "Pi-Star activity endpoints failed (" + "; ".join(errors) + ")"
            )

        return activity

    def _parse_api_activity(self, payload: list[Any]) -> dict[str, Any]:
        """Parse Pi-Star's structured /api/last_heard.php response."""
        result: dict[str, Any] = {
            **LAST_HEARD_DEFAULTS,
            **LOCAL_RF_DEFAULTS,
        }
        rows = [row for row in payload if isinstance(row, dict)]
        if not rows:
            return result

        latest = rows[0]
        source = self._clean_value(latest.get("src"))
        duration = self._clean_value(latest.get("duration"))

        result.update(
            {
                "last_time": self._clean_value(latest.get("time_utc")),
                "last_callsign": self._clean_value(latest.get("callsign")),
                "last_tg": self._clean_value(latest.get("target")),
                "last_mode": self._normalize_mode(latest.get("mode")),
                "last_source": source,
                "last_duration": duration,
                "last_loss": self._clean_value(latest.get("loss")),
                "last_ber": self._clean_value(latest.get("bit_error_rate")),
                "currently_tx": duration is None
                and source is not None
                and source.casefold() != "rf",
            }
        )

        for row in rows:
            row_source = self._clean_value(row.get("src"))
            mode = self._normalize_mode(row.get("mode"))
            if (
                row_source is None
                or row_source.casefold() != "rf"
                or not self._is_local_rf_mode(mode)
            ):
                continue

            result.update(
                {
                    "local_last_callsign": self._clean_value(row.get("callsign")),
                    "local_last_tg": self._clean_value(row.get("target")),
                    "local_last_mode": mode,
                    "local_last_duration": self._clean_value(row.get("duration")),
                    "local_last_ber": self._clean_value(row.get("bit_error_rate")),
                    "local_last_rssi": self._clean_value(row.get("rssi")),
                }
            )
            break

        return result

    def _parse_last_heard(self, html: str) -> dict[str, Any]:
        """Parse /mmdvmhost/lh.php gateway activity."""
        result = dict(LAST_HEARD_DEFAULTS)
        soup = BeautifulSoup(html, "html.parser")
        row = self._first_data_row(soup, minimum_cells=5)
        if row is None:
            return result

        cells = row.find_all("td")
        source = self._cell_text(cells[4])
        result["last_time"] = self._cell_text(cells[0])
        result["last_mode"] = self._normalize_mode(self._cell_text(cells[1]))
        result["last_callsign"] = self._callsign_text(cells[2])
        result["last_tg"] = self._cell_text(cells[3])
        result["last_source"] = source

        if len(cells) == 6:
            result["currently_tx"] = (
                source is not None and source.casefold() != "rf"
            )
        elif len(cells) >= 8:
            result["last_duration"] = self._cell_text(cells[5])
            result["last_loss"] = self._cell_text(cells[6])
            result["last_ber"] = self._cell_text(cells[7])

        return result

    def _parse_repeater_info(self, html: str) -> dict[str, Any]:
        """Parse /mmdvmhost/repeaterinfo.php radio and network information."""
        result = dict(REPEATER_INFO_DEFAULTS)
        soup = BeautifulSoup(html, "html.parser")

        radio_labels = {
            "trx": "trx_status",
            "tx": "tx_frequency",
            "rx": "rx_frequency",
            "fw": "firmware",
        }
        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) != 2 or cells[0].name != "th":
                continue
            label = self._cell_text(cells[0])
            if label is None:
                continue
            key = radio_labels.get(label.casefold())
            if key is not None:
                result[key] = self._cell_text(cells[1])

        dmr_table = self._find_dmr_table(soup)
        if dmr_table is not None:
            self._parse_dmr_table(dmr_table, result)

        result["dmr_network"] = self._parse_dmr_network_status(soup)
        return result

    def _find_dmr_table(self, soup: BeautifulSoup):
        """Find the primary DMR repeater table, excluding cross-mode tables."""
        for table in soup.find_all("table"):
            text = " ".join(table.stripped_strings)
            if "DMR ID" in text and "DMR CC" in text:
                return table
        return None

    def _parse_dmr_table(self, table, result: dict[str, Any]) -> None:
        """Parse DMR repeater values and active master names from one table."""
        label_map = {
            "dmr id": "dmr_id",
            "dmr cc": "dmr_cc",
            "ts1": "ts1_status",
            "ts2": "ts2_status",
        }
        seen_ts2 = False
        masters: list[str] = []

        for row in table.find_all("tr", recursive=False):
            ths = row.find_all("th", recursive=False)
            tds = row.find_all("td", recursive=False)

            if len(ths) == 1 and len(tds) == 1:
                label = self._cell_text(ths[0])
                if label is not None:
                    key = label_map.get(label.casefold())
                    if key is not None:
                        result[key] = self._cell_text(tds[0])
                        if key == "ts2_status":
                            seen_ts2 = True
                    continue

            if not seen_ts2 or ths or not tds:
                continue

            value = " | ".join(
                text for cell in tds if (text := self._cell_text(cell))
            )
            if not value or value.casefold() == "no dmr network":
                continue
            if value not in masters:
                masters.append(value)

        if masters:
            result["dmr_master"] = " | ".join(masters)

    def _parse_dmr_network_status(self, soup: BeautifulSoup) -> str:
        """Translate Pi-Star's DMR Net status colour into a stable state."""
        for td in soup.find_all("td"):
            text = self._cell_text(td)
            if text is None or text.casefold() != "dmr net":
                continue

            style = re.sub(r"\s+", "", td.get("style", "").casefold())
            if "#0b0" in style or "#1d1" in style:
                return "connected"
            if "#ff9" in style:
                return "login_failed"
            if "#b00" in style or "#f00" in style:
                return "disconnected"
            if "#606060" in style:
                return "disabled"
            return "unknown"

        return "unknown"

    def _parse_local_rf(self, html: str) -> dict[str, Any]:
        """Parse /mmdvmhost/localtx.php local RF activity."""
        result = dict(LOCAL_RF_DEFAULTS)
        soup = BeautifulSoup(html, "html.parser")

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            source = self._cell_text(cells[4])
            if source is not None and source.casefold() == "rf":
                break
        else:
            return result

        result["local_last_mode"] = self._normalize_mode(self._cell_text(cells[1]))
        result["local_last_callsign"] = self._callsign_text(cells[2])
        result["local_last_tg"] = self._cell_text(cells[3])

        if len(cells) >= 8:
            result["local_last_duration"] = self._cell_text(cells[5])
            result["local_last_ber"] = self._cell_text(cells[6])
            result["local_last_rssi"] = self._cell_text(cells[7])

        return result

    @staticmethod
    def _first_data_row(soup: BeautifulSoup, minimum_cells: int):
        """Return the first table row that contains enough data cells."""
        for row in soup.find_all("tr"):
            if len(row.find_all("td")) >= minimum_cells:
                return row
        return None

    @classmethod
    def _callsign_text(cls, cell) -> str | None:
        """Return the visible callsign from a dashboard table cell."""
        link = cell.find("a")
        return cls._cell_text(link if link is not None else cell)

    @staticmethod
    def _cell_text(cell) -> str | None:
        """Normalize visible dashboard cell text."""
        if cell is None:
            return None
        return PiStarCoordinator._clean_value(cell.get_text(" ", strip=True))

    @staticmethod
    def _clean_value(value: Any) -> str | None:
        """Normalize a Pi-Star scalar value while preserving its content."""
        if value is None:
            return None
        text = str(value).replace("\xa0", " ").strip()
        return text or None

    @classmethod
    def _normalize_mode(cls, value: Any) -> str | None:
        """Normalize Pi-Star's DMR 'Slot N' display to its dashboard 'TSN' form."""
        text = cls._clean_value(value)
        if text is None:
            return None
        return text.replace("Slot ", "TS")

    @staticmethod
    def _is_local_rf_mode(mode: str | None) -> bool:
        """Return whether a mode belongs in Pi-Star's Local RF list."""
        if mode is None:
            return False
        return mode in LOCAL_RF_MODES or mode.startswith("DMR")
