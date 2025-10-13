# Advanced Configuration Guide

This document provides detailed configuration instructions for advanced ft_wheel deployment scenarios, including user management, content configuration, and system administration.

### Creating Superusers

Superusers are created through the `superusers.json` configuration file located at `backend/django/data/superusers.json`.

#### Configuration Format

```json
{
  "superusers": {
    "username1": {
      "intra_id": 123456,
      "testmode": false,
      "role": "admin"
    },
    "username2": {
      "intra_id": 789012,
      "testmode": true,
      "role": "moderator"
    }
  }
}
```

To get informations about roles and testmode, see [ADMINISTRATION](./ADMINISTRATION.md).

**Tips to find your intra_id:**

- On "https://profile.intra.42.fr/" (v2) inspect the page source (Ctrl+U) and search (Ctrl+F) for `"id":` to find your numeric user ID.

#### Configuration Parameters

- **login**: The 42 intranet username (used as the key)
- **intra_id**: The numeric user ID from the 42 API
- **testmode**: Boolean flag enabling test mode features
  - `true`: Bypasses spin cooldowns and ticket consumption
  - `false`: Normal operation with standard restrictions
- **role**: User privilege level
  - `"user"`: Standard user permissions
  - `"moderator"`: Administrative permissions without wheel management
  - `"admin"`: Full administrative access

#### Test Mode Features

When `testmode` is enabled for a user:

- Spin cooldowns are bypassed
- Ticket consumption is skipped for ticket-only wheels
- User can spin indefinitely without restrictions
- Useful for demonstration and testing purposes

#### Applying Superuser Configuration

The superuser configuration is automatically processed during container startup. To manually trigger the creation process:

```bash
docker exec -it ft_wheel-backend-1 python create_superusers.py
```

## Emergency Database Access

In case of lost administrative permissions, direct database access can restore admin privileges.

### Accessing the Database

1. Connect to the PostgreSQL container:

   ```bash
   docker exec -it ft_wheel-postgres-1 sh
   ```
2. Access the PostgreSQL shell:

   ```bash
   psql -U postgres -d your_database_name
   ```
3. Query current user roles:

   ```sql
   SELECT id, login, role FROM users_account;
   ```
4. Restore admin privileges:

   ```sql
   UPDATE users_account SET role='admin' WHERE login='your_username';
   ```
5. Verify the change:

   ```sql
   SELECT id, login, role FROM users_account WHERE login='your_username';
   ```
6. Exit the database:

   ```sql
   \q
   ```

### Database Table Structure

Key tables for user management:

- `users_account`: Main user table containing roles and permissions
- `wheel_ticket`: Spin tickets granted to users
- `wheel_history`: Complete spin history and results
- `administration_sitesettings`: System-wide configuration

## Patch Notes System

The patch notes system provides version tracking and change communication to users.

### Configuration File

Patch notes are managed through `backend/django/data/patch_notes.json`:

```json
{
  "current_version": "1.0.0",
  "versions": {
    "1.0.0": {
      "title": "Initial Release",
      "date": "2025-07-11",
      "notes": [
        "Initial release of ft_wheel.",
        "Basic wheel spinning functionality.",
        "User authentication via 42 OAuth.",
        "Administrative control panel."
      ]
    },
    "1.1.0": {
      "title": "Feature Update",
      "date": "2025-08-15",
      "notes": [
        "Added ticket system for premium wheels.",
        "Improved history tracking.",
        "Enhanced administrative controls.",
        "Performance optimizations."
      ]
    }
  }
}
```

### Configuration Structure

- **current_version**: The active version displayed to users
- **versions**: Object containing version-specific information
  - **title**: Display name for the version
  - **date**: Release date in YYYY-MM-DD format
  - **notes**: Array of change descriptions

### Updating Patch Notes

1. Edit the `patch_notes.json` file to add new version entries
2. Update the `current_version` field to the latest version
3. Restart the application or trigger a configuration reload

The patch notes are accessible to users through the FAQ section and are automatically displayed when version changes are detected.

## Wheel Configuration

Wheel configurations define the available jackpots, their probabilities, and associated rewards.

### Configuration Location

Wheel configurations are stored in `backend/django/data/wheel_configs/` as individual JSON files.

### Configuration Format

Each wheel configuration file follows this structure:

```json
{
  "sequence": [
    {
      "label": "Jackpot Name",
      "color": "#1be4e4",
      "message": "Message displayed to user",
      "function": "builtins.default",
      "args": {
        "parameter": "value"
      }
    },
    {
      "label": "Another Jackpot",
      "color": "#ff5733",
      "message": "Congratulations! You won something else.",
      "function": "builtins.coa_points",
      "args": {
        "amount": 10,
        "reason": "Won from the wheel"
      }
    }
  ],
  "url": "wheel-slug",
  "title": "Display Name",
  "slug": "wheel-slug",
  "ticket_only": false
}
```

### Configuration Parameters

#### Wheel-Level Settings

- **sequence**: Array of jackpot definitions (sectors on the wheel)
- **url**: URL-friendly identifier for the wheel
- **title**: Human-readable name displayed in the interface
- **slug**: Internal identifier matching the filename
- **ticket_only**: Boolean flag requiring tickets for spinning
  - `true`: Users must have valid tickets to spin
  - `false`: Standard cooldown-based access

#### Jackpot-Level Settings

- **label**: Text displayed on the wheel sector
- **color**: Hexadecimal color code for the sector
- **message**: Success message shown to the user
- **function**: Reward function to execute
- **args**: Function-specific parameters

### Creating New Wheels At Initial Setup

1. Create a new JSON file in `wheel_configs/` directory:

```bash
   cp wheel_configs/jackpots_standard.json wheel_configs/jackpots_custom.json
```

2. Edit the configuration with your desired settings
3. Update the wheel metadata:

   - Change `slug` and `url` to match filename
   - Update `title` for display purposes
   - Configure `ticket_only` as needed
4. Restart the application to load the new wheel


**For more details on reward functions, refer to the [REWARDS_OPTIONS](./REWARDS_OPTIONS.md) documentation.**

**For more details on wheel administration, refer to the [ADMINISTRATION](./ADMINISTRATION.md) documentation.**


## System Configuration

### Site Settings

Global system settings are managed through the database and accessible via the Control Panel:

- **Maintenance Mode**: Temporarily restrict access to administrators
- **Jackpot Cooldown**: Default time between spins (1-168 hours)
- **Announcement Message**: Homepage marquee text

### Maintenance Mode

When enabled, maintenance mode:

- Displays a maintenance page to regular users
- Allows administrators and moderators to access the system
- Useful for deployments and system updates

### Ticket System

The ticket system provides fine-grained access control:

- **Grant Tickets**: Administrators can grant spin tickets to specific users
- **Ticket-Only Wheels**: Wheels requiring valid tickets for access
- **Ticket Management**: View, filter, and delete tickets through the Control Panel

### Logging and Monitoring

The system maintains comprehensive logs:

- **Admin Activity**: All administrative actions are logged
- **Spin History**: Complete record of all wheel spins and results
- **Error Tracking**: System errors and exceptions
- **API Requests**: External API interactions

Logs are stored in the `saved-logs` Docker volume and accessible through the container file system.


## Security Considerations

### Access Control

- Role-based permissions prevent privilege escalation
- CSRF protection on all administrative endpoints
- OAuth state validation for authentication flows
- Session management with secure cookies

### Data Protection

- Database credentials stored in Docker secrets
- Environment-specific configuration through `.env` files
- Audit trails for all administrative actions
- Input validation and sanitization

### Operational Security

- Regular backup of configuration files and database
- Version control for wheel configurations
- Monitoring of administrative access patterns
- Secure storage of 42 API credentials
-

## Troubleshooting

### Common Issues

1. **Superuser Creation Fails**

   - Verify `superusers.json` syntax
   - Check `intra_id` accuracy
   - Ensure user exists in 42 system
2. **Wheel Configuration Errors**

   - Validate JSON syntax
   - Verify reward function names
   - Check parameter requirements
3. **Permission Denied Errors**

   - Confirm user role assignments
   - Check middleware configuration
   - Verify database permissions

### Database Backup and Recovery

Regular backups ensure data persistence:

```bash
# Create backup
make snapshot

# List available backups
make list-snapshots

# Restore from backup
make restore

# Restore specific backup
make restore-from FILE=backup_filename.tar.gz
```

For additional deployment and configuration guidance, refer to the [BASIC_INSTALLATION](./BASIC_INSTALLATION.md) guide.

## Next Steps

For Administration options, refer to [ADMINISTRATION](./ADMINISTRATION.md).
