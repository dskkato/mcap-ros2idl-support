"""Python port of the ``cdr`` TypeScript library.

At this stage the port only includes a subset of the original project –
primarily enumerations and small utility helpers.  The public API mirrors
``src/index.ts`` of the original repository by re-exporting the
implemented components.
"""

from __future__ import annotations

from mcap_ros2idl_support.cdr.encapsulation_kind import EncapsulationKind
from mcap_ros2idl_support.cdr.get_encapsulation_kind_info import (
    EncapsulationInfo,
    get_encapsulation_kind_info,
)
from mcap_ros2idl_support.cdr.is_big_endian import is_big_endian
from mcap_ros2idl_support.cdr.length_codes import (
    LengthCode,
    LengthCodeError,
    get_length_code_for_object_size,
    length_code_to_object_sizes,
)
from mcap_ros2idl_support.cdr.reader import CdrReader
from mcap_ros2idl_support.cdr.reserved_pids import EXTENDED_PID, SENTINEL_PID
from mcap_ros2idl_support.cdr.size_calculator import CdrSizeCalculator
from mcap_ros2idl_support.cdr.writer import CdrWriter

__all__ = [
    "EncapsulationKind",
    "EncapsulationInfo",
    "get_encapsulation_kind_info",
    "is_big_endian",
    "LengthCode",
    "LengthCodeError",
    "get_length_code_for_object_size",
    "length_code_to_object_sizes",
    "CdrReader",
    "CdrWriter",
    "CdrSizeCalculator",
    "EXTENDED_PID",
    "SENTINEL_PID",
]
