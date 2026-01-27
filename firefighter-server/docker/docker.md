# Docker Setup Guide - Firefighter Server

Complete guide for managing Docker services (Qdrant, PostgreSQL, and Firefighter Server).

---

## Quick Start

### Install PostgreSQL Only (Since Qdrant is Already Running)

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs -f postgres

# Test PostgreSQL connection
docker exec -it firefighter-postgres psql -U firefighter_user -d firefighter
```

---

## Service Management Commands

### Start All Services

```bash
# Start all services (Qdrant + PostgreSQL + Server)
docker-compose up -d

# Start all services with logs visible
docker-compose up

# Start specific services
docker-compose up -d postgres qdrant
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop all services and remove volumes (⚠️ DELETES DATA)
docker-compose down -v

# Stop only PostgreSQL
docker-compose stop postgres

# Stop and remove only PostgreSQL container
docker-compose rm -f -s postgres
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart only PostgreSQL
docker-compose restart postgres

# Restart after code changes (rebuilds server)
docker-compose up -d --build server
```

### View Status & Logs

```bash
# Check status of all services
docker-compose ps

# View logs for all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for specific service
docker-compose logs -f postgres
docker-compose logs -f qdrant
docker-compose logs -f server

# View last 100 lines
docker-compose logs --tail=100 postgres
```

---

## PostgreSQL Configuration

### Connection Details

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Host** | `localhost` (or server IP) | From outside Docker |
| **Port** | `5432` | Default PostgreSQL port |
| **Database** | `firefighter` | Database name |
| **User** | `firefighter_user` | Database user |
| **Password** | `dev_password` | Default (set via .env) |

### Set Custom Password

Create/edit `.env` file in the same directory as `docker-compose.yml`:

```bash
# Create .env file
cat > .env << 'EOF'
POSTGRES_PASSWORD=your_secure_password_here
EOF

# Restart PostgreSQL to apply new password
docker-compose down postgres
docker-compose up -d postgres
```

### Access PostgreSQL Shell

```bash
# Interactive psql shell
docker exec -it firefighter-postgres psql -U firefighter_user -d firefighter

# Run single SQL command
docker exec -it firefighter-postgres psql -U firefighter_user -d firefighter -c "SELECT version();"

# Execute SQL file
docker exec -i firefighter-postgres psql -U firefighter_user -d firefighter < your_script.sql
```

### Common PostgreSQL Commands

Once inside `psql` shell:

```sql
-- List all databases
\l

-- List all tables
\dt

-- Describe table structure
\d sessions
\d activity_types

-- View all sessions
SELECT * FROM sessions LIMIT 10;

-- Count records
SELECT COUNT(*) FROM sessions;

-- Exit psql
\q
```

---

## Qdrant Configuration

### Connection Details

| Parameter | Value | Notes |
|-----------|-------|-------|
| **REST API** | `http://localhost:6333` | HTTP interface |
| **gRPC** | `localhost:6334` | gRPC interface |
| **Dashboard** | `http://localhost:6333/dashboard` | Web UI |

### Access Qdrant Dashboard

Open in browser:
```
http://localhost:6333/dashboard
```

### Qdrant CLI Commands

```bash
# View Qdrant logs
docker-compose logs -f qdrant

# Check Qdrant health
curl http://localhost:6333/health

# List collections
curl http://localhost:6333/collections

# View collection info
curl http://localhost:6333/collections/foot_windows
curl http://localhost:6333/collections/accel_windows
```

---

## Data Persistence

### Data Locations

All data is stored in the `./data` directory:

```
firefighter-server/
├── data/
│   ├── postgres/          # PostgreSQL data files
│   ├── qdrant/            # Qdrant vector storage
│   └── sessions/          # Session files (if any)
```

### Backup Data

```bash
# Backup PostgreSQL database
docker exec firefighter-postgres pg_dump -U firefighter_user firefighter > backup_$(date +%Y%m%d).sql

# Backup Qdrant data (just copy the directory)
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz data/qdrant/

# Backup everything
tar -czf full_backup_$(date +%Y%m%d).tar.gz data/
```

### Restore Data

```bash
# Restore PostgreSQL from backup
docker exec -i firefighter-postgres psql -U firefighter_user -d firefighter < backup_20250120.sql

# Restore Qdrant (stop service, replace data, restart)
docker-compose stop qdrant
rm -rf data/qdrant/*
tar -xzf qdrant_backup_20250120.tar.gz
docker-compose start qdrant
```

---

## Troubleshooting

### PostgreSQL Won't Start

**Check logs:**
```bash
docker-compose logs postgres
```

**Common issues:**

1. **Port 5432 already in use:**
   ```bash
   # Check what's using the port
   sudo lsof -i :5432

   # Stop local PostgreSQL service
   sudo systemctl stop postgresql
   # or on macOS:
   brew services stop postgresql
   ```

2. **Permission issues on data directory:**
   ```bash
   # Fix permissions
   sudo chown -R 999:999 data/postgres
   ```

3. **Corrupted data directory:**
   ```bash
   # Remove and recreate (⚠️ DELETES DATA)
   docker-compose down
   rm -rf data/postgres/*
   docker-compose up -d postgres
   ```

### Qdrant Won't Start

**Check logs:**
```bash
docker-compose logs qdrant
```

**Common issues:**

1. **Port 6333 already in use:**
   ```bash
   # Check what's using the port
   sudo lsof -i :6333

   # Kill the process or change port in docker-compose.yml
   ```

2. **Out of disk space:**
   ```bash
   # Check disk usage
   df -h

   # Clean up Docker resources
   docker system prune -a
   ```

### Server Won't Connect to Databases

**Verify services are healthy:**
```bash
docker-compose ps

# Should show "Up (healthy)" for postgres and qdrant
```

**Check network connectivity:**
```bash
# From server container, ping databases
docker exec firefighter-server ping -c 3 postgres
docker exec firefighter-server ping -c 3 qdrant
```

**Verify environment variables:**
```bash
# Check server container environment
docker exec firefighter-server env | grep -E 'POSTGRES|QDRANT'
```

---

## Production Deployment

### Security Recommendations

1. **Change default password:**
   ```bash
   # Set strong password in .env
   POSTGRES_PASSWORD=$(openssl rand -base64 32)
   ```

2. **Restrict network access:**
   ```yaml
   # In docker-compose.yml, remove port mappings for internal services
   # postgres:
   #   ports:
   #     - "5432:5432"  # REMOVE this line in production
   ```

3. **Enable SSL/TLS for PostgreSQL:**
   ```bash
   # Mount SSL certificates in docker-compose.yml
   volumes:
     - ./certs/server.crt:/var/lib/postgresql/server.crt
     - ./certs/server.key:/var/lib/postgresql/server.key
   ```

### Resource Limits

Add resource limits to docker-compose.yml:

```yaml
postgres:
  # ... existing config
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 2G
      reservations:
        memory: 512M
```

### Monitoring

```bash
# Monitor resource usage
docker stats firefighter-postgres firefighter-qdrant firefighter-server

# Monitor in real-time
watch -n 1 'docker stats --no-stream'
```

---

## Initial Setup (First Time Only)

### Step 1: Create Data Directories

```bash
# Create directories for persistent data
mkdir -p data/postgres data/qdrant data/sessions
```

### Step 2: Set PostgreSQL Password (Optional)

```bash
# Create .env file with custom password
echo "POSTGRES_PASSWORD=your_secure_password" > .env
```

### Step 3: Start PostgreSQL

```bash
# Start only PostgreSQL (since Qdrant is already running)
docker-compose up -d postgres

# Wait for health check
sleep 10

# Verify PostgreSQL is healthy
docker-compose ps postgres
```

### Step 4: Verify Database Initialization

```bash
# Connect to PostgreSQL
docker exec -it firefighter-postgres psql -U firefighter_user -d firefighter

# Check tables exist
\dt

# Should see: sessions, activity_types tables
```

### Step 5: Start All Services (If Needed)

```bash
# Start everything
docker-compose up -d

# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Daily Operations

### Morning Startup

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Monitor logs for any errors
docker-compose logs --tail=50
```

### Evening Shutdown

```bash
# Stop all services (data persists)
docker-compose down

# Or keep running (recommended for servers)
# Services will auto-restart on server reboot
```

### Check Service Health

```bash
# Quick health check
docker-compose ps

# Detailed status
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Test PostgreSQL connection
docker exec firefighter-postgres pg_isready -U firefighter_user

# Test Qdrant connection
curl -s http://localhost:6333/health | jq
```

---

## Useful Docker Commands

### Container Management

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Remove stopped containers
docker container prune

# View container resource usage
docker stats
```

### Image Management

```bash
# List images
docker images

# Pull latest images
docker-compose pull

# Remove unused images
docker image prune -a

# Build server image
docker-compose build server
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect firefighter-server_qdrant_storage

# Remove unused volumes (⚠️ DELETES DATA)
docker volume prune
```

### Network Management

```bash
# List networks
docker network ls

# Inspect network
docker network inspect firefighter-server_default

# View connected containers
docker network inspect firefighter-server_default --format '{{range .Containers}}{{.Name}} {{end}}'
```

---

## Migration from Local to Docker

If you were running PostgreSQL/Qdrant locally and want to migrate:

### PostgreSQL Migration

```bash
# 1. Dump local database
pg_dump -U your_user firefighter > local_dump.sql

# 2. Import to Docker PostgreSQL
docker exec -i firefighter-postgres psql -U firefighter_user -d firefighter < local_dump.sql

# 3. Verify import
docker exec -it firefighter-postgres psql -U firefighter_user -d firefighter -c "\dt"
```

### Qdrant Migration

```bash
# 1. Stop local Qdrant
sudo systemctl stop qdrant

# 2. Copy data to Docker volume
cp -r /var/lib/qdrant/storage/* data/qdrant/

# 3. Start Docker Qdrant
docker-compose up -d qdrant

# 4. Verify collections
curl http://localhost:6333/collections
```

---

## Environment Variables Reference

Create `.env` file with these variables:

```bash
# PostgreSQL Configuration
POSTGRES_PASSWORD=your_secure_password_here

# Optional: Override other settings
# POSTGRES_DB=firefighter
# POSTGRES_USER=firefighter_user

# Server Configuration (if needed)
# SERVER_HOST=0.0.0.0
# SERVER_PORT=4100
# DEBUG=false
```

---

## Quick Reference Card

```bash
# START POSTGRESQL ONLY
docker-compose up -d postgres

# STOP POSTGRESQL
docker-compose stop postgres

# VIEW LOGS
docker-compose logs -f postgres

# ACCESS DATABASE
docker exec -it firefighter-postgres psql -U firefighter_user -d firefighter

# BACKUP DATABASE
docker exec firefighter-postgres pg_dump -U firefighter_user firefighter > backup.sql

# RESTORE DATABASE
docker exec -i firefighter-postgres psql -U firefighter_user -d firefighter < backup.sql

# CHECK HEALTH
docker-compose ps
curl http://localhost:6333/health
docker exec firefighter-postgres pg_isready -U firefighter_user

# RESTART EVERYTHING
docker-compose restart

# CLEAN RESTART (⚠️ REMOVES CONTAINERS)
docker-compose down && docker-compose up -d
```

---

## Support

### Check Docker Version

```bash
docker --version
docker-compose --version
```

### System Requirements

- Docker: 20.10+
- Docker Compose: 2.0+
- Disk Space: 5GB+ recommended
- RAM: 4GB+ recommended

### Official Documentation

- [Docker Compose](https://docs.docker.com/compose/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Qdrant Docker](https://qdrant.tech/documentation/quick-start/)

---

## Notes

- All data persists in the `./data` directory even after containers are removed
- PostgreSQL password defaults to `dev_password` (change in `.env` for production)
- Services auto-restart unless explicitly stopped
- Health checks ensure services are ready before dependencies start
- Use `docker-compose down -v` ONLY if you want to delete all data permanently

---

**Last Updated**: 2025-01-20
**Maintainer**: Firefighter Sensor Project Team
