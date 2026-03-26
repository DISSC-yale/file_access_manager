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
  -m, --managers [MANAGERS ...]
                        manager users
  -r, --remote REMOTE   git remote
  -b, --branch BRANCH   git branch
```

### config

```sh
usage: manage-access config [-h] [-c AUTO_COMMIT] [-p AUTO_PUSH] [-d DEFER]

Configure an access manager project.

options:
  -h, --help            show this help message and exit
  -c, --auto_commit AUTO_COMMIT
                        automatically commit access actions
  -p, --auto_push AUTO_PUSH
                        automatically push committed access actions
  -d, --defer DEFER     defer access setting to a separate process
```