# nr.admin

This module provides cross-platform privilege elevation.

### `nr.admin.is_admin()`

Returns `True` if the process is running as a privileged user.

### `nr.admin.run_as_admin(command, cwd=None, environ=None): int`

Runs the specified *command* as a privileged user. The user will be
asked for permission by the operating system.
