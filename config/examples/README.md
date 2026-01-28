# Configuration Examples

This directory contains example configuration files for different deployment environments of the SoulSense application.

## File Structure

```
config/examples/
├── .env.development      # Development environment variables
├── .env.testing          # Testing environment variables
├── .env.staging          # Staging environment variables
├── .env.production       # Production environment variables
├── config.development.json    # Development JSON config
├── config.testing.json        # Testing JSON config
├── config.staging.json        # Staging JSON config
└── config.production.json     # Production JSON config
```

## Usage

### Quick Setup

1. **Development**:
   ```bash
   cp .env.development ../../.env
   cp config.development.json ../../config.json
   ```

2. **Testing**:
   ```bash
   cp .env.testing ../../.env
   cp config.testing.json ../../config.json
   ```

3. **Staging**:
   ```bash
   cp .env.staging ../../.env
   cp config.staging.json ../../config.json
   ```

4. **Production**:
   ```bash
   cp .env.production ../../.env
   cp config.production.json ../../config.json
   ```

### Environment Variables (.env files)

The `.env` files contain environment variables used by:
- FastAPI backend (`backend/fastapi/app/config.py`)
- Docker Compose (`docker-compose.yml`)
- Main application (via `app/config.py`)

### JSON Configuration (config.json)

The `config.json` files are used by the main application (`app/config.py`) for:
- UI settings
- Feature toggles
- Database path configuration
- Experimental features

## Security Notes

⚠️ **Important**: Never commit actual `.env` files to version control!

- The example files contain placeholder values and insecure defaults
- For production, always use secure, randomly generated secrets
- Store production secrets in secure vaults (AWS Secrets Manager, Azure Key Vault, etc.)
- Rotate secrets regularly

## Environment Differences

| Environment | Database | Debug | Logging | Features |
|-------------|----------|-------|---------|----------|
| Development | SQLite   | On    | DEBUG   | All enabled |
| Testing     | SQLite   | On    | DEBUG   | All enabled |
| Staging     | PostgreSQL | Off | INFO    | Most enabled |
| Production  | PostgreSQL | Off | WARNING | Stable only |

## Customization

After copying the example files:

1. **Update secrets**: Replace placeholder passwords and keys
2. **Configure domains**: Update CORS origins and database hosts
3. **Set paths**: Adjust file paths for your environment
4. **Enable features**: Toggle experimental features as needed

## Validation

The application validates environment configuration on startup. Check the logs for any validation errors:

```bash
✅ Environment validation successful!
```

See `docs/architecture/config_examples.md` for detailed documentation.</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\config\examples\README.md