"""Models and validation for Vaillant's home status endpoint.

The sync API can return duplicate room entries. Records are deduplicated by
stable room ID; disagreement between duplicates is treated as an error rather
than silently selecting an arbitrary temperature.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RoomStatus:
    """Current reading for one logical Vaillant room.

    The endpoint does not supply a measurement timestamp for this temperature.
    """

    room_id: str
    measured_temperature: float | None
    setpoint_temperature: float | None
    reachable: bool | None


class InvalidHomeStatusResponse(ValueError):
    """Raised when home status cannot be mapped unambiguously."""


@dataclass(frozen=True)
class HomeStatus:
    """Room and module readings from one homestatus response, without caching."""

    rooms: dict[str, RoomStatus]
    boiler_statuses: dict[str, bool]


def parse_home_status_snapshot(response: dict, expected_home_id: str) -> HomeStatus:
    """Parse a home snapshot, retaining valid module boiler booleans by stable ID.

    Bad module data is omitted independently of room temperatures. Identical
    boiler readings for a repeated ID are collapsed. A conflicting, missing,
    invalid or unreachable duplicate rejects that ID for this response.
    """
    rooms = parse_home_status(response)
    body = response["body"]
    home = body.get("home")
    if not isinstance(home, dict):
        home = body["data"]["home"]
    if (
        not isinstance(expected_home_id, str)
        or not expected_home_id
        or home.get("id") != expected_home_id
    ):
        raise InvalidHomeStatusResponse("Home status does not match requested home")

    modules = home.get("modules")
    if not isinstance(modules, list):
        return HomeStatus(rooms, {})
    readings: dict[str, bool] = {}
    rejected: set[str] = set()
    for record in modules:
        if not isinstance(record, dict):
            continue
        module_id = record.get("id")
        if not isinstance(module_id, str) or not module_id or module_id in rejected:
            continue
        value = record.get("boiler_status")
        if (
            type(value) is not bool
            or record.get("reachable", True) is not True
            or (module_id in readings and readings[module_id] != value)
        ):
            readings.pop(module_id, None)
            rejected.add(module_id)
            continue
        readings[module_id] = value
    return HomeStatus(rooms, readings)


def parse_home_status(response: dict) -> dict[str, RoomStatus]:
    """Return one status per distinct room ID from a successful API response.

    Does not log or include raw response data or identifiers in exceptions.
    """
    if not isinstance(response, dict) or response.get("status") != "ok":
        raise InvalidHomeStatusResponse("Home status request was not successful")

    body = response.get("body")
    if not isinstance(body, dict):
        raise InvalidHomeStatusResponse("Missing home status body")
    home = body.get("home")
    if not isinstance(home, dict):
        # Some API response wrappers expose the home under body.data.home.
        data = body.get("data")
        if isinstance(data, dict):
            home = data.get("home")
    if not isinstance(home, dict):
        raise InvalidHomeStatusResponse("Missing home status home object")

    rooms = home.get("rooms")
    if not isinstance(rooms, list):
        raise InvalidHomeStatusResponse("Missing home status rooms list")

    result: dict[str, RoomStatus] = {}
    for raw_room in rooms:
        if not isinstance(raw_room, dict):
            raise InvalidHomeStatusResponse("Invalid room record")
        room_id = raw_room.get("id")
        if not isinstance(room_id, str) or not room_id:
            raise InvalidHomeStatusResponse("Room record has no valid ID")

        temp = _temperature(raw_room.get("therm_measured_temperature"))
        setpoint = _temperature(raw_room.get("therm_setpoint_temperature"))
        reachable = raw_room.get("reachable")
        if reachable is not None and not isinstance(reachable, bool):
            raise InvalidHomeStatusResponse("Invalid room reachability")

        status = RoomStatus(room_id, temp, setpoint, reachable)
        previous = result.get(room_id)
        if previous is not None and previous != status:
            raise InvalidHomeStatusResponse("Conflicting duplicate room records")
        result[room_id] = status

    return result


def _temperature(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidHomeStatusResponse("Invalid temperature type")
    result = float(value)
    if not isfinite(result):
        raise InvalidHomeStatusResponse("Non-finite temperature")
    return result
