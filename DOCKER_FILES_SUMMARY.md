# Docker Deployment Files Summary

Complete overview of Docker deployment files for GivTCP with Phase 1-5 refactoring support.

## Files Created

### Build and Deployment

| File | Purpose | Usage |
|------|---------|-------|
| `Dockerfile` | Multi-stage build for ARM architectures | Updated with feature flags |
| `docker-compose.yml` | Container orchestration | Configured for custom registry |
| `build.sh` | Linux/Mac build script | `./build.sh [version]` |
| `build.ps1` | Windows PowerShell build script | `.\build.ps1 [version]` |
| `Makefile` | Convenience commands | `make help` |

### Configuration

| File | Purpose | Usage |
|------|---------|-------|
| `.env.example` | Environment variable template | Copy to `.env` and customize |
| `.dockerignore` | Build optimization | Excludes unnecessary files |

### Documentation

| File | Purpose | Audience |
|------|---------|----------|
| `QUICKSTART.md` | 5-minute deployment guide | End users |
| `DOCKER_DEPLOYMENT.md` | Complete deployment guide | DevOps/Admins |
| `DOCKER_FILES_SUMMARY.md` | This file | Developers |

## Architecture

### Registry Configuration
- **Registry**: `rpi-matthew.fritz.box:5000`
- **Image**: `givtcp`
- **Tags**: `latest`, version tags (e.g., `v2.5.0`)

### Multi-Architecture Support
- **linux/arm/v7**: Raspberry Pi 2/3
- **linux/arm64**: Raspberry Pi 4/5

### Container Services
```
┌─────────────────────────────────────┐
│          GivTCP Container           │
├─────────────────────────────────────┤
│  • Python Application               │
│  • Redis Server                     │
│  • MQTT Broker (Mosquitto)          │
│  • RQ Workers                       │
│  • REST API (Gunicorn)              │
│  • Web Dashboard (Nginx)            │
└─────────────────────────────────────┘
```

## Feature Flags

All Phase 1-5 refactoring implementations are included but disabled by default:

```yaml
environment:
  # Phase 2: Thread-safe cache repository
  - USE_NEW_CACHE=false

  # Phase 5: ThreadLockManager (eliminates TOCTOU)
  - USE_NEW_LOCKS=false

  # Phase 3: Service layer extraction
  - USE_NEW_SERVICES=false
```

**Benefits:**
- Instant rollback capability
- No code deployment for flag changes
- Gradual feature adoption
- A/B testing in production

## Build Process

### Build Flow
```
1. Multi-stage Docker build
   ├── Stage 1: Vue.js frontend (node:current-alpine)
   │   └── npm install && npm run build
   └── Stage 2: Python backend (python:alpine3.19)
       ├── Install system dependencies
       ├── Install Python packages
       ├── Copy application code
       └── Copy Vue.js dist from Stage 1

2. Docker Buildx
   ├── Build for linux/arm/v7
   └── Build for linux/arm64

3. Push to Registry
   └── rpi-matthew.fritz.box:5000/givtcp:latest
```

### Build Commands

**Quick Build (Default):**
```bash
# Windows
.\build.ps1

# Linux/Mac
./build.sh
```

**Version Tagged Build:**
```bash
# Windows
.\build.ps1 v2.5.0

# Linux/Mac
./build.sh v2.5.0
```

**Using Make:**
```bash
make build    # Build locally
make push     # Build and push to registry
```

## Deployment Scenarios

### Scenario 1: First Time Deployment

```bash
# 1. Build image
./build.sh

# 2. On Raspberry Pi
cd ~/givtcp
cp .env.example .env
nano .env  # Edit INVERTOR_IP

# 3. Deploy
docker-compose up -d

# 4. Monitor
docker-compose logs -f
```

### Scenario 2: Upgrade Existing Installation

```bash
# On Raspberry Pi
cd ~/givtcp

# Pull latest
docker-compose pull

# Restart
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs --tail=50
```

### Scenario 3: Enable New Features

```bash
# Edit docker-compose.yml
nano docker-compose.yml

# Change:
# - USE_NEW_CACHE=true

# Apply changes
docker-compose up -d

# Monitor for 24 hours
docker-compose logs -f
```

### Scenario 4: Rollback

```bash
# Option 1: Feature flag rollback (instant)
nano docker-compose.yml  # Set flag to false
docker-compose up -d

# Option 2: Version rollback
docker-compose down
docker-compose up -d rpi-matthew.fritz.box:5000/givtcp:v2.4.0
```

## Environment Variables

### Required
- `INVERTOR_IP` - Inverter IP address
- `INVERTOR_NUM_BATTERIES` - Number of batteries (0-3)

### Optional (with defaults)
- `TZ` - Timezone (Europe/London)
- `MQTT_ADDRESS` - MQTT broker (127.0.0.1)
- `LOG_LEVEL` - Logging level (Info)
- `SELF_RUN_LOOP_TIMER` - Poll interval (5s)

### Feature Flags
- `USE_NEW_CACHE` - Enable cache repository (false)
- `USE_NEW_LOCKS` - Enable lock manager (false)
- `USE_NEW_SERVICES` - Enable service layer (false)

Full list in `.env.example`

## Volumes

### Persistent Data
```yaml
volumes:
  - ./config:/config  # Configuration and cache
```

**Contents:**
- `settings.json` - GivTCP configuration
- `*.pkl` - Cache files (if legacy mode)
- Log files
- Certificate files (if HTTPS)

## Ports

| Port | Service | Protocol |
|------|---------|----------|
| 1883 | MQTT Broker | TCP |
| 3000 | Web Dashboard | HTTP |
| 6379 | Redis | TCP |
| 8098 | REST API + Config | HTTPS |
| 8099 | REST API (internal) | HTTP |

## Health Checks

Container includes health check:
```dockerfile
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:6345/readData || exit 1
```

**Manual Health Check:**
```bash
curl http://localhost:6345/readData
```

## Security

### Image Security
- Based on Alpine Linux (minimal attack surface)
- Regular updates via base image
- No root user for application processes

### Network Security
- Use Docker networks for isolation
- Restrict external port exposure
- Enable MQTT authentication if exposed

### Registry Security
```bash
# Login to private registry
docker login rpi-matthew.fritz.box:5000

# Use HTTPS for registry (recommended)
```

## Monitoring

### Container Logs
```bash
docker-compose logs -f givtcp
```

### Application Metrics
- REST API: http://localhost:8098/readData
- MQTT: Subscribe to `GivEnergy/#`
- Logs: Container stdout/stderr

### Resource Usage
```bash
docker stats givtcp
```

## Backup and Restore

### Backup Configuration
```bash
make backup
# Or manually:
tar -czf givtcp-backup-$(date +%Y%m%d).tar.gz config/
```

### Restore Configuration
```bash
make restore BACKUP_FILE=givtcp-backup-20240113.tar.gz
# Or manually:
tar -xzf givtcp-backup-20240113.tar.gz
```

## Troubleshooting

### Build Issues

**Multi-architecture build fails:**
```bash
# Check Docker Buildx
docker buildx ls

# Create new builder
docker buildx create --name mybuilder --use
docker buildx inspect --bootstrap
```

**Registry connection fails:**
```bash
# Test registry connectivity
ping rpi-matthew.fritz.box

# Check registry is accessible
curl http://rpi-matthew.fritz.box:5000/v2/_catalog
```

### Deployment Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs givtcp

# Check resource usage
docker stats

# Check port conflicts
netstat -tulpn | grep -E '(1883|3000|8098)'
```

**No data in Home Assistant:**
```bash
# Verify MQTT broker
docker-compose exec givtcp mosquitto_sub -t 'GivEnergy/#' -v

# Check MQTT config
docker-compose exec givtcp env | grep MQTT

# Verify Home Assistant can reach MQTT
# In Home Assistant: Developer Tools → MQTT → Listen to GivEnergy/#
```

### Performance Issues

**Slow response:**
- Increase `SELF_RUN_LOOP_TIMER`
- Reduce `DATASMOOTHER` level
- Check network latency to inverter

**High CPU usage:**
- Check logs for errors/retries
- Verify inverter connectivity
- Consider enabling `USE_NEW_LOCKS` and `USE_NEW_SERVICES`

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Build and Push
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push
        run: ./build.sh ${{ github.ref_name }}
```

### Automated Updates
Use Watchtower for automatic updates:
```yaml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_INCLUDE_RESTARTING=true
    command: givtcp
```

## Development Workflow

### Local Development
```bash
# Install dependencies
make dev-setup

# Run locally (without Docker)
make dev-run

# Run tests
make test

# Format code
make format
```

### Build and Test
```bash
# Build locally
make build

# Run with all features enabled
make test-all

# Check health
make health

# View logs
make logs
```

### Release Process
```bash
# Tag version
make tag VERSION=v2.5.0

# Build and push
make push VERSION=v2.5.0

# Deploy to production
ssh pi@raspberry-pi
cd ~/givtcp
docker-compose pull
docker-compose up -d
```

## References

- **Documentation**: `DOCKER_DEPLOYMENT.md`
- **Quick Start**: `QUICKSTART.md`
- **Environment Config**: `.env.example`
- **Build Scripts**: `build.sh`, `build.ps1`
- **Compose File**: `docker-compose.yml`

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- Review documentation in this directory
- GitHub Issues: https://github.com/britkat1980/giv_tcp/issues
