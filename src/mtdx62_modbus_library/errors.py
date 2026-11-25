"""Errors raised by this library.

Only conditions the library itself decides are represented here. Errors of the
exchange — timeouts, protocol faults, refusals — are raised by
``modbus-connection`` and pass through untouched, so a caller can tell a silent
device from a rejected value.
"""

from __future__ import annotations

from typing import Any


class Mtdx62Error(Exception):
    """Base class for errors raised by this library."""


class WriteVerificationError(Mtdx62Error):
    """The device stores a different value than the one that was written.

    The write itself succeeded: the device accepted the frame. What it kept is
    known only from the read that follows, and here it differs from the request.
    """

    def __init__(self, field: str, requested: Any, stored: Any) -> None:
        """Remember what was asked for and what the device reports."""
        self.field = field
        self.requested = requested
        self.stored = stored
        super().__init__(f"{field}: wrote {requested!r}, the device reports {stored!r}")
