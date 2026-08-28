"""Packet parsing errors."""

class PacketFormatError(ValueError):
    """Input bytes do not conform to their declared packet format."""
