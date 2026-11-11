"""Ensure homesdata retains the room-to-thermostat mapping."""

from vaillant_netatmo_api.home import Home, Room


def test_room_module_ids_are_preserved():
    home = Home(id="home-1", rooms=[{"id": "room-1", "module_ids": ["therm-1"]}])
    assert home.rooms[0].module_ids == ["therm-1"]


def test_room_without_module_ids_defaults_to_empty_list():
    assert Room(id="room-1").module_ids == []
