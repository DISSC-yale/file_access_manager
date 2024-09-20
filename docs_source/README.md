A Python command-line interface package to manage access to directories.

The main use-case in mind is to manage access of researchers to data files.

## Features

- Grant or revoke access of users or groups of users (e.g., principal investigators and their collaborators or research assistants)
- Keep a list of users needing access, pending account creation
- Establish named paths (e.g., dataset names associated with their location)
- Track access status changes of users and datasets

## System Requirements

This package manages access through [Access Control Lists](https://linux.die.net/man/5/acl),
so this should work on any system with the `getfacl` and `setfacl` commands.

## Installation

If needed, download Python from [python.org](https://www.python.org/downloads), then install the package with pip:

```sh
pip install git+https://github.com/DISSC-yale/file_access_manager.git
```

## Usage

Initialize an access management project:

```sh
manage-access init
```

Name a location:

```sh
manage-access locations location_name /full/path/to/location
```

Manage access to that location:

```sh
# add a user
manage-access location_name user1

# add a user to that user's group
manage-access location_name user2 user1

# remove user and their group(s) from all locations
manage-access -r user1
```
