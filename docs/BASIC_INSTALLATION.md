# Basic Installation Guide

This document provides step-by-step instructions for setting up and running ft_wheel.

## Prerequisites

Before beginning the installation, ensure you have the following:

- Docker and Docker Compose installed
- Access to 42 API credentials with appropriate permissions
- Basic knowledge of command line operations

## Configuration

### Environment Setup

1. Copy the environment template to create your configuration file:

   ```bash
   cp .env-template .env
   ```
2. Edit the `.env` file with your specific values:

   ```bash
   vi .env
   ```

### Required Configuration Variables

#### OAuth Credentials

Configure your 42 API credentials in the `.env` file:

```env
OAUTH_UID=your_oauth_uid
OAUTH_SECRET=your_oauth_secret
OAUTH_REDIRECT_URI=your_oauth_redirect_uri
```

**Note:** The `OAUTH_REDIRECT_URI` endpoint should be `/login/oauth/callback`.

**Important:** Your 42 API credentials must have appropriate permissions. For example, wallet jackpots require `Transaction Manager` rights. Refer to [REWARDS_OPTIONS](./REWARDS_OPTIONS.md) for detailed permission requirements.

#### Security Settings

Generate secure random strings for the following fields (recommended: 16-32 bytes base64 encoded):

```env
DJANGO_SECRET=1cpBPJ18yrPqFSiEM2i+WQ==
POSTGRES_PASSWORD=TX8G0qx11fW3aCSugpLqRQ==
```

#### Application Settings

- **HOSTNAME**: The domain or IP address where ft_wheel will be accessible (without HTTP/HTTPS protocol)

  - Example: `ft_wheel.mydomain.org` or `localhost:8000`
- **HTTPS** (True/False): Set to `True` if using a reverse proxy with SSL termination. The application itself does not handle HTTPS directly.
- **DEBUG** (True/False): Set to `False` for production environments. Use `True` only during development when frontend log access is needed.
- **ASK_CONSENT** (True/False): When set to `True`, new users will see a consent page on first login, warning about potential consequences such as TIG assignments.

## Deployment

### Starting the Application

Once your `.env` file is properly configured, start the application with:

```bash
make up
```

### Available Make Commands

The project includes a comprehensive Makefile with the following commands:

#### Docker Management

- `make up` - Start the project (detached mode)
- `make down` - Stop the project
- `make logs` - Display application logs
- `make re` - Perform full restart with cleanup (includes automatic snapshot backup)

#### Snapshot Management

- `make snapshot` - Create snapshots of all Docker volumes
- `make list-snapshots` - List all available snapshots
- `make verify-snapshots` - Verify integrity of existing snapshots
- `make restore` - Restore from the most recent snapshots
- `make restore-from FILE=filename.tar.gz` - Restore from a specific snapshot file

#### Cleanup Operations

- `make clean` - Remove dangling Docker images
- `make clean-snapshots` - Retain only the 5 most recent snapshots per volume
- `make fclean` - Perform comprehensive cleanup with automatic backup

## System Architecture

### Data Persistence

The application uses three Docker volumes for data persistence:

1. **postgres-data**

   - Contains all PostgreSQL databases including users, history, and application data
   - Mount point: `/var/lib/postgresql/data`
2. **saved-logs**

   - Stores application logs including jackpot logs, API request logs, and admin activity logs
   - Mount point: `/var/log/ft_wheel`
3. **wheel-configs**

   - Contains wheel configuration files and related data
   - Mount point: `/backend/django/data/wheel_configs`

### Snapshot System

The Makefile includes an automated backup system that creates snapshots before destructive operations. Snapshots are stored in the `./snapshots` directory and can be used to restore the application to a previous state.

The snapshot system automatically:

- Creates backups before volume resets
- Maintains version history
- Provides easy restoration options
- Includes integrity verification

### Security Management

The application uses Docker secrets for secure credential management:

1. The `make up` command automatically executes `make create-secrets`
2. The `docker_secrets.sh` script parses the `.env` file
3. Individual secret files are created in `./secrets/` directory
4. Secrets are securely mounted into containers via `docker-compose.yml`

### Network Configuration

The application uses a single Docker network named `pg-network` to facilitate communication between the backend and PostgreSQL database.

**Reverse Proxy Setup:** If you plan to use a reverse proxy, the backend application is accessible on port `8000`.

## Next Steps

For advanced configuration options, initialization procedures, and detailed customization instructions, please refer to [ADVANCED_CONFIGURATION](./ADVANCED_CONFIGURATION.md).
