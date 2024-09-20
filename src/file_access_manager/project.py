"""Project initialization and management."""

import json
import subprocess
from os import chdir, makedirs
from os.path import isdir, isfile
from pathlib import Path
from shutil import which
from typing import Union

import pandas

ACCESS_FILE = "access.csv"
ACCESS_STRUCTURE = {"user": str, "group": str, "location": str, "permissions": str, "date": str}
LOCATIONS_FILE = "locations.json"
GIT_PATH = which("git")


def init_manager_project(
    base_dir=".",
    managers: "Union[list[str], None]" = None,
    locations: "Union[dict[str, str], None]" = None,
    git_remote: "Union[str, None]" = None,
    auto_commit=True,
    auto_push=False,
    git_branch="main",
):
    """
    Initialize a file access management project.

    Args:
        base_dir (str): Path to a directory in which to establish the project.
        managers (list[str]): A list of users who should have full access to all locations.
        locations (dict[str, str]): A dictionary of initial locations, with names associated with paths.
        git_remote (str): Location of a remote repository.
        auto_commit (bool): If `False`, will not commit after each action. This is added to the `config.json` file.
        auto_push (bool): If `True`, will push to the remote after each action. This is added to the `config.json` file.
        git_branch (str): Name of the branch to initially pull in or create.
    """
    makedirs(base_dir, exist_ok=True)
    chdir(base_dir)
    fresh = False
    if GIT_PATH:
        subprocess.run([GIT_PATH, "init"], check=False, capture_output=True)
    if git_remote:
        if not GIT_PATH:
            msg = "`git` is not available"
            raise RuntimeError(msg)
        subprocess.run([GIT_PATH, "remote", "add", "origin", git_remote], check=False)
    if (
        GIT_PATH
        and not isfile(".gitignore")
        and subprocess.run([GIT_PATH, "pull", "origin", git_branch], check=False, capture_output=True).stderr != b""
    ):
        # first-time git setup
        fresh = True
        subprocess.run([GIT_PATH, "checkout", "-b", git_branch], check=False, capture_output=True)
        with open(".gitignore", "w", encoding="utf-8") as opened:
            opened.write(".*\n!.gitignore")
    config = _get_config()
    config["auto_commit"] = auto_commit
    config["auto_push"] = auto_push
    with open("config.json", "w", encoding="utf-8") as opened:
        json.dump(config, opened, indent=2, sort_keys=True)
    if managers:
        managers_file = "managers.txt"
        if isfile(managers_file):
            with open(managers_file, encoding="utf-8") as opened:
                for user in opened.readlines():
                    if user not in managers:
                        managers.append(user)
        with open(managers_file, "w", encoding="utf-8") as opened:
            opened.write("\n".join(managers))
    if locations:
        if isfile(LOCATIONS_FILE):
            with open(LOCATIONS_FILE, encoding="utf-8") as opened:
                locations = {**json.load(opened), **locations}
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as opened:
            json.dump(locations, opened, indent=2, sort_keys=True)
    elif not isfile(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as opened:
            opened.write("{}")
    Path.touch(Path("log.txt"), exist_ok=True)
    if not isfile(ACCESS_FILE):
        pandas.DataFrame(columns=list(ACCESS_STRUCTURE.keys())).to_csv(ACCESS_FILE, index=False)
        pandas.DataFrame(columns=list(ACCESS_STRUCTURE.keys())).to_csv("pending_" + ACCESS_FILE, index=False)
    _git_update("initial commit" if fresh else "reinitialized")


def _get_config():
    file = "config.json"
    if not isfile(file):
        config = {"auto_commit": True, "auto_push": False}
        with open(file, "w", encoding="utf-8") as opened:
            json.dump(config, opened, indent=2, sort_keys=True)
    else:
        with open(file, encoding="utf-8") as opened:
            config = json.load(opened)
    return config


def _git_update(message: str):
    config = _get_config()
    if isdir(".git") and GIT_PATH:
        if config["auto_commit"]:
            subprocess.run([GIT_PATH, "add", "-A"], check=False)
            subprocess.run([GIT_PATH, "commit", "-m", message], check=False)
        if config["auto_push"]:
            subprocess.run([GIT_PATH, "push"], check=False)


def _check_for_project(file: str):
    if not isfile(file):
        msg = f"directory does not appear to be an access management project ({file} does not exist)"
        raise RuntimeError(msg)
