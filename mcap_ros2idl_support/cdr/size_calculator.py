"""Utility for computing CDR encoded message sizes.

This module provides a Python translation of the :code:`CdrSizeCalculator`
class from the original TypeScript implementation.  The calculator tracks an
internal offset which represents the number of bytes that would be written
when serialising values in CDR (Common Data Representation) format.  Each
method returns the new offset after accounting for padding and the size of the
written value.
"""

from __future__ import annotations


class CdrSizeCalculator:
    """Compute the number of bytes required for CDR serialisation."""

    # Two bytes for Representation Id and two bytes for Options
    def __init__(self) -> None:
        self._offset = 4

    @property
    def size(self) -> int:
        """Return the current offset in bytes."""

        return self._offset

    # Basic integer and floating point types ---------------------------------
    def int8(self) -> int:
        return self._increment_and_return(1)

    def uint8(self) -> int:
        return self._increment_and_return(1)

    def int16(self) -> int:
        return self._increment_and_return(2)

    def uint16(self) -> int:
        return self._increment_and_return(2)

    def int32(self) -> int:
        return self._increment_and_return(4)

    def uint32(self) -> int:
        return self._increment_and_return(4)

    def int64(self) -> int:
        return self._increment_and_return(8)

    def uint64(self) -> int:
        return self._increment_and_return(8)

    def float32(self) -> int:
        return self._increment_and_return(4)

    def float64(self) -> int:
        return self._increment_and_return(8)

    # Complex types -----------------------------------------------------------
    def string(self, length: int) -> int:
        """Account for a UTF-8 string of ``length`` characters.

        The string is prefixed by a 32-bit unsigned length field and suffixed
        by a null terminator.  The length parameter should reflect the number
        of bytes in the string *without* the terminator.
        """

        self.uint32()  # Encoded string length
        self._offset += length + 1  # Include null terminator
        return self._offset

    def sequence_length(self) -> int:
        """Account for the length field of a sequence."""

        return self.uint32()

    # Private helpers --------------------------------------------------------
    def _increment_and_return(self, byte_count: int) -> int:
        """Increment the offset by ``byte_count`` and any required padding.

        The CDR encoding requires that primitive types be aligned to their
        natural boundaries relative to the start of the CDR stream.  The stream
        begins with a four byte header, so alignment is performed on
        ``self._offset - 4``.
        """

        alignment = (self._offset - 4) % byte_count
        if alignment > 0:
            self._offset += byte_count - alignment
        self._offset += byte_count
        return self._offset
