"""Regression tests for Vaillant home status room mapping."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from vaillant_netatmo_api_ng.homestatus import (
    InvalidHomeStatusResponse,
    RoomStatus,
    parse_home_status,
)
from vaillant_netatmo_api_ng.thermostat import ThermostatClient


def response(rooms):
    return {"status": "ok", "body": {"home": {"rooms": rooms}}}


def room(room_id="room-1", temp=19.5, setpoint=20.0, reachable=True):
    return {
        "id": room_id,
        "therm_measured_temperature": temp,
        "therm_setpoint_temperature": setpoint,
        "reachable": reachable,
    }


def test_one_room_with_duplicate_api_records():
    result = parse_home_status(response([room(), room()]))
    assert len(result) == 1
    assert result["room-1"].measured_temperature == 19.5
    assert result["room-1"].setpoint_temperature == 20.0
    assert result["room-1"].reachable is True


def test_multiple_distinct_rooms_are_not_collapsed():
    result = parse_home_status(response([room(), room("room-2", 18.5)]))
    assert set(result) == {"room-1", "room-2"}
    assert result["room-2"].measured_temperature == 18.5


def test_conflicting_duplicates_rejected():
    with pytest.raises(InvalidHomeStatusResponse, match="Conflicting"):
        parse_home_status(response([room(), room(temp=19.6)]))


@pytest.mark.parametrize("bad_room", [
    {}, {"id": ""}, {"id": "room-1", "therm_measured_temperature": "19.5"},
    {"id": "room-1", "therm_measured_temperature": True},
    {"id": "room-1", "therm_measured_temperature": float("nan")},
])
def test_invalid_room_rejected(bad_room):
    with pytest.raises(InvalidHomeStatusResponse):
        parse_home_status(response([bad_room]))


def test_missing_temperature_is_not_fabricated():
    result = parse_home_status(response([{"id": "room-1"}]))
    assert result["room-1"].measured_temperature is None
    assert result["room-1"].setpoint_temperature is None


def test_missing_or_bad_response_rejected():
    for payload in ({}, {"status": "error"}, {"status": "ok", "body": {}}):
        with pytest.raises(InvalidHomeStatusResponse):
            parse_home_status(payload)


def test_client_uses_expected_endpoint_and_params():
    async def check():
        # Skip the network client constructor and mock only its HTTP boundary.
        client = object.__new__(ThermostatClient)
        client._post = AsyncMock(return_value=response([room(), room()]))
        result = await client.async_get_home_status("home-1")
        assert len(result) == 1
        client._post.assert_awaited_once_with(
            "syncapi/v1/homestatus",
            json={
                "home_id": "home-1",
                "app_type": "app_thermostat_vaillant",
                "app_version": "2.4.5.0",
            },
        )
    asyncio.run(check())


def test_client_rejects_empty_home_id_before_network():
    async def check():
        client = object.__new__(ThermostatClient)
        client._post = AsyncMock()
        with pytest.raises(ValueError):
            await client.async_get_home_status("")
        client._post.assert_not_awaited()
    asyncio.run(check())


def test_setpoint_mode_and_end_time_are_exposed():
    """Recorded from a live homestatus response right after a manual setstate."""
    raw = room(setpoint=16.5)
    raw["therm_setpoint_mode"] = "manual"
    raw["therm_setpoint_end_time"] = 1795350676
    result = parse_home_status(response([raw, dict(raw)]))
    assert result["room-1"].setpoint_mode == "manual"
    assert result["room-1"].setpoint_end_time == 1795350676


def test_schedule_mode_has_no_end_time():
    raw = room(setpoint=16.0)
    raw["therm_setpoint_mode"] = "home"
    result = parse_home_status(response([raw]))
    assert result["room-1"].setpoint_mode == "home"
    assert result["room-1"].setpoint_end_time is None


@pytest.mark.parametrize("mode", [None, "", 3, True, ["manual"]])
@pytest.mark.parametrize("end", [None, "1795350676", True, 1.5])
def test_malformed_mode_or_end_time_is_none_and_keeps_readings(mode, end):
    raw = room()
    raw["therm_setpoint_mode"] = mode
    raw["therm_setpoint_end_time"] = end
    result = parse_home_status(response([raw]))
    assert result["room-1"].setpoint_mode is None
    assert result["room-1"].setpoint_end_time is None
    assert result["room-1"].measured_temperature == 19.5


def test_conflicting_duplicate_modes_rejected():
    first, second = room(), room()
    first["therm_setpoint_mode"] = "manual"
    second["therm_setpoint_mode"] = "home"
    with pytest.raises(InvalidHomeStatusResponse, match="Conflicting"):
        parse_home_status(response([first, second]))


def test_room_status_positional_construction_is_unchanged():
    status = RoomStatus("room-1", 19.5, 20.0, True)
    assert status.setpoint_mode is None
    assert status.setpoint_end_time is None
