"""Helpers for determining system endianness."""

from __future__ import annotations

import sys


def is_big_endian() -> bool:
    """Return ``True`` if the current system uses big-endian byte order.

    The TypeScript implementation inspects an ``ArrayBuffer`` to determine
    endianness.  In Python we can rely on :mod:`sys` which exposes the
    interpreter's byte order via :data:`sys.byteorder`.
    """

    return sys.byteorder == "big"
