"""Regression tests for the sethomedata request body."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from vaillant_netatmo_api_ng.home import TemperatureControlMode, ThermMode
from vaillant_netatmo_api_ng.thermostat import NonOkResponseException, ThermostatClient


def client_with_post(return_value):
    # Skip the network client constructor and mock only its HTTP boundary.
    client = object.__new__(ThermostatClient)
    client._post = AsyncMock(return_value=return_value)
    return client


@pytest.mark.parametrize("therm_mode", [ThermMode.AWAY, ThermMode.SCHEDULE, ThermMode.HG])
def test_therm_mode_is_sent_inside_home(therm_mode):
    async def check():
        client = client_with_post({"status": "ok"})
        await client.async_set_home_data("home-1", TemperatureControlMode.HEATING, therm_mode)
        client._post.assert_awaited_once_with(
            "api/sethomedata",
            json={
                "home": {
                    "id": "home-1",
                    "temperature_control_mode": "heating",
                    "therm_mode": therm_mode.value,
                },
                "app_identifier": "app_thermostat_vaillant",
            },
        )
    asyncio.run(check())


def test_without_therm_mode_only_control_mode_is_sent():
    async def check():
        client = client_with_post({"status": "ok"})
        await client.async_set_home_data("home-1", TemperatureControlMode.COOLING)
        client._post.assert_awaited_once_with(
            "api/sethomedata",
            json={
                "home": {"id": "home-1", "temperature_control_mode": "cooling"},
                "app_identifier": "app_thermostat_vaillant",
            },
        )
    asyncio.run(check())


def test_non_ok_response_raises():
    async def check():
        client = client_with_post({"status": "error"})
        with pytest.raises(NonOkResponseException):
            await client.async_set_home_data("home-1", TemperatureControlMode.HEATING, ThermMode.AWAY)
    asyncio.run(check())
