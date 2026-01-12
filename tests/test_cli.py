"""Tests for CLI module."""

import argparse

from steelseries_oled.cli import cmd_profile, cmd_stats


class TestCmdStats:
    """Tests for cmd_stats command."""

    def test_invalid_interval_zero(self) -> None:
        """Should return 1 for zero interval."""
        args = argparse.Namespace(interval=0, font=None, backend="auto")
        result = cmd_stats(args)
        assert result == 1

    def test_invalid_interval_negative(self) -> None:
        """Should return 1 for negative interval."""
        args = argparse.Namespace(interval=-1.0, font=None, backend="auto")
        result = cmd_stats(args)
        assert result == 1


class TestCmdProfile:
    """Tests for cmd_profile command."""

    def test_negative_profile_number(self) -> None:
        """Should return 1 for negative profile number."""
        args = argparse.Namespace(profile_number=-1)
        result = cmd_profile(args)
        assert result == 1
