::: file_access_manager.project

## Command Line

### init

```sh
usage: manage-access init [-h] [-m [MANAGERS ...]] [-r REMOTE] [-b BRANCH]
                          [base_dir]

Initialize an access manager project.

positional arguments:
  base_dir              directory of the access manager project

options:
  -h, --help            show this help message and exit
  -m [MANAGERS ...], --managers [MANAGERS ...]
                        manager users
  -r REMOTE, --remote REMOTE
                        git remote
  -b BRANCH, --branch BRANCH
                        git branch
```

### config

```sh
usage: manage-access config [-h] [-c AUTO_COMMIT] [-p AUTO_PUSH] [-d DEFER]

Configure an access manager project.

options:
  -h, --help            show this help message and exit
  -c AUTO_COMMIT, --auto_commit AUTO_COMMIT
                        automatically commit access actions
  -p AUTO_PUSH, --auto_push AUTO_PUSH
                        automatically push committed access actions
  -d DEFER, --defer DEFER
                        defer access setting to a separate process
```