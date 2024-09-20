"""Manage named locations."""

import json
import warnings
from os.path import isdir

from file_access_manager.project import LOCATIONS_FILE, _check_for_project, _git_update


def list_locations():
    """
    View named locations.
    """
    locations = _get_locations()
    if len(locations):
        message = "Named locations:"
        for name, path in locations.items():
            message += f"\n  - {name}: {path}"
    else:
        message = "No named locations on record."
    print(message)
    return message


def add_location(name: str, path: str):
    """
    Add a named location.

    Args:
        name (str): Name to assign to the location.
        path (str): Path of the location.
    """
    locations = _get_locations()
    if name in locations and path == locations[name]:
        return
    if not isdir(path):
        warnings.warn(f"{path} does not exist", stacklevel=2)
    action = "edited" if name in locations else "created"
    message = f"{action} named location: {name} = {path}"
    locations[name] = path
    with open(LOCATIONS_FILE, "w", encoding="utf-8") as opened:
        json.dump(locations, opened, indent=2, sort_keys=True)
    print(message)
    _git_update(message)


def remove_location(name: str):
    """
    Remove a named location.

    Args:
        name (str): Name of the location to remove.
    """
    locations = _get_locations()
    if name in locations:
        print(f"removed named location `{name}`")
        locations.pop(name)
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as opened:
            json.dump(locations, opened, indent=2, sort_keys=True)
    else:
        print(f"`{name}` is not a named location")


def _get_locations():
    _check_for_project(LOCATIONS_FILE)
    with open(LOCATIONS_FILE, encoding="utf-8") as opened:
        locations = json.load(opened)
    return locations
