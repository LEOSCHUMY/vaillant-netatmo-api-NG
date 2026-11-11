"""Regression coverage for real vSMART boiler status response shapes."""

import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from vaillant_netatmo_api.homestatus import (
    InvalidHomeStatusResponse,
    parse_home_status_snapshot,
)
from vaillant_netatmo_api.thermostat import ThermostatClient


def response(modules, home_id="home", wrapped=False):
    """Build a response with stable IDs and no actual account information."""
    home = {
        "id": home_id,
        "rooms": [{"id": "room", "therm_measured_temperature": 19.8}],
        "modules": modules,
    }
    body = {"data": {"home": home}} if wrapped else {"home": home}
    return {"status": "ok", "body": body}


@pytest.mark.parametrize("value", [False, True])
def test_concordant_duplicates_are_collapsed(value):
    """Repeated home modules must produce one reading, including False."""
    record = {"id": "thermostat", "boiler_status": value}
    payload = response([{"id": "bridge"}, record, {"id": "bridge"}, record.copy()])
    before = deepcopy(payload)
    result = parse_home_status_snapshot(payload, "home")
    assert result.boiler_statuses == {"thermostat": value}
    assert result.rooms["room"].measured_temperature == 19.8
    assert payload == before


@pytest.mark.parametrize("values", [[False, True, False], [True, False, True]])
def test_conflicting_duplicate_is_never_restored_by_later_record(values):
    """A conflict must stay rejected regardless of record ordering."""
    payload = response([{"id": "thermostat", "boiler_status": v} for v in values])
    result = parse_home_status_snapshot(payload, "home")
    assert result.boiler_statuses == {}
    assert result.rooms["room"].measured_temperature == 19.8


@pytest.mark.parametrize("value", [None, 0, 1, "true", "false", [], {}])
def test_invalid_boolean_does_not_become_idle(value):
    """Only actual booleans are allowed; unknown states remain absent."""
    result = parse_home_status_snapshot(response([
        {"id": "thermostat", "boiler_status": value},
        {"id": "other", "boiler_status": True},
    ]), "home")
    assert result.boiler_statuses == {"other": True}


@pytest.mark.parametrize("bad_record", [
    {"id": "thermostat"},
    {"id": "thermostat", "boiler_status": None},
    {"id": "thermostat", "boiler_status": True, "reachable": False},
])
@pytest.mark.parametrize("reverse", [False, True])
def test_invalid_duplicate_rejects_the_module_in_either_order(bad_record, reverse):
    """An otherwise valid duplicate cannot hide missing or unreachable data."""
    records = [{"id": "thermostat", "boiler_status": True}, bad_record]
    if reverse:
        records.reverse()
    assert parse_home_status_snapshot(response(records), "home").boiler_statuses == {}


@pytest.mark.parametrize("reachable", [False, None, 1, "true"])
def test_unreachable_or_invalid_reachability_is_omitted(reachable):
    """Do not report an unreachable module as an authoritative reading."""
    assert parse_home_status_snapshot(response([
        {"id": "thermostat", "boiler_status": True, "reachable": reachable},
    ]), "home").boiler_statuses == {}


@pytest.mark.parametrize("modules", [None, {}, "invalid", []])
def test_bad_module_collection_preserves_temperatures(modules):
    """Optional module state failures must not discard valid room readings."""
    result = parse_home_status_snapshot(response(modules), "home")
    assert result.boiler_statuses == {}
    assert result.rooms["room"].measured_temperature == 19.8


def test_wrapped_home_and_separate_module_ids():
    """Handle the alternate wrapper and preserve independent module readings."""
    result = parse_home_status_snapshot(response([
        {"id": "a", "boiler_status": True},
        {"id": "b", "boiler_status": False},
        {"id": "", "boiler_status": True},
        None,
    ], wrapped=True), "home")
    assert result.boiler_statuses == {"a": True, "b": False}


def test_wrong_home_is_rejected_without_disclosing_identifiers():
    """Reject accidental cross-home data before consumers can use it."""
    with pytest.raises(InvalidHomeStatusResponse) as error:
        parse_home_status_snapshot(response([], "private-home-id"), "expected-home-id")
    assert "private-home-id" not in str(error.value)
    assert "expected-home-id" not in str(error.value)


def test_snapshot_client_uses_one_request_and_has_no_stale_cache():
    """The next response replaces both readings, and errors cannot return old data."""
    async def check():
        client = object.__new__(ThermostatClient)
        client._post = AsyncMock(side_effect=[
            response([{"id": "thermostat", "boiler_status": True}]),
            response([]),
            ValueError("failed request"),
        ])
        first = await client.async_get_home_status_snapshot("home")
        assert first.boiler_statuses == {"thermostat": True}
        client._post.assert_awaited_once_with(
            "syncapi/v1/homestatus",
            json={"home_id": "home", "app_type": "app_thermostat_vaillant",
                  "app_version": "2.4.5.0"},
        )
        second = await client.async_get_home_status_snapshot("home")
        assert second.boiler_statuses == {}
        assert first.boiler_statuses == {"thermostat": True}
        with pytest.raises(ValueError, match="failed request"):
            await client.async_get_home_status_snapshot("home")
        assert client._post.await_count == 3
    asyncio.run(check())


def test_empty_home_id_is_rejected_before_network():
    """Validate the new API's arguments before making a request."""
    async def check():
        client = object.__new__(ThermostatClient)
        client._post = AsyncMock()
        with pytest.raises(ValueError):
            await client.async_get_home_status_snapshot("")
        client._post.assert_not_awaited()
    asyncio.run(check())
