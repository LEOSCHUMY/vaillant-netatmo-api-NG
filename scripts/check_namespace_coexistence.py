"""Check installed original and Next-Gen distributions without cloud requests."""

from importlib.metadata import distribution
import subprocess
import sys


def main() -> None:
    """Reject shared installed paths and exercise both import orders in fresh processes."""
    upstream = distribution("vaillant-netatmo-api")
    candidate = distribution("vaillant-netatmo-api-ng")
    if upstream.version != "0.13.1":
        raise ValueError("This coexistence check targets upstream 0.13.1")
    if not upstream.files or not candidate.files:
        raise ValueError("Installed distribution file records are required")
    original_files = {str(upstream.locate_file(path).resolve()) for path in upstream.files}
    ng_files = {str(candidate.locate_file(path).resolve()) for path in candidate.files}
    if original_files & ng_files:
        raise ValueError("The distributions must not own overlapping files")
    if not any(str(path).startswith("vaillant_netatmo_api_ng/") for path in candidate.files):
        raise ValueError("Install the built NG package, not an editable checkout")
    if any(str(path).startswith("vaillant_netatmo_api/") for path in candidate.files):
        raise ValueError("NG must not ship files in the original import namespace")

    check = """
from importlib import import_module
from pathlib import Path
import sys

first_name, second_name = sys.argv[1:]
first = import_module(first_name)
original_client = first.ThermostatClient
second = import_module(second_name)
assert import_module(first_name) is first
assert first.ThermostatClient is original_client
old = import_module("vaillant_netatmo_api")
ng = import_module("vaillant_netatmo_api_ng")
assert Path(old.__file__).parent.name == "vaillant_netatmo_api"
assert Path(ng.__file__).parent.name == "vaillant_netatmo_api_ng"
for name in ("ThermostatClient", "Token", "TokenStore", "ApiException"):
    old_type = getattr(old, name)
    ng_type = getattr(ng, name)
    assert old_type is not ng_type
    assert old_type.__module__.startswith("vaillant_netatmo_api.")
    assert ng_type.__module__.startswith("vaillant_netatmo_api_ng.")
assert hasattr(ng.ThermostatClient, "async_get_home_status_snapshot")
assert sys.modules["vaillant_netatmo_api"] is not sys.modules["vaillant_netatmo_api_ng"]
"""
    for order in (
        ("vaillant_netatmo_api", "vaillant_netatmo_api_ng"),
        ("vaillant_netatmo_api_ng", "vaillant_netatmo_api"),
    ):
        subprocess.run([sys.executable, "-c", check, *order], check=True)


if __name__ == "__main__":
    main()
