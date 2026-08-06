"""
Samsung AC IR command.

Frame layout (14 bytes, two 7-byte sections, bits sent LSB-first per byte):
  byte 6  bits 7-6: power, first copy (0b11 on, 0b00 off)
  byte 9  bits 6-4: swing
  byte 10 bits 3-1: special fan feature (WindFree, powerful, econo)
  byte 10 bit 4: display (panel light) on
  byte 11 bits 7-4: temperature (value + 16 = deg C)
  byte 12 bits 6-4: mode, bits 3-1: fan speed
  byte 13 bits 5-4: power, second copy

Each section stores a checksum: the inverted count of set bits across the
section's data nibbles, split into byte 1's high nibble (checksum low nibble)
and byte 2's low nibble (checksum high nibble).

Signal shape: a 550/17550us header pair, then per section a 3000/9000us
section header, 56 bits (500us mark; 500us space = 0, 1500us space = 1) and a
closing 500us mark, with a 3000us gap between sections.
"""

from __future__ import annotations

from typing import Self, override

from infrared_protocols.commands import Command

from .samsung_ac_fan_special import SamsungAcFanSpecial
from .samsung_ac_fan_speed import SamsungAcFanSpeed
from .samsung_ac_mode import SamsungAcMode
from .samsung_ac_swing import SamsungAcSwing

MIN_TEMPERATURE = 16
MAX_TEMPERATURE = 30

_HEADER_MARK = 550
_HEADER_SPACE = 17550
_SECTION_MARK = 3000
_SECTION_SPACE = 9000
_SECTION_GAP = 3000
_BIT_MARK = 500
_BIT_ONE_SPACE = 1500
_BIT_ZERO_SPACE = 500

_SECTION_COUNT = 2
_SECTION_LENGTH = 7
_SECTION_BITS = _SECTION_LENGTH * 8

_POWER_ON_BITS = 0b11
_POWER_OFF_BITS = 0b00

# Captured from a physical Samsung remote, with every field and checksum bit
# cleared; encoding patches the fields back in.
_TEMPLATE = bytes(
    (0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0x30),
) + bytes((0x01, 0x02, 0x80, 0x61, 0x00, 0x01, 0xC0))

# IR receivers distort marks (automatic gain control) more than spaces, so
# marks get a wider relative tolerance when decoding.
_MARK_TOLERANCE = 0.7
_SPACE_TOLERANCE = 0.3

# A receiver skews a bit's mark and space by roughly a fixed number of
# microseconds, so bits get an absolute tolerance that still keeps the zero
# and one spaces apart (150-850 vs 1150-1850).
_BIT_TOLERANCE = 350

# Any space this long can only be the leading header's 17550us space.
_MINIMUM_HEADER_SPACE = 12000


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    """Check if a timing is within the given relative tolerance of expected."""
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _decode_bit(mark: int, space: int) -> int | None:
    """Decode one bit from its mark and space, or None if it matches neither."""
    if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
        return None
    if abs(space - _BIT_ZERO_SPACE) <= _BIT_TOLERANCE:
        return 0
    if abs(space - _BIT_ONE_SPACE) <= _BIT_TOLERANCE:
        return 1
    return None


def _section_checksum(section: bytes) -> int:
    """Return the checksum byte for a 7-byte section."""
    data_bits = (
        section[0].bit_count()
        + (section[1] & 0x0F).bit_count()
        + (section[2] >> 4).bit_count()
        + sum(byte.bit_count() for byte in section[3:_SECTION_LENGTH])
    )
    return ~data_bits & 0xFF


def _stored_checksum(section: bytes) -> int:
    """Return the checksum byte stored in a 7-byte section."""
    return ((section[2] & 0x0F) << 4) | (section[1] >> 4)


class SamsungAcCommand(Command):
    """Samsung AC IR command."""

    power: bool
    mode: SamsungAcMode
    temperature: int
    fan: SamsungAcFanSpeed
    swing: SamsungAcSwing
    fan_special: SamsungAcFanSpecial
    display: bool

    # A protocol value object carries one keyword-only argument per frame
    # field; splitting the constructor would hide the frame's shape.
    def __init__(  # noqa: PLR0913
        self,
        *,
        power: bool,
        mode: SamsungAcMode,
        temperature: int,
        fan: SamsungAcFanSpeed = SamsungAcFanSpeed.AUTO,
        swing: SamsungAcSwing = SamsungAcSwing.OFF,
        fan_special: SamsungAcFanSpecial = SamsungAcFanSpecial.OFF,
        display: bool = False,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Samsung AC IR command."""
        super().__init__(modulation=modulation)

        if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
            message = (
                f"temperature {temperature} out of range "
                f"{MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
            )
            raise ValueError(message)

        self.power = power
        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.swing = swing
        self.fan_special = fan_special
        self.display = display

    def build_frame(self) -> bytes:
        """Build the 14-byte protocol frame for this command."""
        frame = bytearray(_TEMPLATE)
        power_bits = _POWER_ON_BITS if self.power else _POWER_OFF_BITS
        frame[6] |= power_bits << 6
        frame[13] |= power_bits << 4
        frame[9] |= self.swing << 4
        frame[10] |= (self.fan_special << 1) | (self.display << 4)
        frame[11] |= (self.temperature - MIN_TEMPERATURE) << 4
        frame[12] |= (self.mode << 4) | (self.fan << 1)
        for start in (0, _SECTION_LENGTH):
            checksum = _section_checksum(bytes(frame[start : start + _SECTION_LENGTH]))
            frame[start + 1] |= (checksum & 0x0F) << 4
            frame[start + 2] |= checksum >> 4
        return bytes(frame)

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Samsung AC command."""
        frame = self.build_frame()
        timings: list[int] = [_HEADER_MARK, -_HEADER_SPACE]
        for start in (0, _SECTION_LENGTH):
            if start:
                timings.append(-_SECTION_GAP)
            timings += [_SECTION_MARK, -_SECTION_SPACE]
            for byte in frame[start : start + _SECTION_LENGTH]:
                for bit_index in range(8):
                    timings.append(_BIT_MARK)
                    timings.append(
                        -_BIT_ONE_SPACE if byte >> bit_index & 1 else -_BIT_ZERO_SPACE,
                    )
            timings.append(_BIT_MARK)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """
        Decode raw IR timings into a SamsungAcCommand.

        Returns a SamsungAcCommand if the timings match, or None otherwise.
        The leading header pair is optional, so captures that start directly at
        the first section still decode.
        """
        absolute = [abs(timing) for timing in timings]
        index = (
            2
            if len(absolute) > 2 and absolute[1] >= _MINIMUM_HEADER_SPACE  # noqa: PLR2004
            else 0
        )

        frame = bytearray()
        for section_number in range(_SECTION_COUNT):
            if section_number:
                index += 1
            if index + 2 * (_SECTION_BITS + 1) + 1 > len(absolute):
                return None
            if not _is_close(absolute[index], _SECTION_MARK, _MARK_TOLERANCE):
                return None
            if not _is_close(absolute[index + 1], _SECTION_SPACE, _SPACE_TOLERANCE):
                return None
            index += 2

            section_value = 0
            for bit_number in range(_SECTION_BITS):
                bit = _decode_bit(absolute[index], absolute[index + 1])
                if bit is None:
                    return None
                section_value |= bit << bit_number
                index += 2
            if abs(absolute[index] - _BIT_MARK) > _BIT_TOLERANCE:
                return None
            index += 1
            frame += section_value.to_bytes(_SECTION_LENGTH, "little")

        return cls._from_frame(bytes(frame))

    @classmethod
    def _from_frame(cls, frame: bytes) -> Self | None:
        """Decode a 14-byte frame into a command, or None if invalid."""
        for start in (0, _SECTION_LENGTH):
            section = frame[start : start + _SECTION_LENGTH]
            if _section_checksum(section) != _stored_checksum(section):
                return None

        power_first = frame[6] >> 6
        power_second = (frame[13] >> 4) & 0b11
        if power_first != power_second or power_first not in (
            _POWER_ON_BITS,
            _POWER_OFF_BITS,
        ):
            return None

        try:
            mode = SamsungAcMode((frame[12] >> 4) & 0b111)
            fan = SamsungAcFanSpeed((frame[12] >> 1) & 0b111)
            swing = SamsungAcSwing((frame[9] >> 4) & 0b111)
            fan_special = SamsungAcFanSpecial((frame[10] >> 1) & 0b111)
        except ValueError:
            return None

        temperature = (frame[11] >> 4) + MIN_TEMPERATURE
        if temperature > MAX_TEMPERATURE:
            return None

        return cls(
            power=power_first == _POWER_ON_BITS,
            mode=mode,
            temperature=temperature,
            fan=fan,
            swing=swing,
            fan_special=fan_special,
            display=bool(frame[10] >> 4 & 1),
        )
