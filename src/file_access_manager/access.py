"""Manage user access."""

import re
import subprocess
import warnings
from os.path import isdir, isfile
from shutil import which
from time import ctime
from typing import Union

import pandas

from file_access_manager.locations import _get_locations
from file_access_manager.project import ACCESS_FILE, ACCESS_STRUCTURE, _check_for_project, _git_update

ID_PATH = which("id")
SETFACL_PATH = which("setfacl")
GETFACL_PATH = which("getfacl")


def set_permission(location: str, user: str, group: "Union[str, None]" = None, permissions="rx"):
    """
    Grant a user permission, and add them to a group.

    Args:
        location (str): Name of a location, or path, to grant `user` `permissions` to.
        user (str): Name of the user.
        group (str): Group to assign the user to. Defaults to the user themselves. Here,
            groups grant the user the group's access, and any permissions assigned to the
            user in the group would be removed with the group not on removal from the group.
        permissions (str): Permission string (e.g., "rwx").
    """
    access = _get_accesses()
    if isdir(location):
        path = location
    else:
        path = _get_locations().get(location, "")
        if not isdir(path):
            msg = f"location ({location}) does not exist"
            raise RuntimeError(msg)
    if not group:
        group = user
    message = ""
    if ID_PATH and subprocess.run([ID_PATH, user], check=False, capture_output=True).stderr != b"":
        pending = _get_pendings()
        updated = _append_row(pending, user, group, path, permissions)
        if len(pending) != len(updated):
            updated.to_csv("pending_" + ACCESS_FILE, index=False)
            message = f"added {user} to pending access for {location} in group {group}"
            _log(message)
    else:
        res = _set_permissions(user, path, permissions)
        if res.stderr == b"":
            updated = _append_row(access, user, group, path, permissions)
            if len(access) != len(updated):
                updated.to_csv(ACCESS_FILE, index=False)
                message = f"set permissions to {location} for {user} in group {group}"
                _log(message)
        else:
            print(res.stderr)
            _log(f"failed to set permissions for {user}")
    if message:
        _git_update(message)


def _get_accesses():
    _check_for_project(ACCESS_FILE)
    return pandas.read_csv(ACCESS_FILE, dtype=ACCESS_STRUCTURE)


def _get_pendings():
    _check_for_project(ACCESS_FILE)
    return pandas.read_csv("pending_" + ACCESS_FILE, dtype=ACCESS_STRUCTURE)


def _set_permissions(user: str, path: str, perms: str):
    if SETFACL_PATH:
        res = subprocess.run([SETFACL_PATH, "-R", "-m", f"d:u:{user}:{perms}", path], check=False, capture_output=True)
        if res.stderr != b"":
            warnings.warn(
                f"failed to set permissions for user {user} on path {path}: {res.stderr.decode('utf-8')}",
                stacklevel=2,
            )
        else:
            set_perms = _get_current_access(path)
            if user not in set_perms or not _perms_match(set_perms[user], perms):
                msg = "permissions were not successfully set: " + (
                    "none were applied"
                    if user not in set_perms
                    else f"set permissions do not match ({perms} versus {set_perms[user]})"
                )
                raise RuntimeError(msg)
        return res
    else:
        msg = "`setfacl` command not found"


def _append_row(current: pandas.DataFrame, user: str, group: str, location: str, permissions: str):
    return (
        pandas.concat(
            [
                pandas.DataFrame(
                    {
                        "user": [user],
                        "group": [group],
                        "location": [location],
                        "permissions": [permissions],
                        "date": [ctime()],
                    }
                ),
                current,
            ],
            ignore_index=True,
        )
        .drop_duplicates(["user", "group", "location"])
        .sort_values(["user", "group", "location"])
    )


def _log(message: str):
    with open("log.txt", "a", encoding="utf-8") as opened:
        opened.write(f"{ctime()}: {message}\n")


def check_pending():
    """Check any users pending access, and apply permissions if they now exist."""
    pending_file = "pending_" + ACCESS_FILE
    if isfile(pending_file):
        pending = _get_pendings()
        updated = False
        for user, access in pending.groupby("user"):
            if _user_exists(user):
                for location, permissions in zip(access["location"], access["permissions"]):
                    _set_permissions(user, location, permissions)
                pending = pending[pending["user"] != user]
                _log(f"removed {user} from pending after setting permissions")
                updated = True
        if updated:
            pending.to_csv(ACCESS_FILE, index=False)
            _git_update("processed pending permissions")
    else:
        print("no pending users")


def _user_exists(user: str):
    return ID_PATH and subprocess.run([ID_PATH, user], check=False, capture_output=True).stderr == b""


def _revoke(user: str, path: str):
    if SETFACL_PATH:
        res = subprocess.run([SETFACL_PATH, "-R", "-x", f"d:u:{user}", path], check=False, capture_output=True)
        failure_message = f"failed to revoke access to {path} from {user}: "
        if res.stderr != b"":
            msg = failure_message + res.stderr.decode("utf-8")
            raise RuntimeError(msg)
        else:
            set_perms = _get_current_access(path)
            if user in set_perms:
                msg = failure_message + "still appears in access list"
                raise RuntimeError(msg)
    else:
        msg = "`setfacl` command not found"
        raise RuntimeError(msg)


def revoke_permissions(user: str, location: "Union[str, None]" = None):
    access = _get_accesses()
    removed = su = access["user"] == user
    if any(su):
        if location:
            locations = _get_locations()
            path = locations.get(location, location)
            _revoke(user, path)
            removed = removed & (access["location"] == path)
            _log(f"removed permissions from {user}: can no longer access {path}")
        else:
            for path in access["location"][su]:
                _revoke(user, path)
            _log(f"removed all permissions from {user}")
        group_access = access[~su & (access["group"] == user)]
        if len(group_access):
            removed = removed | (access["group"] == user)
            if location:
                group_access = group_access[group_access["location"] == path]
                if len(group_access):
                    for sub_user in group_access["user"]:
                        _revoke(sub_user, path)
                        _log(f"removed permissions from {sub_user}: can no longer access {path} under {user}")
                    removed = removed & (access["location"] == path)
            else:
                for sub_user, path in zip(group_access["user"], group_access["location"]):
                    _revoke(sub_user, path)
                    _log(f"removed permissions from {sub_user}: can no longer access {path} under {user}")
        access[~removed].to_csv(ACCESS_FILE, index=False)
        _git_update(
            f"removed access to {location} ({path}) from {user}" if location else f"remove all access from {user}"
        )
    else:
        pending = _get_pendings()
        su = pending["user"] == user
        if any(su):
            pending[~su].to_csv("pending_" + ACCESS_FILE, index=False)
            message = f"removed {user} from pending without setting permissions"
            _log(message)
            _git_update(message)


def check_access(
    user: "Union[str, None]" = None, location: "Union[str, None]" = None, group: "Union[str, None]" = None, verbose=True
) -> "tuple[pandas.DataFrame, pandas.DataFrame]":
    """
    List and confirm access for a given user, location, and/or group, or all current and pending access.

    Args:
        user (str): User to check access for.
        location (str): Location to check access for.
        group (str): Group to check access for.
        verbose (bool): If `False`, will not print subset access.

    Returns:
        A tuple containing the subset of [0] current and [1] pending access.
    """
    access = _get_accesses()
    pending = _get_pendings()
    if location:
        location = _get_locations().get(location, location)
    if user:
        access = access[access["user"] == user]
        pending = pending[pending["user"] == user]
    if location:
        access = access[access["location"] == location]
        pending = pending[pending["location"] == location]
    if group:
        access = access[access["group"] == group]
        pending = pending[pending["group"] == group]
    if len(access):
        access["actual_permissions"] = "None"
        for check_location in access["location"].unique():
            for current_user, current_perms in _get_current_access(check_location).items():
                target_perms = access[(access["location"] == check_location) & (access["user"] == current_user)]
                if len(target_perms):
                    access.loc[
                        (access["location"] == check_location) & (access["user"] == current_user), "actual_permissions"
                    ] = current_perms
    if verbose:
        if len(access):
            print("current access:\n")
            print(access.to_string())
        if len(pending):
            print("\npending access:\n")
            print(pending.to_string())
        if len(access) == 0 and len(pending) == 0:
            print("no access not found")
    return (access, pending)


def _get_current_access(location: str):
    if GETFACL_PATH:
        current = subprocess.run([GETFACL_PATH, "-dc", location], check=False, capture_output=True)
        if current.stderr != b"":
            msg = f"failed to check current access: {current.stderr.decode('utf-8')}"
            raise RuntimeError(msg)
        access = current.stdout.decode("utf-8")
        if re.search("Not Supported", access):
            msg = "ACLs are not supported on this platform"
            raise RuntimeError(msg)
        current_users: "dict[str, str]" = {}
        for entry in access.split("\n"):
            entry_parts = entry.split(":")
            if len(entry_parts) == 3 and entry_parts[1]:
                current_users[entry_parts[1]] = entry_parts[2]
        return current_users
    else:
        msg = "`getfacl` command not found"
        raise RuntimeError(msg)


def _perms_match(current: str, target: str):
    for perm in ["r", "w", "x"]:
        if (perm in current) is not (perm in target):
            return False
    return True
