"""Command-Line Interface to the File Access Manager"""

import argparse
import sys

from file_access_manager.access import check_access, check_pending, revoke_permissions, set_permission
from file_access_manager.locations import add_location, list_locations, remove_location
from file_access_manager.project import init_manager_project


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
                    "manage-access init\n",
                ]
            )
        )
    possible_function = sys.argv[1]
    if possible_function == "locations":
        parser = argparse.ArgumentParser("manage-access locations", description="Manage named locations.")
        parser.add_argument("name", nargs="?", help="name of the location")
        parser.add_argument("path", nargs="?", help="path to be named")
        parser.add_argument("-r, --remove", dest="remove", help="name to be removed")
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
        parser.add_argument("-m, --managers", dest="managers", nargs="*", help="manager users")
        parser.add_argument("-r, --remote", dest="remote", help="git remote")
        parser.add_argument("-b, --branch", dest="branch", default="main", help="git branch")
        args = parser.parse_args(sys.argv[2:])
        init_manager_project(args.base_dir, managers=args.managers, git_remote=args.remote, git_branch=args.branch)
    elif possible_function == "pending":
        parser = argparse.ArgumentParser(
            "manage-access pending", description="Check pending users, and apply permissions if they now exist."
        )
        check_pending()
    elif possible_function == "check":
        parser = argparse.ArgumentParser(
            "manage-access check", description="Check pending users, and apply permissions if they now exist."
        )
        parser.add_argument("user", nargs="?", help="name of a user to check access for")
        parser.add_argument("-l, --location", dest="location", help="name or path of a location to check access to")
        parser.add_argument("-g, --group", dest="group", help="name of a group to check access for")
        if len(sys.argv) == 2:
            sys.argv.append("--help")
        args = parser.parse_args(sys.argv[2:])
        check_access(args.user, args.location, args.group)
    else:
        parser = argparse.ArgumentParser("manage-access", description="Manage access.")
        parser.add_argument("location", nargs="?", help="path, or name of a location")
        parser.add_argument("user", nargs="?", help="name of the user to grant access to")
        parser.add_argument("group", nargs="?", help="group to assign the user to")
        parser.add_argument("-p, --perms", default="rx", dest="permissions", help="permissions to set to the user")
        parser.add_argument("-r, --remove", dest="remove", help="user to revoke access from")
        args = parser.parse_args(sys.argv[1:])
        if args.remove:
            revoke_permissions(args.remove, args.location)
        elif args.user and args.location:
            set_permission(location=args.location, user=args.user, group=args.group, permissions=args.permissions)
        else:
            msg = "specify at least a user and location"
            raise RuntimeError(msg)
