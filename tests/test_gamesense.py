"""Tests for GameSense backend module."""

import json
from pathlib import Path
from unittest.mock import patch

from steelseries_oled.backends.gamesense import find_gamesense_address


class TestFindGamesenseAddress:
    """Tests for find_gamesense_address function."""

    def test_parses_valid_config(self, tmp_path: Path) -> None:
        """Should parse valid coreProps.json and return host/port tuple."""
        config = {"address": "127.0.0.1:12345"}
        config_path = tmp_path / "coreProps.json"
        config_path.write_text(json.dumps(config))

        with patch(
            "steelseries_oled.backends.gamesense.CORE_PROPS_PATHS", [config_path]
        ):
            result = find_gamesense_address()

        assert result == ("127.0.0.1", 12345)

    def test_malformed_json(self, tmp_path: Path) -> None:
        """Should return None for malformed JSON."""
        config_path = tmp_path / "coreProps.json"
        config_path.write_text("not valid json {{{")

        with patch(
            "steelseries_oled.backends.gamesense.CORE_PROPS_PATHS", [config_path]
        ):
            result = find_gamesense_address()

        assert result is None

    def test_invalid_port(self, tmp_path: Path) -> None:
        """Should return None when port is not a valid integer."""
        config = {"address": "127.0.0.1:notanumber"}
        config_path = tmp_path / "coreProps.json"
        config_path.write_text(json.dumps(config))

        with patch(
            "steelseries_oled.backends.gamesense.CORE_PROPS_PATHS", [config_path]
        ):
            result = find_gamesense_address()

        assert result is None
