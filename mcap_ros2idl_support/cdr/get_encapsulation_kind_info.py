"""Utility helpers for :class:`~cdr.encapsulation_kind.EncapsulationKind`."""

from __future__ import annotations

from dataclasses import dataclass

from mcap_ros2idl_support.cdr.encapsulation_kind import EncapsulationKind


@dataclass(frozen=True)
class EncapsulationInfo:
    """Information about the behaviour of an :class:`EncapsulationKind`.

    Attributes correspond to the flags described in the TypeScript
    implementation.  They are primarily used by the reader and writer to
    determine how a payload should be serialised or parsed.
    """

    is_cdr2: bool
    little_endian: bool
    uses_delimiter_header: bool
    uses_member_header: bool


def get_encapsulation_kind_info(kind: EncapsulationKind) -> EncapsulationInfo:
    """Return information about a given ``EncapsulationKind``.

    Parameters
    ----------
    kind:
        The :class:`EncapsulationKind` to inspect.

    Returns
    -------
    EncapsulationInfo
        A data object describing whether the kind is CDR2, little endian
        and whether it uses delimiter or member headers.
    """

    # ``Enum`` members do not support ordering comparisons directly, so we
    # compare using their underlying integer values.
    is_cdr2 = kind.value > EncapsulationKind.PL_CDR_LE.value

    little_endian = kind in {
        EncapsulationKind.CDR_LE,
        EncapsulationKind.PL_CDR_LE,
        EncapsulationKind.CDR2_LE,
        EncapsulationKind.PL_CDR2_LE,
        EncapsulationKind.DELIMITED_CDR2_LE,
        EncapsulationKind.RTPS_CDR2_LE,
        EncapsulationKind.RTPS_PL_CDR2_LE,
        EncapsulationKind.RTPS_DELIMITED_CDR2_LE,
    }

    is_delimited_cdr2 = kind in {
        EncapsulationKind.DELIMITED_CDR2_BE,
        EncapsulationKind.DELIMITED_CDR2_LE,
        EncapsulationKind.RTPS_DELIMITED_CDR2_BE,
        EncapsulationKind.RTPS_DELIMITED_CDR2_LE,
    }

    is_pl_cdr2 = kind in {
        EncapsulationKind.PL_CDR2_BE,
        EncapsulationKind.PL_CDR2_LE,
        EncapsulationKind.RTPS_PL_CDR2_BE,
        EncapsulationKind.RTPS_PL_CDR2_LE,
    }

    is_pl_cdr1 = kind in {
        EncapsulationKind.PL_CDR_BE,
        EncapsulationKind.PL_CDR_LE,
    }

    uses_delimiter_header = is_delimited_cdr2 or is_pl_cdr2
    uses_member_header = is_pl_cdr2 or is_pl_cdr1

    return EncapsulationInfo(
        is_cdr2=is_cdr2,
        little_endian=little_endian,
        uses_delimiter_header=uses_delimiter_header,
        uses_member_header=uses_member_header,
    )
