"""Manage user access."""

import re
import subprocess
import warnings
from os.path import dirname, isdir, isfile
from shutil import which
from time import ctime
from typing import Union

import pandas

from file_access_manager.locations import _get_locations
from file_access_manager.project import (
    ACCESS_FILE,
    ACCESS_STRUCTURE,
    GIT_PATH,
    _check_for_project,
    _get_config,
    _git_update,
)

ID_PATH = which("id")
SETFACL_PATH = which("setfacl")
GETFACL_PATH = which("getfacl")


def set_permission(location: str, user: str, group: Union[str, None] = None, permissions="rx", parents=1):
    """
    Grant a user permission, and add them to a group.

    Args:
        location (str): Name of a location, or path, to grant `user` `permissions` to.
        user (str): Name of the user.
        group (str): Group to assign the user to. Defaults to the user themselves. Here,
            groups grant the user the group's access, and any permissions assigned to the
            user in the group would be removed with the group not on removal from the group.
        permissions (str): Permission string (e.g., "rwx").
        parents (int): Number of parent directories on which to set read and execute permissions.
    """
    access = _get_accesses()
    defer = _get_config().get("defer", False)
    if isdir(location):
        path = location
    else:
        path = _get_locations().get(location, "")
        if not defer and not isdir(path):
            msg = f"location ({location}) does not exist"
            raise RuntimeError(msg)
    path = path.replace("[\\/]$", "")
    if not group:
        group = user
    message = ""
    if defer or (ID_PATH and subprocess.run([ID_PATH, user], check=False, capture_output=True).stderr != b""):
        pending = _get_pendings()
        updated = _append_row(pending, user, group, path, permissions, parents)
        if not updated.equals(pending):
            updated.to_csv("pending_" + ACCESS_FILE, index=False)
            message = f"added {user} to pending access for {location} in group {group}"
            _log(message)
    else:
        _apply_to_parent(user, path, parents)
        res = _set_permissions(user, path, permissions)
        if res.stderr == b"":
            updated = _append_row(access, user, group, path, permissions, parents)
            if not updated.equals(access):
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


def _set_permissions(user: str, path: str, perms: str, recursive=True):
    if SETFACL_PATH:
        res = subprocess.run(
            [SETFACL_PATH, *(["-R", "-m"] if recursive else ["-m"]), f"u:{user}:{perms}", path],
            check=False,
            capture_output=True,
        )
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
                warnings.warn(msg, stacklevel=2)
        return res
    msg = "`setfacl` command not found"
    raise RuntimeError(msg)


def _apply_to_parent(user: str, path: str, parents: int):
    failed = False
    parent = path
    for _ in range(parents):
        parent = dirname(parent)
        if parent:
            res = _set_permissions(user, parent, "rx", False)
            failed = res.stderr != b"" or not user in _get_current_access(parent)
            if failed:
                break
        else:
            break
    if failed:
        print(res.stderr)
        _log(f"failed to set permissions on parents for {user}")
    return not failed


def _append_row(current: pandas.DataFrame, user: str, group: str, location: str, permissions: str, parents: int):
    new_row = pandas.DataFrame(
        {
            "user": [user],
            "group": [group],
            "location": [location],
            "permissions": [permissions],
            "parents": [parents],
            "date": [ctime()],
        }
    )
    return (
        pandas.concat([new_row, current], ignore_index=True)
        .drop_duplicates(["user", "group", "location"])
        .sort_values(["user", "group", "location"])
    )


def _log(message: str):
    with open("log.txt", "a", encoding="utf-8") as opened:
        opened.write(f"{ctime()}: {message}\n")


def check_pending(pull=True, push=False, update=True):
    """
    Check any users pending access, and apply permissions if they exist.

    Args:
        pull (bool): If `False`, will not pull the remote before checking pending.
        push (bool): If `True`, will push any changes made (bypassing auto_push option).
        update (bool): If `False`, will not change pending or access files.
    """
    if pull and GIT_PATH and isdir(".git"):
        if subprocess.run([GIT_PATH, "pull"], check=False, capture_output=True).stderr != b"":
            warnings.warn("failed to pull before checking pending", stacklevel=2)
    pending_file = "pending_" + ACCESS_FILE
    if isfile(pending_file):
        pending = _get_pendings()
        updated = False
        for user, access in pending.groupby("user"):
            if _user_exists(user):
                for group, location, permissions, parents in zip(
                    access["group"], access["location"], access["permissions"], access["parents"]
                ):
                    if pandas.isna(permissions):
                        updated = revoke_permissions(user, "" if pandas.isna(location) else location, True)
                    elif isdir(location):
                        _set_permissions(user, location, permissions)
                        _apply_to_parent(user, location, parents)
                        updated = True
                        current_access = _get_accesses()
                        added_access = _append_row(current_access, user, group, location, permissions, parents)
                        if update and not added_access.equals(current_access):
                            added_access.to_csv(ACCESS_FILE, index=False)
                            _log(f"set permissions to {location} for {user} in group {group}")
                    if updated:
                        pending = pending[~((pending["user"] == user) & (pending["location"] == location))]
        if update and updated:
            pending.to_csv(pending_file, index=False)
            _git_update("processed pending permissions", push)
    else:
        print("no pending users")


def _user_exists(user: str):
    return ID_PATH and subprocess.run([ID_PATH, user], check=False, capture_output=True).stderr == b""


def _revoke(user: str, path: str, recursive=True):
    if not recursive:
        set_perms = _get_current_access(path)
        if user not in set_perms:
            return True
    if SETFACL_PATH:
        res = subprocess.run(
            [SETFACL_PATH, *(["-R", "-x"] if recursive else ["-x"]), f"u:{user}", path],
            check=False,
            capture_output=True,
        )
        success = res.stderr == b""
        failure_message = f"failed to revoke access to {path} from {user}: "
        if success:
            set_perms = _get_current_access(path)
            if user in set_perms:
                success = False
                warnings.warn(failure_message + "still appears in access list", stacklevel=2)
        else:
            warnings.warn(failure_message + res.stderr.decode("utf-8"), stacklevel=2)
        return success
    msg = "`setfacl` command not found"
    raise RuntimeError(msg)


def revoke_permissions(user: str, location: "Union[str, None]" = None, from_pending=False):
    """
    Remove access from a user.

    Args:
        user (str): User to remove access from.
        location (str): Location to remove `user`s access from; if not
            specified, access from all locations will be removed.
        from_pending (bool): If `False`, will not also remove the user from pending access.
    """
    access = _get_accesses()
    removed = su = access["user"] == user
    if any(su):
        path = ""
        any_fail = False
        if location:
            locations = _get_locations()
            path = locations.get(location, location)
        if not from_pending and _get_config().get("defer", False):
            pending = _get_pendings()
            updated = _append_row(pending, user, user, path, "", 0)
            if not updated.equals(pending):
                updated.to_csv("pending_" + ACCESS_FILE, index=False)
                message = f"added {user} to pending removal" + (f" from {location}" if location else "")
                _log(message)
                _git_update(message)
            return False
        if location:
            parents = access.loc[su & (access["location"] == path), "parents"].max()
            alt_access = access.loc[su & (access["location"] != path), "location"].unique()
            parent_path = dirname(path)
            for _ in range(parents):
                retain = False
                for alt_path in alt_access:
                    if parent_path in alt_path:
                        retain = True
                        break
                if not retain and not _revoke(user, parent_path, False):
                    any_fail = True
                parent_path = dirname(parent_path)
            removed = removed & (access["location"] == path)
            success = _revoke(user, path)
            if success:
                _log(f"removed permissions from {user}: they can no longer access {path}")
            else:
                any_fail = True
        else:
            user_access = access[su]
            any_parent_fail = False
            for path, parents in zip(user_access["location"], user_access["parents"]):
                parent = path
                for _ in range(parents):
                    parent = dirname(parent)
                    if parent:
                        success = _revoke(user, parent, False)
                        if not success:
                            any_parent_fail = True
                    else:
                        break
                success = _revoke(user, path)
                if not success:
                    any_parent_fail = True
            if not any_parent_fail:
                _log(f"removed all permissions from {user}")
            else:
                access.loc[su, "permissions"] = "---"
                any_fail = True
        group_access = access[~su & (access["group"] == user)]
        if len(group_access):
            removed = removed | (access["group"] == user)
            if location:
                removed = removed & (access["location"] == path)
                group_access = group_access[group_access["location"] == path]
                if len(group_access):
                    for sub_user in group_access["user"]:
                        success = _revoke(sub_user, path)
                        if success:
                            _log(f"removed permissions from {sub_user}: they can no longer access {path} under {user}")
                        else:
                            any_fail = True
            else:
                for sub_user, path in zip(group_access["user"], group_access["location"]):
                    success = _revoke(sub_user, path)
                    if success:
                        _log(f"removed permissions from {sub_user}: they can no longer access {path} under {user}")
                    else:
                        any_fail = True
        if any_fail:
            access.loc[removed, "permissions"] = "---"
            access.to_csv(ACCESS_FILE, index=False)
            _git_update(
                "failed to remove "
                + (f"access to {location} ({path}) from {user}" if location else f"all access from {user}")
                + ", so setting blank permissions temporarily"
            )
        else:
            access[~removed].to_csv(ACCESS_FILE, index=False)
            _git_update(
                f"removed access to {location} ({path}) from {user}" if location else f"removed all access from {user}"
            )
            return True
    elif not from_pending:
        pending = _get_pendings()
        su = pending["user"] == user
        if any(su):
            pending[~su].to_csv("pending_" + ACCESS_FILE, index=False)
            message = f"removed {user} from pending without setting permissions"
            _log(message)
            _git_update(message)
    return False


def check_access(
    user: "Union[str, None]" = None,
    location: "Union[str, None]" = None,
    group: "Union[str, None]" = None,
    pull=True,
    reapply=True,
    verbose=True,
) -> "tuple[pandas.DataFrame, pandas.DataFrame]":
    """
    List and confirm access for a given user, location, and/or group, or all current and pending access.

    Args:
        user (str): User to check access for.
        location (str): Location to check access for.
        group (str): Group to check access for.
        pull (bool): If `False`, will not pull the remote before checking access.
        reapply (bool): If `False`, will attempt to set all permissions check checking.
        verbose (bool): If `False`, will not print subset access.

    Returns:
        A tuple containing [0] current and [1] pending access.
    """
    if pull and GIT_PATH and isdir(".git"):
        if subprocess.run([GIT_PATH, "pull"], check=False, capture_output=True).stderr != b"":
            warnings.warn("failed to pull before checking pending", stacklevel=2)
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
        access["access_to_parents"] = False
        for check_location in access["location"].unique():
            if isdir(check_location):
                target_access = access[access["location"] == check_location]
                current_access = _get_current_access(check_location)
                for current_user in target_access["user"].unique():
                    target_perms = target_access[target_access["user"] == current_user]
                    if len(target_perms):
                        current_perms = current_access.get(current_user)
                        if reapply:
                            res = _set_permissions(current_user, check_location, target_perms.iloc[0]["permissions"])
                            if res.stderr == b"":
                                current_perms = target_perms.iloc[0]["permissions"]
                        access.loc[
                            (access["location"] == check_location) & (access["user"] == current_user),
                            "actual_permissions",
                        ] = current_perms
                        access.loc[
                            (access["location"] == check_location) & (access["user"] == current_user),
                            "access_to_parents",
                        ] = _apply_to_parent(current_user, check_location, target_perms.iloc[0]["parents"])
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
        current = subprocess.run([GETFACL_PATH, "-ac", location], check=False, capture_output=True)
        if current.stdout == b"" and current.stderr != b"":
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
