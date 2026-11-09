"""Regression tests for parsed thermostat measurements."""

from src.vaillant_netatmo_api.thermostat import Device


def test_module_preserves_measured_timestamp():
    timestamp = 1794255738
    device = Device(
        _id="device",
        modules=[
            {
                "_id": "module",
                "measured": {
                    "temperature": 20.2,
                    "setpoint_temp": 19,
                    "est_setpoint_temp": 19,
                    "time": timestamp,
                },
            }
        ],
    )

    assert device.modules[0].measured.time == timestamp
