import re
import subprocess
from os import chdir, getcwd, listdir, makedirs
from shutil import which
from tempfile import TemporaryDirectory

import pandas

import file_access_manager

CLI_PATH = which("manage-access")


def test_functions():
    with TemporaryDirectory() as temp:
        initial_dir = getcwd()
        project_dir = temp + "/access/"

        # project initialization
        file_access_manager.init_manager_project(project_dir)
        assert listdir(project_dir) == [
            ".git",
            ".gitignore",
            "access.csv",
            "config.json",
            "locations.json",
            "log.txt",
            "pending_access.csv",
            "README.md",
        ]
        chdir(project_dir)

        # named location creation
        test_dir = "../dir_to_access"
        makedirs(test_dir)
        file_access_manager.add_location("location_name", test_dir)
        locations = file_access_manager.list_locations()
        assert re.search(f"location_name: {test_dir}", locations)

        # access management
        file_access_manager.set_permission("location_name", "user_name", "group_name")
        pending = pandas.read_csv("pending_access.csv")
        assert pending.iloc[0].to_list()[:4] == ["user_name", "group_name", test_dir, "rx"]

        _, pending_subset = file_access_manager.check_access("user_name")
        assert all(pending == pending_subset)

        file_access_manager.revoke_permissions("user_name")
        pending = pandas.read_csv("pending_access.csv")
        assert "user_name" not in pending["user"].to_list()

        # named location removal
        file_access_manager.remove_location("location_name")
        locations = file_access_manager.list_locations()
        assert re.match("No named locations", locations)
        chdir(initial_dir)


def test_cli():
    with TemporaryDirectory() as temp:
        initial_dir = getcwd()
        project_dir = temp + "/access/"

        # project initialization
        subprocess.run([CLI_PATH, "init", project_dir], check=False)
        assert listdir(project_dir) == [
            ".git",
            ".gitignore",
            "access.csv",
            "config.json",
            "locations.json",
            "log.txt",
            "pending_access.csv",
            "README.md",
        ]
        chdir(project_dir)

        # named location creation
        test_dir = "../dir_to_access"
        makedirs(test_dir)
        subprocess.run([CLI_PATH, "locations", "location_name", test_dir], check=False, capture_output=True)
        locations = subprocess.run([CLI_PATH, "locations"], check=False, capture_output=True)
        assert re.search(f"location_name: {test_dir}", locations.stdout.decode("utf-8"))

        # access management
        subprocess.run([CLI_PATH, "location_name", "user_name", "group_name"], check=False, capture_output=True)
        pending = pandas.read_csv("pending_access.csv")
        assert pending.iloc[0].to_list()[:4] == ["user_name", "group_name", test_dir, "rx"]

        res = subprocess.run([CLI_PATH, "check", "user_name"], check=False, capture_output=True)
        assert re.search("pending access", res.stdout.decode("utf-8"))

        subprocess.run([CLI_PATH, "-r", "user_name"], check=False, capture_output=True)
        pending = pandas.read_csv("pending_access.csv")
        assert "user_name" not in pending["user"].to_list()

        # named location removal
        subprocess.run([CLI_PATH, "locations", "-r", "location_name"], check=False, capture_output=True)
        locations = subprocess.run([CLI_PATH, "locations"], check=False, capture_output=True)
        assert re.match("No named locations", locations.stdout.decode("utf-8"))
        chdir(initial_dir)
