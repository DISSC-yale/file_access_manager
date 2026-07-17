"""Project initialization and management."""

import json
import subprocess
from os import chdir, getcwd, makedirs
from os.path import abspath, exists
from pathlib import Path
from shutil import which
from typing import Union

import pandas

ACCESS_FILE = "access.csv"
ACCESS_STRUCTURE = {"user": str, "group": str, "location": str, "permissions": str, "parents": int, "date": str}
LOCATIONS_FILE = "locations.json"
ALLOW_DIRS_FILE = ".allowed_directories"
GIT_PATH = which("git")


def init_manager_project(
    base_dir: str = ".",
    locations: "Union[dict[str, str], None]" = None,
    allow_dirs: "Union[str, list[str], None]" = None,
    git_remote: "Union[str, None]" = None,
    auto_commit: bool = True,
    auto_push: bool = False,
    defer: bool = False,
    git_branch: str = "main",
):
    """
    Initialize a file access management project.

    Args:
        base_dir (str): Path to a directory in which to establish the project.
        locations (dict[str, str]): A dictionary of initial locations, with names associated with paths.
        allow_dirs (str | list[str]): A directory or list of directories within which access may be managed.
            If ommited, any directory is allowed.
        git_remote (str): Location of a remote repository.
        auto_commit (bool): If `False`, will not commit after each action. This is added to the `config.json` file.
        auto_push (bool): If `True`, will push to the remote after each action. This is added to the `config.json` file.
        defer (bool): If `True`, will always add users to pending, leaving actual access granting to a later process.
        git_branch (str): Name of the branch to initially pull in or create.
    """
    makedirs(base_dir, exist_ok=True)
    initial_dir = getcwd()
    chdir(base_dir)
    fresh = False
    if GIT_PATH:
        subprocess.run([GIT_PATH, "init"], check=False, capture_output=True)
    if git_remote:
        if not GIT_PATH:
            chdir(initial_dir)
            msg = "`git` is not available"
            raise RuntimeError(msg)
        subprocess.run([GIT_PATH, "remote", "add", "origin", git_remote], check=False)
    if (
        GIT_PATH
        and not exists(".gitignore")
        and subprocess.run([GIT_PATH, "pull", "origin", git_branch], check=False, capture_output=True).returncode != 0
    ):
        # first-time git setup
        fresh = True
        subprocess.run([GIT_PATH, "checkout", "-b", git_branch], check=False, capture_output=True)
        with open(".gitignore", "w", encoding="utf-8") as opened:
            opened.write(".*\n!.gitignore")
    set_options(auto_commit=auto_commit, auto_push=auto_push, defer=defer)
    if locations:
        if exists(LOCATIONS_FILE):
            with open(LOCATIONS_FILE, encoding="utf-8") as opened:
                locations = {**json.load(opened), **locations}
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as opened:
            json.dump(locations, opened, indent=2, sort_keys=True)
    elif not exists(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as opened:
            opened.write("{}")
    Path.touch(Path("log.txt"), exist_ok=True)
    if not exists(ACCESS_FILE):
        pandas.DataFrame(columns=list(ACCESS_STRUCTURE.keys())).to_csv(ACCESS_FILE, index=False)
    if not exists("pending_" + ACCESS_FILE):
        pandas.DataFrame(columns=list(ACCESS_STRUCTURE.keys())).to_csv("pending_" + ACCESS_FILE, index=False)
    if not exists("README.md"):
        with open("README.md", "w", encoding="utf-8") as opened:
            opened.write(
                "\n\n".join(
                    [
                        "This is an access management project initialized by `manage-access init` from the"
                        " [file_access_manager](https://dissc-yale.github.io/file_access_manager/) package.",
                        "Install that package with pip:",
                        "```sh\npip install git+https://github.com/DISSC-yale/file_access_manager.git\n```",
                        "Then you can use the `manage-access` commands:",
                        "```sh\nmanage-access -h\nmanage-access locations -h\n```",
                    ]
                )
            )
    if allow_dirs:
        if isinstance(allow_dirs, str):
            allow_dirs = [allow_dirs]
        with open(ALLOW_DIRS_FILE, "w", encoding="utf-8") as file:
            file.write("\n".join(allow_dirs) + "\n")
    _git_update("initial commit" if fresh else "reinitialized")
    chdir(initial_dir)


def set_options(**kwargs: Union[bool, str]):
    """
    Set Project Options

    Args:
        **kwargs: Named options with associated values:

            - `auto_commit`: If `False`, will not git commit each access actions; defaults to `True`.
            - `auto_push`: If `True`, will not git push each access actions; defaults to `False`.
            - `defer`: If `True`, will always initially add users to pending without checking if they
                exist, leaving permission setting to a separate process; defaults to `False`.

    Examples:
        >>> file_access_manager.set_options(defer=True)
    """
    file = "config.json"
    current = _get_config()
    for name, value in kwargs.items():
        if name not in ["auto_commit", "auto_push", "defer"]:
            msg = f"{name} is not a recognized option"
            raise RuntimeError(msg)
        if value is not None:
            current[name] = value if isinstance(value, bool) else value.lower() == "true"
    with open(file, "w", encoding="utf-8") as opened:
        json.dump(current, opened, indent=2, sort_keys=True)
    return current


def _get_config():
    file = "config.json"
    if not exists(file):
        config = {"auto_commit": True, "auto_push": False, "defer": False}
        with open(file, "w", encoding="utf-8") as opened:
            json.dump(config, opened, indent=2, sort_keys=True)
    else:
        with open(file, encoding="utf-8") as opened:
            config = json.load(opened)
    return config


def _git_update(message: Union[str, None] = None, bypass: bool = False):
    config = _get_config()
    if exists(".git") and GIT_PATH:
        if message and (config["auto_commit"] or bypass):
            subprocess.run([GIT_PATH, "add", "-A"], check=False)
            subprocess.run([GIT_PATH, "commit", "-m", message], check=False)
        if config["auto_push"] or bypass:
            subprocess.run([GIT_PATH, "push"], check=False)


def _check_for_project(file: str):
    if not exists(file):
        msg = f"directory does not appear to be an access management project ({file} does not exist)"
        raise RuntimeError(msg)


def _validate_location(path: str):
    allowed_dirs: "list[str]" = []
    if exists(ALLOW_DIRS_FILE):
        with open(ALLOW_DIRS_FILE, encoding="utf-8") as file:
            for line in file.readlines():
                allowed_dirs.append(abspath(line.rstrip()))
    if not allowed_dirs:
        return True
    normed = abspath(path)
    for allowed in allowed_dirs:
        if normed.startswith(allowed):
            return True
    return False
