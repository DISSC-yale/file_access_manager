"""Command-Line Interface to the File Access Manager"""

import argparse
import sys

from file_access_manager.access import check_access, check_pending, revoke_permissions, set_permission
from file_access_manager.locations import add_location, list_locations, remove_location
from file_access_manager.project import init_manager_project, set_options


def main():
    """CLI entry point."""
    if len(sys.argv) == 1:
        return print(
            "\n  ".join(
                [
                    "Basic usage: manage-access [location] [user] [group]\n\n"
                    "Use --help to see help for managing access, or use one of the commands:\n",
                    "manage-access locations",
                    "manage-access check",
                    "manage-access pending",
                    "manage-access config",
                    "manage-access init\n",
                ]
            )
        )
    possible_function = sys.argv[1]
    if possible_function == "locations":
        parser = argparse.ArgumentParser("manage-access locations", description="Manage named locations.")
        parser.add_argument("name", nargs="?", help="name of the location")
        parser.add_argument("path", nargs="?", help="path to be named")
        parser.add_argument("-r", "--remove", dest="remove", help="name to be removed")
        args = parser.parse_args(sys.argv[2:])
        if args.remove:
            remove_location(args.remove)
        elif not args.name:
            list_locations()
        elif args.path:
            add_location(args.name, args.path)
        else:
            parser.print_help()
    elif possible_function == "init":
        parser = argparse.ArgumentParser("manage-access init", description="Initialize an access manager project.")
        parser.add_argument("base_dir", nargs="?", default=".", help="directory of the access manager project")
        parser.add_argument("-m", "--managers", dest="managers", nargs="*", help="manager users")
        parser.add_argument("-r", "--remote", dest="remote", help="git remote")
        parser.add_argument("-b", "--branch", dest="branch", default="main", help="git branch")
        args = parser.parse_args(sys.argv[2:])
        init_manager_project(args.base_dir, managers=args.managers, git_remote=args.remote, git_branch=args.branch)
    elif possible_function == "config":
        parser = argparse.ArgumentParser(
            "manage-access config", description="Configure an access manager project.", allow_abbrev=True
        )
        parser.add_argument(
            "-c",
            "--auto_commit",
            dest="auto_commit",
            default=None,
            help="automatically commit access actions",
        )
        parser.add_argument(
            "-p",
            "--auto_push",
            dest="auto_push",
            default=None,
            help="automatically push committed access actions",
        )
        parser.add_argument(
            "-d",
            "--defer",
            dest="defer",
            default=None,
            help="defer access setting to a separate process",
        )
        args = parser.parse_args(sys.argv[2:])
        set_options(auto_commit=args.auto_commit, auto_push=args.auto_push, defer=args.defer)
    elif possible_function == "pending":
        parser = argparse.ArgumentParser(
            "manage-access pending", description="Check pending users, and apply permissions if they now exist."
        )
        parser.add_argument(
            "-i", "--no-pull", dest="pull", action="store_true", help="do not git pull before checking pending"
        )
        parser.add_argument(
            "-o",
            "--push",
            dest="push",
            action="store_true",
            help="git commit and push after applying pending",
        )
        parser.add_argument(
            "-u",
            "--no-update",
            dest="update",
            action="store_true",
            help="do not update pending and access files",
        )
        args = parser.parse_args(sys.argv[2:])
        check_pending(not args.pull, args.push, not args.update)
    elif possible_function == "check":
        parser = argparse.ArgumentParser(
            "manage-access check", description="Check pending users, and apply permissions if they now exist."
        )
        parser.add_argument("user", nargs="?", help="name of a user to check access for")
        parser.add_argument("-l", "--location", dest="location", help="name or path of a location to check access to")
        parser.add_argument("-g", "--group", dest="group", help="name of a group to check access for")
        parser.add_argument(
            "-p",
            "--no-pull",
            dest="pull",
            action="store_true",
            help="disable pull from remote before checking access",
        )
        parser.add_argument(
            "-a", "--no-reapply", dest="reapply", action="store_true", help="disable application during check"
        )
        args = parser.parse_args(sys.argv[2:])
        check_access(args.user, args.location, args.group, not args.pull, not args.reapply)
    else:
        parser = argparse.ArgumentParser("manage-access", description="Manage access.")
        parser.add_argument("location", nargs="?", help="path, or name of a location")
        parser.add_argument("user", nargs="?", help="name of the user to grant access to")
        parser.add_argument("group", nargs="?", help="group to assign the user to")
        parser.add_argument("-p", "--perms", default="rx", dest="permissions", help="permissions to set to the user")
        parser.add_argument("-r", "--remove", dest="remove", help="user to revoke access from")
        parser.add_argument(
            "-n",
            "--parents",
            dest="parents",
            default=1,
            help="number of parent directories to also assign read and execute permission to",
        )
        args = parser.parse_args(sys.argv[1:])
        if args.remove:
            revoke_permissions(args.remove, args.location)
        elif args.user and args.location:
            set_permission(
                location=args.location,
                user=args.user,
                group=args.group,
                permissions=args.permissions,
                parents=args.parents,
            )
        else:
            msg = "specify at least a user and location"
            raise RuntimeError(msg)
