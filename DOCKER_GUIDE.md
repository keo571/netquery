# Docker Deployment Guide

This guide explains how to deploy the Netquery Text-to-SQL system using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB of available RAM
- Gemini API key

## Quick Start

1. **Initial Setup**
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/netquery.git
   cd netquery

   # Run initial setup (creates .env file and directories)
   make setup

   # Edit .env and add your GEMINI_API_KEY
   nano .env
   ```

2. **Build and Start Services**
   ```bash
   # Build Docker images
   make build

   # Start services
   make up

   # View logs
   make logs
   ```

3. **Verify Installation**
   ```bash
   # Check service health
   make health

   # Test MCP server
   make mcp-test
   ```

## Docker Architecture

### Services

1. **text-to-sql**: Main MCP server for Text-to-SQL operations
2. **postgres**: PostgreSQL database (production profile)
3. **redis**: Redis cache for query results (cache profile)
4. **dev-tools**: Development container with additional tools

### Volumes

- `./data`: Persistent database storage
- `./config`: Configuration files
- `./logs`: Application logs

### Networks

- `netquery-network`: Internal bridge network for service communication

## Usage Modes

### Development Mode

For local development with hot-reloading:

```bash
# Start development environment
make dev

# This opens a shell with all development tools installed
# Source code is mounted for live editing
```

### Production Mode

For production deployment with PostgreSQL:

```bash
# Start production services (includes PostgreSQL)
make prod

# Monitor services
docker-compose ps
docker-compose logs -f
```

### Testing Mode

Run tests in isolated container:

```bash
make test
```

## Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Required
GEMINI_API_KEY=your_key_here

# Database (choose one)
DATABASE_URL=sqlite:////app/data/infrastructure.db  # SQLite (default)
DATABASE_URL=postgresql://user:pass@postgres:5432/db  # PostgreSQL

# Optional
LOG_LEVEL=INFO
API_PORT=5001
MAX_RESULT_ROWS=1000
QUERY_TIMEOUT=30
```

### Custom Configuration

1. **Create custom config file**:
   ```yaml
   # config/config.yaml
   metadata:
     version: "1.0.0"
     environment: production
   
   llm:
     model_name: gemini-1.5-flash
     temperature: 0.1
     max_tokens: 2048
   
   safety:
     max_result_rows: 1000
     max_query_length: 10000
   ```

2. **Mount in docker-compose.yml**:
   ```yaml
   volumes:
     - ./config/config.yaml:/app/config/config.yaml:ro
   ```

## Database Management

### SQLite (Default)

```bash
# Access SQLite database
make db-shell

# Recreate sample data
make db-create
```

### PostgreSQL (Production)

```bash
# Start with PostgreSQL
docker-compose --profile production up -d

# Access PostgreSQL
docker-compose exec postgres psql -U netquery -d infrastructure

# Import existing data
docker-compose exec -T postgres psql -U netquery -d infrastructure < backup.sql
```

## MCP Server Operations

### Start MCP Server

```bash
# MCP server starts automatically with container
# Or manually start it:
make mcp-start
```

### Test MCP Server

```bash
# Run example client
make mcp-test

# Or use curl to test
docker-compose exec text-to-sql python -c "
from src.text_to_sql.mcp_client_example import test_mcp_server
import asyncio
asyncio.run(test_mcp_server())
"
```

### Integration with Claude Desktop

1. Get container's MCP endpoint:
   ```bash
   docker inspect netquery-text-to-sql | grep IPAddress
   ```

2. Configure Claude Desktop to connect to Docker container
   (Note: This requires additional network configuration)

## Monitoring and Debugging

### View Logs

```bash
# All services
make logs

# Specific service
docker-compose logs -f text-to-sql

# Last 100 lines
docker-compose logs --tail=100 text-to-sql
```

### Health Checks

```bash
# Check all services
docker-compose ps

# Detailed health check
make health

# Manual health check
docker-compose exec text-to-sql python -c "
from src.text_to_sql.tools.database_toolkit import db_toolkit
print('Database OK' if db_toolkit.test_connection() else 'Database FAILED')
"
```

### Debug Mode

```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart

# Open shell for debugging
make shell
```

## Performance Optimization

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  text-to-sql:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Caching with Redis

```bash
# Enable Redis cache
docker-compose --profile cache up -d

# Configure in .env
REDIS_URL=redis://redis:6379/0
ENABLE_CACHE=true
CACHE_TTL=3600
```

## Backup and Restore

### Backup

```bash
# Backup SQLite database
docker-compose exec text-to-sql sqlite3 /app/data/infrastructure.db .dump > backup.sql

# Backup PostgreSQL
docker-compose exec postgres pg_dump -U netquery infrastructure > backup.sql

# Backup entire data directory
tar -czf netquery-backup-$(date +%Y%m%d).tar.gz data/ config/
```

### Restore

```bash
# Restore SQLite
docker-compose exec -T text-to-sql sqlite3 /app/data/infrastructure.db < backup.sql

# Restore PostgreSQL
docker-compose exec -T postgres psql -U netquery infrastructure < backup.sql

# Restore data directory
tar -xzf netquery-backup-20240101.tar.gz
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs text-to-sql

# Rebuild image
make rebuild

# Check environment variables
docker-compose config
```

### Database Connection Issues

```bash
# Test database connection
make health

# Reset database
rm -rf data/infrastructure.db
make db-create
```

### Memory Issues

```bash
# Check memory usage
docker stats

# Increase Docker memory limit
# Docker Desktop > Settings > Resources > Memory
```

### Permission Issues

```bash
# Fix permissions
sudo chown -R 1000:1000 data/ logs/ config/

# Or run as root (not recommended)
docker-compose exec -u root text-to-sql /bin/bash
```

## Security Considerations

1. **Never commit `.env` file** with real API keys
2. **Use secrets management** in production:
   ```yaml
   services:
     text-to-sql:
       secrets:
         - gemini_api_key
   
   secrets:
     gemini_api_key:
       external: true
   ```

3. **Network isolation**: Services only communicate within Docker network
4. **Non-root user**: Containers run as non-root user (uid 1000)
5. **Read-only mounts**: Configuration files mounted as read-only

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build and push
        run: |
          docker build -t myregistry/netquery:${{ github.sha }} .
          docker push myregistry/netquery:${{ github.sha }}
      
      - name: Deploy
        run: |
          ssh server "cd /app && docker-compose pull && docker-compose up -d"
```

## Useful Commands

```bash
# Remove all containers and volumes
make clean

# Restart services
make restart

# Show running containers
make ps

# Format code
make format

# Run linting
make lint

# Complete rebuild
make rebuild
```

## Support

For issues or questions:
1. Check logs: `make logs`
2. Review this guide
3. Open an issue on GitHub