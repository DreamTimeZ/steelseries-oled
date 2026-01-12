"""GameSense API backend for stats display.

Uses SteelSeries GG's HTTP JSON API to display stats via text mode.
Works with all keyboards including Gen3.
"""

import json
import logging
import time
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from steelseries_oled.backends.base import StatsBackend
from steelseries_oled.exceptions import DeviceCommunicationError, DeviceNotFoundError
from steelseries_oled.models import SystemStats, format_rate

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# GameSense configuration
GAME_NAME = "STEELSERIES_OLED"
GAME_DISPLAY_NAME = "SteelSeries OLED Stats"
EVENT_NAME = "STATS_UPDATE"

# HTTP configuration for robustness
HTTP_TIMEOUT = 2.0
MAX_RETRIES = 2
RETRY_DELAY = 0.1
HTTP_OK = 200
HTTP_NOT_FOUND = 404

# Paths to SteelSeries GG configuration
CORE_PROPS_PATHS = [
    Path(r"C:\ProgramData\SteelSeries\SteelSeries Engine 3\coreProps.json"),
    Path.home() / "Library/Application Support/SteelSeries Engine 3/coreProps.json",
]


def _ensure_requests() -> Any:
    """Ensure requests library is available."""
    if not REQUESTS_AVAILABLE:
        msg = (
            "The 'requests' library is required for GameSense backend. "
            "Install with: uv add requests"
        )
        raise ImportError(msg)
    return requests


def find_gamesense_address() -> tuple[str, int] | None:
    """Find the SteelSeries GG GameSense API address.

    Returns:
        Tuple of (host, port) if found, None otherwise.
    """
    for path in CORE_PROPS_PATHS:
        if path.exists():
            try:
                with path.open() as f:
                    data = json.load(f)
                address = data.get("address", "")
                if ":" in address:
                    host, port_str = address.split(":", 1)
                    return host, int(port_str)
            except (json.JSONDecodeError, ValueError, OSError) as e:
                logger.debug("Failed to parse %s: %s", path, e)
                continue
    return None


def is_gamesense_available() -> bool:
    """Check if SteelSeries GG GameSense API is available.

    Returns:
        True if GG is installed and running, False otherwise.
    """
    if not REQUESTS_AVAILABLE:
        return False

    result = find_gamesense_address()
    if result is None:
        return False

    # Try to connect
    try:
        host, port = result
        response = requests.get(
            f"http://{host}:{port}/",
            timeout=HTTP_TIMEOUT,
        )
        # 404 is OK, means server is up but endpoint doesn't exist
        return response.status_code in (HTTP_OK, HTTP_NOT_FOUND)
    except OSError:
        return False


class GameSenseBackend(StatsBackend):
    """GameSense API backend using text mode.

    Displays stats as text on the OLED via SteelSeries GG's HTTP API.
    Works with all keyboards including Gen3.

    Requires:
        - SteelSeries GG installed and running
        - 'requests' library installed
    """

    def __init__(self) -> None:
        """Initialize the GameSense backend."""
        self._base_url: str | None = None
        self._registered = False
        self._req: Any = None
        self._session: Any = None

    @property
    def name(self) -> str:
        """Return the backend name."""
        return "GameSense"

    def __enter__(self) -> Self:
        """Initialize connection to SteelSeries GG."""
        self._req = _ensure_requests()
        self._session = self._req.Session()

        try:
            # Find GG address
            result = find_gamesense_address()
            if result is None:
                msg = (
                    "SteelSeries GG not found. "
                    "Ensure SteelSeries GG is installed and running."
                )
                raise DeviceNotFoundError(msg)

            host, port = result
            self._base_url = f"http://{host}:{port}"

            # Verify connection
            if not self._verify_connection():
                msg = (
                    "Cannot connect to SteelSeries GG. "
                    "Ensure SteelSeries GG is running."
                )
                raise DeviceCommunicationError(msg)

            # Register game and bind event
            self._register_game()
            self._bind_stats_event()
            self._registered = True

            return self
        except BaseException:
            self._session.close()
            self._session = None
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Clean up: unregister game from GameSense."""
        if self._registered and self._base_url:
            try:
                self._post("/remove_game", {"game": GAME_NAME})
            except Exception as e:
                # Log but don't raise - we're cleaning up
                logger.debug("Failed to unregister game: %s", e)
        self._registered = False
        self._base_url = None
        if self._session is not None:
            self._session.close()
            self._session = None

    def update_stats(self, stats: SystemStats) -> None:
        """Update the OLED display with current stats.

        Args:
            stats: System statistics to display.
        """
        if not self._registered:
            msg = "Backend not initialized"
            raise DeviceCommunicationError(msg)

        # Line 1: CPU + GPU (adaptive)
        line1_parts = [f"C:{stats.cpu_percent:3.0f}%"]
        if stats.cpu_temp is not None:
            line1_parts.append(f"{stats.cpu_temp:.0f}C")
        if stats.gpu_percent is not None:
            line1_parts.append(f"G:{stats.gpu_percent:.0f}%")
            if stats.gpu_temp is not None:
                line1_parts.append(f"{stats.gpu_temp:.0f}C")
        line1 = " ".join(line1_parts)

        # Line 2: RAM
        line2 = f"RAM:{stats.mem_used_gb:.1f}/{stats.mem_total_gb:.0f}GB"

        # Line 3: Network (download first - users care more about it)
        up = format_rate(stats.net_up_bytes)
        down = format_rate(stats.net_down_bytes)
        line3 = f"D:{down} U:{up}"

        # Send stats event with frame data for multi-line display
        self._post(
            "/game_event",
            {
                "game": GAME_NAME,
                "event": EVENT_NAME,
                "data": {
                    "value": int(stats.cpu_percent),
                    "frame": {
                        "line1": line1,
                        "line2": line2,
                        "line3": line3,
                    },
                },
            },
        )

    def _verify_connection(self) -> bool:
        """Verify connection to SteelSeries GG."""
        try:
            response = self._session.get(
                f"{self._base_url}/",
                timeout=HTTP_TIMEOUT,
            )
            # 404 is OK, means server is up but endpoint doesn't exist
            return response.status_code in (HTTP_OK, HTTP_NOT_FOUND)
        except OSError:
            return False

    def _register_game(self) -> None:
        """Register our game with GameSense."""
        self._post(
            "/game_metadata",
            {
                "game": GAME_NAME,
                "game_display_name": GAME_DISPLAY_NAME,
                "developer": "steelseries-oled",
                "deinitialize_timer_length_ms": 30000,
            },
        )

    def _bind_stats_event(self) -> None:
        """Bind the stats display event handler."""
        self._post(
            "/bind_game_event",
            {
                "game": GAME_NAME,
                "event": EVENT_NAME,
                "handlers": [
                    {
                        "device-type": "screened-128x40",
                        "zone": "one",
                        "mode": "screen",
                        "datas": [
                            {
                                "lines": [
                                    {
                                        "has-text": True,
                                        "context-frame-key": "line1",
                                    },
                                    {
                                        "has-text": True,
                                        "context-frame-key": "line2",
                                    },
                                    {
                                        "has-text": True,
                                        "context-frame-key": "line3",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
        )

    def _post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to GameSense API with retry logic.

        Args:
            endpoint: API endpoint (e.g., "/game_event").
            data: JSON data to send.

        Returns:
            Response JSON data.

        Raises:
            DeviceCommunicationError: If request fails after retries.
        """
        url = f"{self._base_url}{endpoint}"
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._session.post(
                    url,
                    json=data,
                    timeout=HTTP_TIMEOUT,
                )
                response.raise_for_status()
                try:
                    return response.json() if response.text else {}
                except json.JSONDecodeError:
                    return {}
            except self._req.exceptions.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                break

        # Timeout can manifest as exception OR HTTP 500 with timeout in error body
        # (GG proxies to internal service which may timeout)
        error_str = str(last_error).lower()
        is_timeout = isinstance(last_error, self._req.exceptions.Timeout)
        if is_timeout or "timed out" in error_str or "timeout" in error_str:
            msg = "GameSense API timed out. Try restarting SteelSeries GG."
        else:
            msg = f"GameSense API request failed: {last_error}"
        raise DeviceCommunicationError(msg) from last_error
