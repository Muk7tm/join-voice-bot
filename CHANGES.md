# Changes

## Latest Update

### Bring Button Role Access
- Added role-based access for the `سحب` button.
- `سحب` is now usable by:
  - Administrators, and
  - Roles explicitly allowed by administrators.

### New Admin Commands
- Added `/addbringrole <role>` to allow a role to use `سحب`.
- Added `/removebringrole <role>` to remove access for a role.
- Added `/listbringroles` to show allowed roles.
- Added `/clearbringroles` to clear all extra role access.

### Persistence
- Added `bring_roles.json` to persist allowed bring roles per guild.

### Permission Logic
- Updated bring-button permission checks to use the new role policy.
- Kept admin access always enabled regardless of configured role list.

### Embed/UX Text
- Updated permission-related embed text to match role-based behavior.

### Documentation
- Replaced outdated docs in `README.md`.
- Updated setup, features, commands, and data file descriptions to match current behavior.
