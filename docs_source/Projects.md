Projects keep a record of access and changes to access. Initialize a project with the init command:

```sh
manage-access init ./access_record
cd access_record
```

This will create the following initial files:

```
access_record/
  .git
  .gitignore
  access.csv
  config.json
  locations.json
  log.txt
  pending_access.csv
```

`access.csv` keeps a record of what should be current user access. It is a comma delimited file with these columns:

- `user`: Name of the user receiving access.
- `group`: Group under which the user is receiving access. This will default to the user themselves.
- `location`: Path to the directory the user is receiving access to.
- `permissions`: Type of access the user should have; `rx` by default.
- `date`: Date and time at which permission was set.

This is added to each time a user is granted access to a location, and is removed from when that access is revoked.

`pending_access.csv` is the same structure as `access.csv`. Users are added here if they cannot be found on the system.

`locations.json` keeps an association between names and full paths, for convenience. This is only used for initial translation,
such that stored references to locations are always the associated path, rather than the name.

`log.txt` keeps a log of events.
