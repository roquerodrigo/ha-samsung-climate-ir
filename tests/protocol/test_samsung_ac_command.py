from __future__ import annotations

import pytest

from custom_components.samsung_climate_ir.protocol import (
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    SamsungAcCommand,
    SamsungAcFanSpecial,
    SamsungAcFanSpeed,
    SamsungAcMode,
    SamsungAcSwing,
)
from custom_components.samsung_climate_ir.protocol.samsung_ac_command import (
    _section_checksum,
)
from tests.protocol_fixtures import CAPTURED_COOL, CAPTURED_HEAT, CAPTURED_OFF

COOL_COMMAND = {
    "power": True,
    "mode": SamsungAcMode.COOL,
    "temperature": 22,
    "fan": SamsungAcFanSpeed.AUTO,
    "swing": SamsungAcSwing.OFF,
    "fan_special": SamsungAcFanSpecial.WIND_FREE,
    "display": False,
}
HEAT_COMMAND = {
    "power": True,
    "mode": SamsungAcMode.HEAT,
    "temperature": 24,
    "fan": SamsungAcFanSpeed.AUTO,
    "swing": SamsungAcSwing.BOTH,
    "fan_special": SamsungAcFanSpecial.OFF,
    "display": False,
}
OFF_COMMAND = {**COOL_COMMAND, "power": False}


def fields(command):
    return (
        command.power,
        command.mode,
        command.temperature,
        command.fan,
        command.swing,
        command.fan_special,
        command.display,
    )


def test_cool_frame_matches_captured_remote_code():
    frame = SamsungAcCommand(**COOL_COMMAND).build_frame()
    assert frame.hex().upper() == "02920F000000F001C2FE6B6011F0"


def test_heat_frame_matches_captured_remote_code():
    frame = SamsungAcCommand(**HEAT_COMMAND).build_frame()
    assert frame.hex().upper() == "02920F000000F00112CF618041F0"


def test_off_frame_matches_captured_remote_code():
    frame = SamsungAcCommand(**OFF_COMMAND).build_frame()
    assert frame.hex().upper() == "02B20F0000003001E2FE6B6011C0"


@pytest.mark.parametrize(
    ("captured", "expected"),
    [
        (CAPTURED_COOL, COOL_COMMAND),
        (CAPTURED_HEAT, HEAT_COMMAND),
        (CAPTURED_OFF, OFF_COMMAND),
    ],
    ids=["cool", "heat", "off"],
)
def test_decode_captured_timings(captured, expected):
    command = SamsungAcCommand.from_raw_timings(captured)
    assert command is not None
    assert fields(command) == tuple(expected.values())


def test_decode_captured_timings_without_leading_header():
    command = SamsungAcCommand.from_raw_timings(CAPTURED_COOL[2:])
    assert command is not None
    assert fields(command) == tuple(COOL_COMMAND.values())


@pytest.mark.parametrize("power", [True, False])
@pytest.mark.parametrize("mode", list(SamsungAcMode))
@pytest.mark.parametrize("temperature", [MIN_TEMPERATURE, 22, MAX_TEMPERATURE])
def test_roundtrip_over_modes(power, mode, temperature):
    command = SamsungAcCommand(power=power, mode=mode, temperature=temperature)
    decoded = SamsungAcCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert fields(decoded) == fields(command)


@pytest.mark.parametrize(
    "fan", [f for f in SamsungAcFanSpeed if f is not SamsungAcFanSpeed.AUTO_ALTERNATE]
)
@pytest.mark.parametrize("swing", list(SamsungAcSwing))
@pytest.mark.parametrize("fan_special", list(SamsungAcFanSpecial))
def test_roundtrip_over_fan_swing_and_special(fan, swing, fan_special):
    command = SamsungAcCommand(
        power=True,
        mode=SamsungAcMode.COOL,
        temperature=20,
        fan=fan,
        swing=swing,
        fan_special=fan_special,
    )
    decoded = SamsungAcCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert fields(decoded) == fields(command)


@pytest.mark.parametrize("display", [True, False])
def test_roundtrip_display(display):
    command = SamsungAcCommand(
        power=True,
        mode=SamsungAcMode.COOL,
        temperature=22,
        display=display,
    )
    decoded = SamsungAcCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert decoded.display is display


def test_display_sets_only_bit_4_of_byte_10():
    base = SamsungAcCommand(power=True, mode=SamsungAcMode.COOL, temperature=22)
    lit = SamsungAcCommand(
        power=True, mode=SamsungAcMode.COOL, temperature=22, display=True
    )
    base_frame, lit_frame = base.build_frame(), lit.build_frame()
    assert lit_frame[10] == base_frame[10] | 0b0001_0000
    differing = [
        index
        for index in range(14)
        if base_frame[index] != lit_frame[index] and index not in (1, 2, 8, 9)
    ]
    assert differing == [10]


@pytest.mark.parametrize("temperature", [MIN_TEMPERATURE - 1, MAX_TEMPERATURE + 1])
def test_out_of_range_temperature_raises(temperature):
    with pytest.raises(ValueError, match="out of range"):
        SamsungAcCommand(power=True, mode=SamsungAcMode.COOL, temperature=temperature)


def test_decode_rejects_short_signal():
    assert SamsungAcCommand.from_raw_timings(CAPTURED_COOL[:100]) is None


def test_decode_rejects_empty_signal():
    assert SamsungAcCommand.from_raw_timings([]) is None


def test_decode_rejects_corrupted_bit():
    corrupted = list(CAPTURED_COOL)
    corrupted[5] = 1000
    assert SamsungAcCommand.from_raw_timings(corrupted) is None


def test_decode_rejects_bad_checksum():
    corrupted = list(CAPTURED_COOL)
    corrupted[5] = 1496 if corrupted[5] < 1000 else 501
    assert SamsungAcCommand.from_raw_timings(corrupted) is None


def test_decode_rejects_wrong_section_header():
    corrupted = list(CAPTURED_COOL)
    corrupted[3] = 4000
    assert SamsungAcCommand.from_raw_timings(corrupted) is None


def _timings_for_frame(frame: bytes) -> list[int]:
    timings = [550, -17550]
    for start in (0, 7):
        if start:
            timings.append(-3000)
        timings += [3000, -9000]
        for byte in frame[start : start + 7]:
            for bit_index in range(8):
                timings.append(500)
                timings.append(-1500 if byte >> bit_index & 1 else -500)
        timings.append(500)
    return timings


def _with_fixed_checksums(frame: bytearray) -> bytes:
    for start in (0, 7):
        frame[start + 1] &= 0x0F
        frame[start + 2] &= 0xF0
        checksum = _section_checksum(bytes(frame[start : start + 7]))
        frame[start + 1] |= (checksum & 0x0F) << 4
        frame[start + 2] |= checksum >> 4
    return bytes(frame)


def test_decode_rejects_invalid_fan_value():
    frame = bytearray(
        SamsungAcCommand(
            power=True, mode=SamsungAcMode.COOL, temperature=22
        ).build_frame()
    )
    frame[12] = (frame[12] & ~0x0E) | (1 << 1)
    timings = _timings_for_frame(_with_fixed_checksums(frame))
    assert SamsungAcCommand.from_raw_timings(timings) is None


def test_decode_rejects_invalid_mode_value():
    frame = bytearray(
        SamsungAcCommand(
            power=True, mode=SamsungAcMode.COOL, temperature=22
        ).build_frame()
    )
    frame[12] = (frame[12] & ~0x70) | (7 << 4)
    timings = _timings_for_frame(_with_fixed_checksums(frame))
    assert SamsungAcCommand.from_raw_timings(timings) is None


def test_decode_rejects_power_copies_disagreeing():
    frame = bytearray(
        SamsungAcCommand(
            power=True, mode=SamsungAcMode.COOL, temperature=22
        ).build_frame()
    )
    frame[13] &= 0b11001111
    timings = _timings_for_frame(_with_fixed_checksums(frame))
    assert SamsungAcCommand.from_raw_timings(timings) is None


def test_decode_rejects_temperature_above_range():
    frame = bytearray(
        SamsungAcCommand(
            power=True, mode=SamsungAcMode.COOL, temperature=30
        ).build_frame()
    )
    frame[11] |= 0xF0
    timings = _timings_for_frame(_with_fixed_checksums(frame))
    assert SamsungAcCommand.from_raw_timings(timings) is None


def test_timings_start_with_header_and_sections():
    timings = SamsungAcCommand(
        power=True, mode=SamsungAcMode.COOL, temperature=22
    ).get_raw_timings()
    assert timings[:4] == [550, -17550, 3000, -9000]
    assert len(timings) == 233
    assert timings[-1] == 500
