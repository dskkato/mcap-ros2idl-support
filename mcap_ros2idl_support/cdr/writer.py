"""CDR writer implementation.

This module ports the TypeScript ``CdrWriter`` to Python.  A mutable
``bytearray`` acts as the backing buffer and numerical values are written
using :func:`struct.pack_into`.  Only the parts of the original class used
elsewhere in the project are implemented.
"""

from __future__ import annotations

import struct
from array import array as Array
from typing import Sequence, cast

try:  # Python 3.12+
    from collections.abc import Buffer
except ImportError:  # Python <3.12
    from typing_extensions import Buffer

from mcap_ros2idl_support.cdr.encapsulation_kind import EncapsulationKind
from mcap_ros2idl_support.cdr.get_encapsulation_kind_info import (
    get_encapsulation_kind_info,
)
from mcap_ros2idl_support.cdr.is_big_endian import is_big_endian
from mcap_ros2idl_support.cdr.length_codes import (
    LengthCode,
    get_length_code_for_object_size,
    length_code_to_object_sizes,
)
from mcap_ros2idl_support.cdr.reserved_pids import EXTENDED_PID, SENTINEL_PID


class CdrWriter:
    """Serialise primitive values into a CDR formatted byte stream."""

    DEFAULT_CAPACITY = 16
    _ITEMSIZE = {
        "h": 2,
        "H": 2,
        "i": 4,
        "I": 4,
        "q": 8,
        "Q": 8,
        "f": 4,
        "d": 8,
    }

    def __init__(
        self,
        *,
        buffer: bytearray | bytes | None = None,
        size: int | None = None,
        kind: EncapsulationKind = EncapsulationKind.CDR_LE,
    ) -> None:
        if buffer is not None:
            self._buffer = bytearray(buffer)
        elif size is not None:
            self._buffer = bytearray(size)
        else:
            self._buffer = bytearray(self.DEFAULT_CAPACITY)

        info = get_encapsulation_kind_info(kind)
        self._little_endian = info.little_endian
        self._host_little_endian = not is_big_endian()
        self._is_cdr2 = info.is_cdr2
        self._eight_byte_alignment = 4 if self._is_cdr2 else 8

        self._offset = 0
        self._origin = 0

        # Representation identifier and options field
        self._resize_if_needed(4)
        self._buffer[0] = 0
        self._buffer[1] = kind.value
        struct.pack_into(">H", self._buffer, 2, 0)
        self._offset = 4
        self._origin = 4

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def data(self) -> bytes:
        """Return the written portion of the buffer."""

        return bytes(self._buffer[: self._offset])

    @property
    def size(self) -> int:
        """Current size of the written data."""

        return self._offset

    @property
    def kind(self) -> EncapsulationKind:
        """Encapsulation kind used by this writer."""

        return EncapsulationKind(self._buffer[1])

    # ------------------------------------------------------------------
    # Primitive writers
    # ------------------------------------------------------------------
    def int8(self, value: int) -> CdrWriter:
        self._resize_if_needed(1)
        struct.pack_into("b", self._buffer, self._offset, value)
        self._offset += 1
        return self

    def uint8(self, value: int) -> CdrWriter:
        self._resize_if_needed(1)
        struct.pack_into("B", self._buffer, self._offset, value)
        self._offset += 1
        return self

    def int16(self, value: int) -> CdrWriter:
        self.align(2)
        struct.pack_into(self._endian_fmt("h"), self._buffer, self._offset, value)
        self._offset += 2
        return self

    def uint16(self, value: int) -> CdrWriter:
        self.align(2)
        struct.pack_into(self._endian_fmt("H"), self._buffer, self._offset, value)
        self._offset += 2
        return self

    def int32(self, value: int) -> CdrWriter:
        self.align(4)
        struct.pack_into(self._endian_fmt("i"), self._buffer, self._offset, value)
        self._offset += 4
        return self

    def uint32(self, value: int) -> CdrWriter:
        self.align(4)
        struct.pack_into(self._endian_fmt("I"), self._buffer, self._offset, value)
        self._offset += 4
        return self

    def int64(self, value: int) -> CdrWriter:
        self.align(self._eight_byte_alignment, 8)
        struct.pack_into(self._endian_fmt("q"), self._buffer, self._offset, int(value))
        self._offset += 8
        return self

    def uint64(self, value: int) -> CdrWriter:
        self.align(self._eight_byte_alignment, 8)
        struct.pack_into(self._endian_fmt("Q"), self._buffer, self._offset, int(value))
        self._offset += 8
        return self

    def uint16BE(self, value: int) -> CdrWriter:
        self.align(2)
        struct.pack_into(">H", self._buffer, self._offset, value)
        self._offset += 2
        return self

    def uint32BE(self, value: int) -> CdrWriter:
        self.align(4)
        struct.pack_into(">I", self._buffer, self._offset, value)
        self._offset += 4
        return self

    def uint64BE(self, value: int) -> CdrWriter:
        self.align(self._eight_byte_alignment, 8)
        struct.pack_into(">Q", self._buffer, self._offset, int(value))
        self._offset += 8
        return self

    def float32(self, value: float) -> CdrWriter:
        self.align(4)
        struct.pack_into(self._endian_fmt("f"), self._buffer, self._offset, value)
        self._offset += 4
        return self

    def float64(self, value: float) -> CdrWriter:
        self.align(self._eight_byte_alignment, 8)
        struct.pack_into(self._endian_fmt("d"), self._buffer, self._offset, value)
        self._offset += 8
        return self

    # ------------------------------------------------------------------
    # Helper writers
    # ------------------------------------------------------------------
    def string(self, value: str, writeLength: bool = True) -> CdrWriter:
        data = value.encode("utf-8")
        if writeLength:
            self.uint32(len(data) + 1)
        self._resize_if_needed(len(data) + 1)
        self._buffer[self._offset : self._offset + len(data)] = data
        self._buffer[self._offset + len(data)] = 0
        self._offset += len(data) + 1
        return self

    def dHeader(self, objectSize: int) -> CdrWriter:
        """Write a delimiter header using ``objectSize``."""

        return self.uint32(objectSize)

    def emHeader(
        self,
        mustUnderstand: bool,
        id: int,
        objectSize: int,
        lengthCode: LengthCode | None = None,
    ) -> CdrWriter:
        if self._is_cdr2:
            return self._member_header_v2(mustUnderstand, id, objectSize, lengthCode)
        return self._member_header_v1(mustUnderstand, id, objectSize)

    def sentinelHeader(self) -> CdrWriter:
        if not self._is_cdr2:
            self.align(4)
            self.uint16(SENTINEL_PID)
            self.uint16(0)
        return self

    def sequenceLength(self, value: int) -> CdrWriter:
        return self.uint32(value)

    # ------------------------------------------------------------------
    # Array writers with bulk copy optimisations
    # ------------------------------------------------------------------
    def int8Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if writeLength:
            self.sequenceLength(len(value))
        if isinstance(value, (bytes, bytearray)):
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
        elif isinstance(value, Array) and value.typecode in ("b", "B"):
            n = len(value)
            self._resize_if_needed(n)
            mv = memoryview(value).cast("B")
            self._buffer[self._offset : self._offset + n] = mv
            self._offset += n
        else:
            for entry in value:
                self.int8(entry)
        return self

    def uint8Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if writeLength:
            self.sequenceLength(len(value))
        if isinstance(value, (bytes, bytearray)):
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
        elif isinstance(value, Array) and value.typecode in ("b", "B"):
            n = len(value)
            self._resize_if_needed(n)
            mv = memoryview(value).cast("B")
            self._buffer[self._offset : self._offset + n] = mv
            self._offset += n
        else:
            for entry in value:
                self.uint8(entry)
        return self

    def int16Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 2)
            self.align(2, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(value, "h", 2, writeLength):
            return self
        if isinstance(value, Array) and value.typecode == "h":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(2, n * 2)
            self._resize_if_needed(n * 2)
            struct.pack_into(
                self._endian_fmt(f"{n}h"), self._buffer, self._offset, *value
            )
            self._offset += n * 2
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.int16(entry)
        return self

    def uint16Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 2)
            self.align(2, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(value, "H", 2, writeLength):
            return self
        if isinstance(value, Array) and value.typecode == "H":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(2, n * 2)
            self._resize_if_needed(n * 2)
            struct.pack_into(
                self._endian_fmt(f"{n}H"), self._buffer, self._offset, *value
            )
            self._offset += n * 2
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.uint16(entry)
        return self

    def int32Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 4)
            self.align(4, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(value, "i", 4, writeLength):
            return self
        if isinstance(value, Array) and value.typecode == "i":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(4, n * 4)
            self._resize_if_needed(n * 4)
            struct.pack_into(
                self._endian_fmt(f"{n}i"), self._buffer, self._offset, *value
            )
            self._offset += n * 4
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.int32(entry)
        return self

    def uint32Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 4)
            self.align(4, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(value, "I", 4, writeLength):
            return self
        if isinstance(value, Array) and value.typecode == "I":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(4, n * 4)
            self._resize_if_needed(n * 4)
            struct.pack_into(
                self._endian_fmt(f"{n}I"), self._buffer, self._offset, *value
            )
            self._offset += n * 4
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.uint32(entry)
        return self

    def int64Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 8)
            self.align(self._eight_byte_alignment, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(
            value, "q", self._eight_byte_alignment, writeLength
        ):
            return self
        if isinstance(value, Array) and value.typecode == "q":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(self._eight_byte_alignment, n * 8)
            self._resize_if_needed(n * 8)
            struct.pack_into(
                self._endian_fmt(f"{n}q"), self._buffer, self._offset, *value
            )
            self._offset += n * 8
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.int64(int(entry))
        return self

    def uint64Array(
        self,
        value: Sequence[int] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 8)
            self.align(self._eight_byte_alignment, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(
            value, "Q", self._eight_byte_alignment, writeLength
        ):
            return self
        if isinstance(value, Array) and value.typecode == "Q":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(self._eight_byte_alignment, n * 8)
            self._resize_if_needed(n * 8)
            struct.pack_into(
                self._endian_fmt(f"{n}Q"), self._buffer, self._offset, *value
            )
            self._offset += n * 8
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.uint64(int(entry))
        return self

    def float32Array(
        self,
        value: Sequence[float] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 4)
            self.align(4, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(value, "f", 4, writeLength):
            return self
        if isinstance(value, Array) and value.typecode == "f":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(4, n * 4)
            self._resize_if_needed(n * 4)
            struct.pack_into(
                self._endian_fmt(f"{n}f"), self._buffer, self._offset, *value
            )
            self._offset += n * 4
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.float32(float(entry))
        return self

    def float64Array(
        self,
        value: Sequence[float] | bytes | bytearray | Array,
        writeLength: bool | None = False,
    ) -> CdrWriter:
        if isinstance(value, (bytes, bytearray)):
            if writeLength:
                self.sequenceLength(len(value) // 8)
            self.align(self._eight_byte_alignment, len(value))
            self._resize_if_needed(len(value))
            self._buffer[self._offset : self._offset + len(value)] = memoryview(value)
            self._offset += len(value)
            return self
        if self._try_write_contiguous(
            value, "d", self._eight_byte_alignment, writeLength
        ):
            return self
        if isinstance(value, Array) and value.typecode == "d":
            n = len(value)
            if writeLength:
                self.sequenceLength(n)
            self.align(self._eight_byte_alignment, n * 8)
            self._resize_if_needed(n * 8)
            struct.pack_into(
                self._endian_fmt(f"{n}d"), self._buffer, self._offset, *value
            )
            self._offset += n * 8
            return self
        if writeLength:
            self.sequenceLength(len(value))
        for entry in value:
            self.float64(float(entry))
        return self

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _try_write_contiguous(
        self,
        value: object,
        fmt_char: str,
        align: int,
        writeLength: bool | None,
    ) -> bool:
        """Attempt bulk copy from a contiguous typed buffer.

        ``fmt_char`` is the expected PEP-3118 format character (without any
        endianness prefix).  ``align`` is the alignment of the type in bytes.
        Returns ``True`` if the value was written using a bulk copy,
        ``False`` otherwise.
        """

        try:
            mv = memoryview(cast(Buffer, value))
        except TypeError:
            return False

        if not mv.c_contiguous or mv.itemsize != self._ITEMSIZE.get(fmt_char, 0):
            return False

        base = mv.format[-1]
        prefix = mv.format[:-1]
        if base != fmt_char:
            return False

        if prefix in ("", "@", "="):
            mv_little = self._host_little_endian
        elif prefix == "<":
            mv_little = True
        elif prefix in (">", "!"):
            mv_little = False
        else:
            return False

        if mv_little != self._little_endian:
            return False

        n = mv.nbytes // mv.itemsize
        if writeLength:
            self.sequenceLength(n)
        self.align(align, mv.nbytes)
        self._resize_if_needed(mv.nbytes)
        self._buffer[self._offset : self._offset + mv.nbytes] = mv.cast("B")
        self._offset += mv.nbytes
        return True

    def reset_origin(self) -> None:
        """Set the origin used for alignment to the current offset."""

        self._origin = self._offset

    def align(self, size: int, bytesToWrite: int | None = None) -> None:
        if bytesToWrite is None:
            bytesToWrite = size
        if size <= 0:
            self._resize_if_needed(bytesToWrite)
            return
        alignment = (self._offset - self._origin) % size
        padding = size - alignment if alignment > 0 else 0
        self._resize_if_needed(padding + bytesToWrite)
        for _ in range(padding):
            self._buffer[self._offset] = 0
            self._offset += 1

    def _endian_fmt(self, fmt: str) -> str:
        return ("<" if self._little_endian else ">") + fmt

    def _resize_if_needed(self, additional: int) -> None:
        capacity = self._offset + additional
        if len(self._buffer) < capacity:
            doubled = len(self._buffer) * 2
            new_capacity = doubled if doubled > capacity else capacity
            self._resize(new_capacity)

    def _resize(self, capacity: int) -> None:
        if len(self._buffer) >= capacity:
            return
        self._buffer.extend(b"\x00" * (capacity - len(self._buffer)))

    def _member_header_v1(
        self, mustUnderstand: bool, id: int, objectSize: int
    ) -> CdrWriter:
        self.align(4)
        must_flag = (1 << 14) if mustUnderstand else 0
        use_extended = id > 0x3F00 or objectSize > 0xFFFF
        if not use_extended:
            self.uint16(must_flag | id)
            self.uint16(objectSize & 0xFFFF)
        else:
            self.uint16(must_flag | EXTENDED_PID)
            self.uint16(8)
            self.uint32(id)
            self.uint32(objectSize)
        self.reset_origin()
        return self

    def _member_header_v2(
        self,
        mustUnderstand: bool,
        id: int,
        objectSize: int,
        lengthCode: LengthCode | None,
    ) -> CdrWriter:
        if id > 0x0FFFFFFF:
            raise ValueError(
                "Member ID %d is too large. Max value is %d" % (id, 0x0FFFFFFF)
            )

        must_flag = (1 << 31) if mustUnderstand else 0
        final_length_code: LengthCode = (
            lengthCode
            if lengthCode is not None
            else get_length_code_for_object_size(objectSize)
        )
        header = must_flag | (final_length_code << 28) | id
        self.uint32(header)

        if final_length_code in (0, 1, 2, 3):
            should_be = length_code_to_object_sizes[final_length_code]
            if objectSize != should_be:
                raise ValueError(
                    (
                        "Cannot write a length code %d header with an object size not "
                        "equal to %d"
                    )
                    % (final_length_code, should_be)
                )
        elif final_length_code in (4, 5):
            self.uint32(objectSize)
        elif final_length_code == 6:
            if objectSize % 4 != 0:
                raise ValueError(
                    (
                        "Cannot write a length code 6 header with an object size "
                        "that is not a multiple of 4"
                    )
                )
            self.uint32(objectSize >> 2)
        elif final_length_code == 7:
            if objectSize % 8 != 0:
                raise ValueError(
                    (
                        "Cannot write a length code 7 header with an object size "
                        "that is not a multiple of 8"
                    )
                )
            self.uint32(objectSize >> 3)
        else:
            raise ValueError("Unexpected length code %d" % final_length_code)

        return self
