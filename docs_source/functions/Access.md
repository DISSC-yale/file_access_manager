::: file_access_manager.access

## Command Line

```sh
usage: manage-access [-h] [-p PERMISSIONS] [-r REMOVE] [-n PARENTS]
                     [location] [user] [group]

Manage access.

positional arguments:
  location              path, or name of a location
  user                  name of the user to grant access to
  group                 group to assign the user to

options:
  -h, --help            show this help message and exit
  -p PERMISSIONS, --perms PERMISSIONS
                        permissions to set to the user
  -r REMOVE, --remove REMOVE
                        user to revoke access from
  -n PARENTS, --parents PARENTS
                        number of parent directories to also assign read and
                        execute permission to
```

### pending

```sh
usage: manage-access pending [-h] [-i] [-o] [-u]

Check pending users, and apply permissions if they now exist.

options:
  -h, --help       show this help message and exit
  -i, --no-pull    do not git pull before checking pending
  -o, --push       git commit and push after applying pending
  -u, --no-update  do not update pending and access files
```

### check

```sh
usage: manage-access check [-h] [-l LOCATION] [-g GROUP] [-p] [-a] [user]

Check pending users, and apply permissions if they now exist.

positional arguments:
  user                  name of a user to check access for

options:
  -h, --help            show this help message and exit
  -l LOCATION, --location LOCATION
                        name or path of a location to check access to
  -g GROUP, --group GROUP
                        name of a group to check access for
  -p, --no-pull         disable pull from remote before checking access
  -a, --no-reapply      disable application during check
```