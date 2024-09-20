"""Manage user access."""

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


def set_permission(location: str, user: str, group: "Union[str, None]" = None, permissions="rx"):
    """
    Grant a user permission, and add them to a group.

    Args:
        location (str): Name of a location, or path, to grant `user` `permissions` to.
        user (str): Name of the user.
        group (str): Group to assign the user to. Defaults to the user themselves. Here,
            groups grant the user the group's access, and any permissions assigned to the
            user under the group would be removed with the group not on removal from the group.
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
    changed = False
    if ID_PATH and subprocess.run([ID_PATH, user], check=False, capture_output=True).stderr != b"":
        pending = _get_pendings()
        updated = _append_row(pending, user, group, path, permissions)
        if len(pending) != len(updated):
            updated.to_csv("pending_" + ACCESS_FILE, index=False)
            _log(f"added {user} to pending because they do not exist")
            changed = True
    else:
        res = _set_permissions(user, path, permissions)
        if res.stderr == b"":
            updated = _append_row(access, user, group, path, permissions)
            if len(access) != len(updated):
                updated.to_csv(ACCESS_FILE, index=False)
                _log(f"set permissions for {user}: can {permissions} {path}, under {group}")
                changed = True
        else:
            error = res.stderr.decode("utf-8").strip().replace("\n", " ")
            _log(f"failed to set permissions for {user}: {error}")
    if changed:
        _git_update(f"set permissions to {location} for {user} under {group}")


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
        return res


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
        return subprocess.run([SETFACL_PATH, "-x", f"d:u:{user}", path], check=False, capture_output=True)


def revoke_permissions(user: str, location: "Union[str, None]" = None):
    access = _get_accesses()
    removed = su = access["user"] == user
    if any(su):
        if location:
            _revoke(user, location)
            removed = removed & access["location"] == location
            _log(f"removed permissions from {user}: can no longer access {location}")
        else:
            for path in access["location"][su]:
                _revoke(user, path)
            _log(f"removed all permissions from {user}")
        group_access = access[~su & access["group"] == user]
        if len(group_access):
            removed = removed | access["group"] == user
            if location:
                group_access = group_access[group_access["location"] == location]
                if len(group_access):
                    for sub_user in group_access["user"]:
                        _revoke(sub_user, location)
                        _log(f"removed permissions from {sub_user}: can no longer access {location} under {user}")
                    removed = removed & access["location"] == location
            else:
                for sub_user, path in zip(group_access["user"], group_access["location"]):
                    _revoke(sub_user, path)
                    _log(f"removed permissions from {sub_user}: can no longer access {path} under {user}")
        access = access[~removed]
        access.to_csv(ACCESS_FILE, index=False)
        _git_update(f"removed access to {location} from {user}")
    else:
        pending = _get_pendings()
        su = pending["user"] == user
        if any(su):
            pending[~su].to_csv("pending_" + ACCESS_FILE, index=False)
            message = f"removed {user} from pending without setting permissions"
            _log(message)
            _git_update(message)


def check_access(
    user: "Union[str, None]" = None, location: "Union[str, None]" = None, group: "Union[str, None]" = None
):
    access = _get_accesses()
    pending = _get_pendings()
    col_name = "user" if user else "group" if group else "location"
    value = user if user else group if group else location
    if user:
        subset = access[access[col_name] == value]
        if len(subset):
            print(f"\ncurrent {col_name} access:\n")
            print(subset.to_string())
        pending_subset = pending[pending[col_name] == value]
        if len(pending_subset):
            print(f"\npending {col_name} access:\n")
            print(pending_subset.to_string())
        else:
            print(f"{col_name} {value} not found")
    return (subset, pending_subset)
