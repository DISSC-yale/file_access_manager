# Changelog

## Version 0.1.0

### Bug Fixes

- Various revokation fixes.
- Avoids possible overwrites from concurrent check pending processes.
- Fixes clearing of pending global removals.
- Accounts for masked permissions.
- Preserves defered location paths.

### Improvements

- Improves current access detection.
- Avoids leaving working directory changed after init.
- Adds feedback about invalid location names.
- Cleans up any existing access for removed, non-existant users.

### Features

- Adds allowed directory mechanism.
