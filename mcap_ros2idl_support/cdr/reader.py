"""Implementation of a binary CDR reader.

This module provides a Python port of a subset of the original TypeScript
``CdrReader``.  It supports reading primitive values, strings and arrays from a
byte buffer while honouring the alignment and endianness rules defined by the
CDR specification.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Sequence, cast

from mcap_ros2idl_support.cdr.encapsulation_kind import EncapsulationKind
from mcap_ros2idl_support.cdr.get_encapsulation_kind_info import (
    get_encapsulation_kind_info,
)
from mcap_ros2idl_support.cdr.is_big_endian import is_big_endian
from mcap_ros2idl_support.cdr.length_codes import (
    LengthCode,
    length_code_to_object_sizes,
)
from mcap_ros2idl_support.cdr.reserved_pids import EXTENDED_PID, SENTINEL_PID

# Precompiled ``struct`` format objects to avoid repeatedly parsing the
# same format strings.  ``struct.Struct`` instances are considerably faster
# when used many times as they cache the parsing of the format.
_INT8 = struct.Struct("b")
_UINT8 = struct.Struct("B")
_INT16_LE = struct.Struct("<h")
_INT16_BE = struct.Struct(">h")
_UINT16_LE = struct.Struct("<H")
_UINT16_BE = struct.Struct(">H")
_INT32_LE = struct.Struct("<i")
_INT32_BE = struct.Struct(">i")
_UINT32_LE = struct.Struct("<I")
_UINT32_BE = struct.Struct(">I")
_INT64_LE = struct.Struct("<q")
_INT64_BE = struct.Struct(">q")
_UINT64_LE = struct.Struct("<Q")
_UINT64_BE = struct.Struct(">Q")
_FLOAT32_LE = struct.Struct("<f")
_FLOAT32_BE = struct.Struct(">f")
_FLOAT64_LE = struct.Struct("<d")
_FLOAT64_BE = struct.Struct(">d")

# Mapping from format character to item size.  Using a dictionary avoids the
# overhead of calling :func:`struct.calcsize` repeatedly when decoding arrays.
_ITEMSIZE = {
    "b": 1,
    "B": 1,
    "h": 2,
    "H": 2,
    "i": 4,
    "I": 4,
    "q": 8,
    "Q": 8,
    "f": 4,
    "d": 8,
}


@dataclass
class MemberHeader:
    """Representation of a member header read from the stream."""

    id: int
    object_size: int
    must_understand: bool
    length_code: LengthCode | None = None
    read_sentinel_header: bool | None = None


class CdrReader:
    """Read primitive values and arrays from a CDR encoded byte buffer."""

    def __init__(self, data: bytes | bytearray | memoryview) -> None:
        if isinstance(data, memoryview):
            self._view = data
        else:
            self._view = memoryview(data)

        if self._view.nbytes < 4:
            raise ValueError(
                f"Invalid CDR data size {self._view.nbytes}, "
                "must contain at least a 4-byte header",
            )

        # Encapsulation kind is encoded in the second byte of the header.
        kind = EncapsulationKind(self._view[1])
        info = get_encapsulation_kind_info(kind)

        self.little_endian = info.little_endian
        self.host_little_endian = not is_big_endian()
        self.is_cdr2 = info.is_cdr2
        self.eight_byte_alignment = 4 if self.is_cdr2 else 8
        self.uses_delimiter_header = info.uses_delimiter_header
        self.uses_member_header = info.uses_member_header

        # Pre-select struct objects and prefix based on endianness so that
        # primitive readers avoid branching and repeated format parsing.
        if self.little_endian:
            self._int16_struct = _INT16_LE
            self._uint16_struct = _UINT16_LE
            self._int32_struct = _INT32_LE
            self._uint32_struct = _UINT32_LE
            self._int64_struct = _INT64_LE
            self._uint64_struct = _UINT64_LE
            self._float32_struct = _FLOAT32_LE
            self._float64_struct = _FLOAT64_LE
            self._endian_prefix = "<"
        else:
            self._int16_struct = _INT16_BE
            self._uint16_struct = _UINT16_BE
            self._int32_struct = _INT32_BE
            self._uint32_struct = _UINT32_BE
            self._int64_struct = _INT64_BE
            self._uint64_struct = _UINT64_BE
            self._float32_struct = _FLOAT32_BE
            self._float64_struct = _FLOAT64_BE
            self._endian_prefix = ">"

        # Origin and current offset start immediately after the four byte header
        self.origin = 4
        self.offset = 4

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------
    @property
    def kind(self) -> EncapsulationKind:
        return EncapsulationKind(self._view[1])

    @property
    def decoded_bytes(self) -> int:
        return self.offset

    @property
    def byte_length(self) -> int:
        return self._view.nbytes

    # ------------------------------------------------------------------
    # Primitive readers
    # ------------------------------------------------------------------
    def int8(self) -> int:
        value = _INT8.unpack_from(self._view, self.offset)[0]
        self.offset += 1
        return value

    def uint8(self) -> int:
        value = _UINT8.unpack_from(self._view, self.offset)[0]
        self.offset += 1
        return value

    def int16(self) -> int:
        self.align(2)
        value = self._int16_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 2
        return value

    def uint16(self) -> int:
        self.align(2)
        value = self._uint16_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 2
        return value

    def int32(self) -> int:
        self.align(4)
        value = self._int32_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 4
        return value

    def uint32(self) -> int:
        self.align(4)
        value = self._uint32_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 4
        return value

    def int64(self) -> int:
        self.align(self.eight_byte_alignment)
        value = self._int64_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 8
        return value

    def uint64(self) -> int:
        self.align(self.eight_byte_alignment)
        value = self._uint64_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 8
        return value

    def uint16_be(self) -> int:
        self.align(2)
        value = _UINT16_BE.unpack_from(self._view, self.offset)[0]
        self.offset += 2
        return value

    def uint32_be(self) -> int:
        self.align(4)
        value = _UINT32_BE.unpack_from(self._view, self.offset)[0]
        self.offset += 4
        return value

    def uint64_be(self) -> int:
        self.align(self.eight_byte_alignment)
        value = _UINT64_BE.unpack_from(self._view, self.offset)[0]
        self.offset += 8
        return value

    def float32(self) -> float:
        self.align(4)
        value = self._float32_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 4
        return value

    def float64(self) -> float:
        self.align(self.eight_byte_alignment)
        value = self._float64_struct.unpack_from(self._view, self.offset)[0]
        self.offset += 8
        return value

    # ------------------------------------------------------------------
    # String and headers
    # ------------------------------------------------------------------
    def string(self, preread_length: int | None = None) -> str:
        length = preread_length or self.uint32()
        if length <= 1:
            self.offset += length
            return ""

        data = self._view[self.offset : self.offset + length - 1]
        value = data.tobytes().decode("utf-8")
        self.offset += length
        return value

    def d_header(self) -> int:
        """Read the delimiter header and return the object size."""

        return self.uint32()

    # ------------------------------------------------------------------
    # EMHEADER reading (used by XCDR2)
    # ------------------------------------------------------------------
    def em_header(self) -> MemberHeader:
        return self._member_header_v2() if self.is_cdr2 else self._member_header_v1()

    def _member_header_v1(self) -> MemberHeader:
        # XCDR1 PL_CDR encapsulation parameter header
        self.align(4)
        id_header = self.uint16()

        must_understand = ((id_header & 0x4000) >> 14) == 1
        implementation_specific = ((id_header & 0x8000) >> 15) == 1
        extended_pid = (id_header & 0x3FFF) == EXTENDED_PID
        sentinel_pid = (id_header & 0x3FFF) == SENTINEL_PID

        if sentinel_pid:
            return MemberHeader(
                id=SENTINEL_PID,
                object_size=0,
                must_understand=False,
                read_sentinel_header=True,
            )

        uses_reserved_pid = (id_header & 0x3FFF) > SENTINEL_PID
        if uses_reserved_pid or implementation_specific:
            raise ValueError(f"Unsupported parameter ID header {id_header:04x}")

        if extended_pid:
            # consume remaining part of the header
            self.uint16()

        pid = self.uint32() if extended_pid else id_header & 0x3FFF
        object_size = self.uint32() if extended_pid else self.uint16()
        self._reset_origin()
        return MemberHeader(
            id=pid,
            object_size=object_size,
            must_understand=must_understand,
        )

    def _member_header_v2(self) -> MemberHeader:
        header = self.uint32()
        must_understand = ((header & 0x80000000) >> 31) == 1
        length_code = cast(LengthCode, ((header & 0x70000000) >> 28) & 0x7)
        pid = header & 0x0FFFFFFF
        object_size = self._em_header_object_size(length_code)
        return MemberHeader(
            id=pid,
            object_size=object_size,
            must_understand=must_understand,
            length_code=length_code,
        )

    def _em_header_object_size(self, length_code: LengthCode) -> int:
        match length_code:
            case 0 | 1 | 2 | 3:
                return length_code_to_object_sizes[length_code]
            case 4 | 5:
                return self.uint32()
            case 6:
                return 4 * self.uint32()
            case 7:
                return 8 * self.uint32()
            case _:
                raise ValueError(
                    f"Invalid length code {length_code} in EMHEADER "
                    f"at offset {self.offset - 4}",
                )

    def _reset_origin(self) -> None:
        self.origin = self.offset

    def sentinel_header(self) -> None:
        """Read the PID_SENTINEL value if encapsulation supports it."""

        if not self.is_cdr2:
            self.align(4)
            header = self.uint16()
            sentinel_pid_flag = (header & 0x3FFF) == SENTINEL_PID
            if not sentinel_pid_flag:
                raise ValueError(
                    f"Expected SENTINEL_PID ({SENTINEL_PID:04x}) flag, "
                    f"but got {header:04x}",
                )
            self.uint16()

    # ------------------------------------------------------------------
    # Sequence helpers and array readers
    # ------------------------------------------------------------------
    def sequence_length(self) -> int:
        return self.uint32()

    # Array readers return a zero-copy ``memoryview`` when possible and fall back
    # to a Python ``list`` for incompatible cases (misalignment or mismatched
    # endianness).
    def int8_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("b", count, 1))

    def uint8_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("B", count, 1))

    def _array(
        self, fmt: str, count: int, alignment: int
    ) -> Sequence[int] | Sequence[float]:
        if count == 0:
            data = self._view[self.offset : self.offset]
            if self.little_endian == self.host_little_endian:
                return data.cast(cast(Any, fmt))
            return []

        self.align(alignment)
        size = _ITEMSIZE.get(fmt)
        if size is None:
            size = struct.calcsize(fmt)
        start = self.offset
        end = start + size * count
        data = self._view[start:end]
        self.offset = end

        if (
            self.little_endian == self.host_little_endian
            and (start - self.origin) % alignment == 0
        ):
            return data.cast(cast(Any, fmt))

        if size == 1:
            return list(data.cast(cast(Any, fmt)))

        values = struct.unpack(f"{self._endian_prefix}{count}{fmt}", data.tobytes())
        return list(values)

    def int16_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("h", count, 2))

    def uint16_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("H", count, 2))

    def int32_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("i", count, 4))

    def uint32_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("I", count, 4))

    def int64_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("q", count, self.eight_byte_alignment))

    def uint64_array(self, count: int | None = None) -> Sequence[int]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[int]", self._array("Q", count, self.eight_byte_alignment))

    def float32_array(self, count: int | None = None) -> Sequence[float]:
        count = self.sequence_length() if count is None else count
        return cast("Sequence[float]", self._array("f", count, 4))

    def float64_array(self, count: int | None = None) -> Sequence[float]:
        count = self.sequence_length() if count is None else count
        return cast(
            "Sequence[float]",
            self._array("d", count, self.eight_byte_alignment),
        )

    def string_array(self, count: int | None = None) -> list[str]:
        count = self.sequence_length() if count is None else count
        if count == 0:
            return []
        return [self.string() for _ in range(count)]

    # ------------------------------------------------------------------
    # Position helpers
    # ------------------------------------------------------------------
    def seek(self, relative_offset: int) -> None:
        new_offset = self.offset + relative_offset
        if new_offset < 4 or new_offset >= self._view.nbytes:
            raise ValueError(
                f"seek({relative_offset}) failed, "
                f"{new_offset} is outside the data range",
            )
        self.offset = new_offset

    def seek_to(self, offset: int) -> None:
        if offset < 4 or offset >= self._view.nbytes:
            raise ValueError(
                f"seekTo({offset}) failed, value is outside the data range"
            )
        self.offset = offset

    def clone(self) -> CdrReader:
        clone = CdrReader(self._view)
        clone.offset = self.offset
        clone.origin = self.origin
        return clone

    def limit(self, length: int) -> None:
        new_byte_length = self.offset + length
        if new_byte_length <= self._view.nbytes:
            self._view = self._view[:new_byte_length]
        else:
            raise ValueError(f"length {length} exceeds byte length of view")

    def is_at_end(self) -> bool:
        return self.offset >= self._view.nbytes

    # ------------------------------------------------------------------
    # Alignment helper
    # ------------------------------------------------------------------
    def align(self, size: int) -> None:
        alignment = (self.offset - self.origin) % size
        if alignment > 0:
            self.offset += size - alignment
