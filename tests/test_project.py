import json
import re
import subprocess
from os import chdir, getcwd, listdir, makedirs
from pathlib import Path
from platform import system
from shutil import rmtree, which
from tempfile import TemporaryDirectory

import pandas

import file_access_manager

CLI_PATH = which("manage-access")
USERADD_PATH = which("useradd")
DELUSER_PATH = which("deluser")
GETFACL_PATH = which("getfacl")

LOCATION = "location_name"
USER = "test_user"
GROUP = "test_group"

IS_LINUX = system() == "Linux"


def test_functions():
    with TemporaryDirectory() as temp:
        initial_dir = getcwd()
        project_dir = temp + "/access/"
        rmtree(project_dir, True)
        if IS_LINUX:
            subprocess.run([DELUSER_PATH, USER], check=False, capture_output=True)

        # project initialization
        file_access_manager.init_manager_project(project_dir, allow_dirs="/non/existant")
        assert sorted(listdir(project_dir)) == sorted(
            [
                ".git",
                ".gitignore",
                ".allowed_directories",
                "access.csv",
                "config.json",
                "locations.json",
                "log.txt",
                "pending_access.csv",
                "README.md",
            ]
        )
        chdir(project_dir)
        assert ["/non/existant", ""] == Path(".allowed_directories").read_text().split("\n")

        # named location creation
        test_dir = "../dir_to_access"
        makedirs(test_dir)
        file_access_manager.add_location(LOCATION, test_dir)
        locations = file_access_manager.list_locations()
        assert re.search(f"location_name: {test_dir}", locations)

        # pending access management
        file_access_manager.set_permission(LOCATION, USER, GROUP)
        pending = pandas.read_csv("pending_access.csv")
        assert pending.iloc[0].to_list()[:4] == [USER, GROUP, test_dir, "rx"]

        _, pending_subset = file_access_manager.check_access(USER, pull=False)
        assert all(pending == pending_subset)

        file_access_manager.revoke_permissions(USER)
        pending = pandas.read_csv("pending_access.csv")
        assert USER not in pending["user"].to_list()

        if IS_LINUX:
            # actual access management
            assert subprocess.run([USERADD_PATH, USER], check=False, capture_output=True).returncode == 0

            error = "none"
            try:
                file_access_manager.set_permission(LOCATION, USER, GROUP)
            except RuntimeError as e:
                error = str(e)
            assert "not within an allowed directory" in error
            with open(".allowed_directories", "a", encoding="utf-8") as file:
                file.write(temp + "\n")
            file_access_manager.set_permission(LOCATION, USER, GROUP)
            access = pandas.read_csv("access.csv")
            assert access.iloc[0].to_list()[:4] == [USER, GROUP, test_dir, "rx"]
            assert USER in subprocess.run(
                [GETFACL_PATH, "-ac", test_dir], check=False, capture_output=True
            ).stdout.decode("utf-8")

            access_subset, _ = file_access_manager.check_access(USER, pull=False)
            assert all(access == access_subset[access.columns])

            file_access_manager.revoke_permissions(USER)
            access = pandas.read_csv("access.csv")
            assert USER not in access["user"].to_list()
            subprocess.run([DELUSER_PATH, USER], check=False, capture_output=True)

        # named location removal
        file_access_manager.remove_location(LOCATION)
        locations = file_access_manager.list_locations()
        assert re.match("No named locations", locations)

        # config editing
        file_access_manager.set_options(defer=True)
        with open(f"{project_dir}/config.json", encoding="utf-8") as opened:
            assert json.load(opened)["defer"]

        chdir(initial_dir)


def test_cli():
    with TemporaryDirectory() as temp:
        initial_dir = getcwd()
        project_dir = temp + "/access/"
        rmtree(project_dir, True)
        if IS_LINUX:
            subprocess.run([DELUSER_PATH, USER], check=False, capture_output=True)

        # project initialization
        subprocess.run([CLI_PATH, "init", project_dir], check=False)
        assert sorted(listdir(project_dir)) == sorted(
            [
                ".git",
                ".gitignore",
                "access.csv",
                "config.json",
                "locations.json",
                "log.txt",
                "pending_access.csv",
                "README.md",
            ]
        )
        chdir(project_dir)

        # named location creation
        test_dir = "../dir_to_access"
        makedirs(test_dir)
        subprocess.run([CLI_PATH, "locations", LOCATION, test_dir], check=False, capture_output=True)
        locations = subprocess.run([CLI_PATH, "locations"], check=False, capture_output=True)
        assert re.search(f"location_name: {test_dir}", locations.stdout.decode("utf-8"))

        # pending access management
        subprocess.run([CLI_PATH, LOCATION, USER, GROUP], check=False, capture_output=True)
        pending = pandas.read_csv("pending_access.csv")
        assert pending.iloc[0].to_list()[:4] == [USER, GROUP, test_dir, "rx"]

        res = subprocess.run([CLI_PATH, "check", USER], check=False, capture_output=True)
        assert re.search("pending access", res.stdout.decode("utf-8"))

        subprocess.run([CLI_PATH, "-r", USER], check=False, capture_output=True)
        pending = pandas.read_csv("pending_access.csv")
        assert USER not in pending["user"].to_list()

        if IS_LINUX:
            # actual access management
            assert subprocess.run([USERADD_PATH, USER], check=False, capture_output=True).returncode == 0

            subprocess.run([CLI_PATH, LOCATION, USER, GROUP], check=False, capture_output=True)
            access = pandas.read_csv("access.csv")
            assert access.iloc[0].to_list()[:4] == [USER, GROUP, test_dir, "rx"]

            res = subprocess.run([CLI_PATH, "check", USER], check=False, capture_output=True)
            assert re.search("access", res.stdout.decode("utf-8"))
            assert USER in subprocess.run(
                [GETFACL_PATH, "-ac", test_dir], check=False, capture_output=True
            ).stdout.decode("utf-8")

            file_access_manager.revoke_permissions(USER)
            access = pandas.read_csv("access.csv")
            assert USER not in access["user"].to_list()
            subprocess.run([DELUSER_PATH, USER], check=False, capture_output=True)

        # named location removal
        subprocess.run([CLI_PATH, "locations", "-r", LOCATION], check=False, capture_output=True)
        locations = subprocess.run([CLI_PATH, "locations"], check=False, capture_output=True)
        assert re.match("No named locations", locations.stdout.decode("utf-8"))

        # config editing
        subprocess.run([CLI_PATH, "config", "-d", "true"], check=False, capture_output=True)
        with open(f"{project_dir}/config.json", encoding="utf-8") as opened:
            assert json.load(opened)["defer"]

        chdir(initial_dir)
