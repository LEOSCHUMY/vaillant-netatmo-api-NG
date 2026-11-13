# vaillant-netatmo-api-ng

[![Tests](https://github.com/LEOSCHUMY/vaillant-netatmo-api-NG/actions/workflows/tests.yml/badge.svg)](https://github.com/LEOSCHUMY/vaillant-netatmo-api-NG/actions/workflows/tests.yml)

## About this fork

**vaillant-netatmo-api-ng** is a community-maintained fork of [Mislav Mandarić's vaillant-netatmo-api](https://github.com/MislavMandaric/vaillant-netatmo-api), a Python library for accessing Vaillant vSMART/eRELAX thermostats through Netatmo-backed APIs.

This fork starts its **own version series at 0.1.0**. Version numbers do **not** track the original project's releases. NG adds read-only room temperatures and, since `0.1.1`, module boiler status from Vaillant's `homestatus` endpoint, while preserving the existing thermostat data and control APIs.

> [!IMPORTANT]
> **Independent, unofficial project — NOT affiliated with, authorized, sponsored, or endorsed by Vaillant or Netatmo.**
> This community fork is not an official Vaillant or Netatmo product, and neither company provides support for it. Their APIs may change or become unavailable without notice.

This fork is also independent of the original project's maintainer. See [LICENSE](LICENSE) for the MIT license and original copyright notice.

## Features

- Existing authenticated thermostat data access and heating controls from the upstream library.
- `ThermostatClient.async_get_homes_data()` for homes, rooms and `Room.module_ids`.
- `ThermostatClient.async_get_home_status(home_id)` for room status (including measured temperature, target temperature and reachability) keyed by room ID.
- Available since `0.1.1`: `ThermostatClient.async_get_home_status_snapshot(home_id)` returns a `HomeStatus` with `rooms` and `boiler_statuses` from one request. Boiler readings are keyed by module ID, including explicit `False`; missing, invalid, unreachable or conflicting duplicate readings are omitted. Consumers should match module IDs against their home topology and retain a legacy fallback. The room-only method remains compatible.
- Defensive validation for malformed responses and duplicate or conflicting room records.
- No fabricated measurement timestamp: the `homestatus` response does not provide a verified temperature acquisition time.

## Installation

Choose a published NG package version from [PyPI](https://pypi.org/project/vaillant-netatmo-api-ng/) or [GitHub Releases](https://github.com/LEOSCHUMY/vaillant-netatmo-api-NG/releases). To install the latest published version compatible with your Python interpreter:

```bash
pip install vaillant-netatmo-api-ng
```


The **distribution name** is `vaillant-netatmo-api-ng`, but the Python **import name** intentionally remains `vaillant_netatmo_api` for compatibility:

```python
from vaillant_netatmo_api.thermostat import ThermostatClient
```

Do not install `vaillant-netatmo-api` and `vaillant-netatmo-api-ng` in the same environment; they provide the same import package and may overwrite each other's files.

Version **0.2.0 requires Python 3.11+** and raises HTTP dependency minimums. Earlier **0.1.1** supports Python 3.8+. Select the release matching your interpreter; merging source changes does not publish them to PyPI.

For development, use Python 3.11+ and run `python -m pip install -r requirements-dev.txt` from the repository root. CI tests Python 3.11, 3.12 and 3.14, including HTTPX 0.27.0 / Tenacity 8.5.0 minimums on Python 3.12. See [dependency maintenance and security](SECURITY.md) for audit scope and update procedures.

## API usage

### Reading room temperatures

With an existing authenticated `ThermostatClient` instance:

```python
homes = await client.async_get_homes_data()
for home in homes:
    statuses = await client.async_get_home_status(home.id)
    for room in home.rooms:
        room_status = statuses.get(room.id)
        if room_status is not None:
            print(room_status.measured_temperature)
```

Use `homesdata` `rooms[].module_ids` to map room readings to the right thermostat module; do not assume the first room represents every thermostat. If `homestatus` cannot provide a valid room reading, applications should retain their previous measured-temperature fallback. This library does not change polling intervals for consumers.

### Reading room temperatures and boiler state together (0.1.1)

In `0.1.1` and later, one request provides both types of reading:

```python
homes = await client.async_get_homes_data()
for home in homes:
    snapshot = await client.async_get_home_status_snapshot(home.id)
    for room in home.rooms:
        room_status = snapshot.rooms.get(room.id)
        if room_status is not None:
            print(room_status.measured_temperature)
        for module_id in room.module_ids:
            boiler_status = snapshot.boiler_statuses.get(module_id)
            if boiler_status is not None:
                # Both True and False are valid readings for this snapshot.
                print(boiler_status)
```

Keep a legacy fallback for absent readings; do not use truthiness to decide
whether a boolean is available. Match module IDs within the requested home's
topology. Each snapshot is uncached, but the API's server-side update latency
is not guaranteed and no measurement timestamp is inferred.

### Existing authentication and thermostat operations

### Getting the token from the OAuth API

All Netatmo APIs are protected and require a bearer token to authenticate. To get this token, Netatmo offers an OAuth API.

Since Vaillant uses Resource Owner Password Credentials Grant, there is only one method in the `AuthClient` API:

* `async_token`: getting a bearer token and storing it in the token store

```python
from vaillant_netatmo_api import auth_client

CLIENT_ID = ""
CLIENT_SECRET = ""

def handle_token_update(token):
    token_string = token.serialize()
    write_to_storage(token_string)

async with auth_client(CLIENT_ID, CLIENT_SECRET, handle_token_update) as client:
    await client.async_token(
        username,
        password,
        user_prefix,
        app_version,
    )
```

### Accessing the Thermostat API

The existing `ThermostatClient` methods include:

* `async_get_thermostats_data`: getting all the devices associated with the user account
* `async_set_system_mode`: changing system mode for a device and module (ie. summer, winter or frostguard)
* `async_set_minor_mode`: changing minor mode for a device and module (ie. manual mode, away mode or hot water boost mode)
* `async_sync_schedule`: updating schedule data for a device and module
* `async_switch_schedule`: changing active schedule for a device and module

```python
from vaillant_netatmo_api import thermostat_client, SystemMode, Token

CLIENT_ID = ""
CLIENT_SECRET = ""

token_string = read_from_storage()
token = Token.deserialize(token_string)

def handle_token_update(token):
    token_string = token.serialize()
    write_to_storage(token_string)

async with thermostat_client(CLIENT_ID, CLIENT_SECRET, token, handle_token_update) as client:
    devices = await client.async_get_thermostats_data()

    d_id = devices[0].id
    m_id = devices[0].modules[0].id

    await client.async_set_system_mode(d_id, m_id, SystemMode.WINTER)
```

### Using clients as singletons

Even though library offers context manager for using `AuthClient` and `ThermostatClient`, this should only be done during development or in very infrequent usage scenarios.

Both of the clients use `httpx.AsyncClient` as the underlying HTTP communication library, which implements connection pooling and connection reuse. This means doing multiple concurent requests should be done by using the same instance of the `AuthClient` or `ThermostatClient`, which is not possible by using the context manager API since this API will return new instance of the client every time `auth_client` or `thermostat_client` method is called.

To achieve optimal usage, which will utilize connection pooling and connection reuse, both `AuthClient` and `ThermostatClient` should be used by instantiating the clients and providing `httpx.AsyncClient` instance in a constructor. This provided client should be used as singleton, or with some other context management mechanism, with the context wider than one block of code or one inbound request.

Here is an example for usage in Home Assistant.

```python
# When setting up integration with all the devices of one account, instantiate and store the client in a configuration memory store
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = get_async_client(hass)
    token_store = TokenStore(
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
        token,
        handle_token_update,
    )

    hass.data[DOMAIN][entry.entry_id] = ThermostatClient(client, token_store)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True

# When unloading the integration of this same account, read the client and close it manually
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```

Similar hooks which represent some kind of application context should be used when integrating this library into a different application (Flask, Django or similar).

## Acknowledgements

The original library was created by **Mislav Mandarić**, who retains the original copyright and attribution. This NG fork builds on that work and preserves its MIT license.


This library would not exist if it weren't for previous implementations by the following projects:

* https://github.com/philippelt/netatmo-api-python
* https://github.com/jabesq/netatmo-api-python
* https://github.com/samueldumont/netatmo-api-python
* https://github.com/jabesq/pyatmo
* https://github.com/pjmaenh/pyvaillant

They laid out the foundation by exploring and documenting the APIs.

## Disclaimers

**This is an unofficial, independent community project. It is not affiliated with, authorized, sponsored, or endorsed by Vaillant or Netatmo.** The project is provided without warranties or official support. Changes to either company's APIs, including restrictions on third-party access, may cause some or all features to stop working.
