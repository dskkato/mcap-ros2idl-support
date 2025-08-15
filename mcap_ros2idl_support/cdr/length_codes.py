"""Helpers for working with XCDR length codes."""

from __future__ import annotations

from typing import Dict, Literal

LengthCode = Literal[0, 1, 2, 3, 4, 5, 6, 7]


class LengthCodeError(ValueError):
    """Raised when an object size cannot be represented by a length code."""


_DEF_SIZES: Dict[int, LengthCode] = {1: 0, 2: 1, 4: 2, 8: 3}


def get_length_code_for_object_size(object_size: int) -> LengthCode:
    """Return the default length code for ``object_size``.

    Parameters
    ----------
    object_size:
        Size in bytes of the value to encode.

    Returns
    -------
    LengthCode
        The length code corresponding to ``object_size``.

    Raises
    ------
    LengthCodeError
        If ``object_size`` is larger than ``0xffffffff`` without an explicit
        length code.  This mirrors the behaviour of the TypeScript
        implementation.
    """

    if object_size in _DEF_SIZES:
        return _DEF_SIZES[object_size]

    if object_size > 0xFFFFFFFF:
        raise LengthCodeError(
            "Object size %d for EMHEADER too large without specifying length code. "
            "Max size is %d" % (object_size, 0xFFFFFFFF)
        )

    # For any other size up to the maximum, a length code of 4 is used.
    return 4


length_code_to_object_sizes: Dict[LengthCode, int] = {
    0: 1,
    1: 2,
    2: 4,
    3: 8,
}
