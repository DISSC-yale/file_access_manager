# Changelog

## Version 0.1.1

### Bug Fixes

- Avoids removing non-existent users from access without a lock in place.

## Version 0.1.0

### Bug Fixes

- Various revocation fixes.
- Avoids possible overwrites from concurrent check pending processes.
- Fixes clearing of pending global removals.
- Accounts for masked permissions.
- Preserves deferred location paths.

### Improvements

- Improves current access detection.
- Avoids leaving working directory changed after init.
- Adds feedback about invalid location names.
- Cleans up any existing access for removed, non-existent users.

### Features

- Adds allowed directory mechanism.
