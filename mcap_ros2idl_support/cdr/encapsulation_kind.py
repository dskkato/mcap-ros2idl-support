"""Enumerations for CDR encapsulation kinds.

This mirrors the constants defined in the TypeScript library's
``EncapsulationKind`` enum.  The values originate from the
DDS-XTypes specification and are used to describe how data is
serialized within a CDR stream.
"""

from __future__ import annotations

from enum import Enum


class EncapsulationKind(Enum):
    """Enumeration of the various CDR encapsulation kinds.

    The member values match those used by the TypeScript implementation
    and the DDS-XTypes specification.  ``Enum`` is used instead of
    :class:`~enum.IntEnum` to provide a closer analogue to TypeScript's
    ``enum`` semantics; code that requires the numerical value should use
    the :attr:`value` attribute of each member.
    """

    # Plain CDR encodings
    CDR_BE = 0x00  # Plain CDR, big-endian
    CDR_LE = 0x01  # Plain CDR, little-endian

    # Parameter list CDR encodings (XCDR1)
    PL_CDR_BE = 0x02  # Parameter List CDR, big-endian
    PL_CDR_LE = 0x03  # Parameter List CDR, little-endian

    # XCDR2 encodings
    CDR2_BE = 0x10  # Plain CDR2, big-endian
    CDR2_LE = 0x11  # Plain CDR2, little-endian
    PL_CDR2_BE = 0x12  # Parameter List CDR2, big-endian
    PL_CDR2_LE = 0x13  # Parameter List CDR2, little-endian
    DELIMITED_CDR2_BE = 0x14  # Delimited CDR2, big-endian
    DELIMITED_CDR2_LE = 0x15  # Delimited CDR2, little-endian

    # RTPS specific IDs for XCDR2
    RTPS_CDR2_BE = 0x06  # Plain CDR2, big-endian
    RTPS_CDR2_LE = 0x07  # Plain CDR2, little-endian
    RTPS_DELIMITED_CDR2_BE = 0x08  # Delimited CDR2, big-endian
    RTPS_DELIMITED_CDR2_LE = 0x09  # Delimited CDR2, little-endian
    RTPS_PL_CDR2_BE = 0x0A  # Parameter List CDR2, big-endian
    RTPS_PL_CDR2_LE = 0x0B  # Parameter List CDR2, little-endian
