# GivTCP Docker Deployment Guide

Complete guide for deploying GivTCP as a Docker container on Raspberry Pi with custom registry.

## Prerequisites

- Raspberry Pi (2, 3, 4, or 5) running Raspberry Pi OS or similar
- Docker and Docker Compose installed
- Access to your custom Docker registry at `rpi-matthew.fritz.box:5000`
- GivEnergy inverter on your local network

## Quick Start

### 1. Build and Push Image

**On Windows (PowerShell):**
```powershell
.\build.ps1
# Or with version tag:
.\build.ps1 v2.5.0
```

**On Linux/Mac:**
```bash
chmod +x build.sh
./build.sh
# Or with version tag:
./build.sh v2.5.0
```

This will:
- Build multi-architecture image (ARM v7 and ARM64)
- Push to your registry: `rpi-matthew.fritz.box:5000/givtcp:latest`
- Take 10-20 minutes depending on your system

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and configure your inverter:
```bash
INVERTOR_IP=192.168.1.100        # Your inverter IP
INVERTOR_NUM_BATTERIES=1         # Number of batteries
```

### 3. Deploy on Raspberry Pi

```bash
# Pull latest image
docker-compose pull

# Start container
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access Services

- **Web Dashboard**: http://your-pi-ip:3000
- **REST API**: http://your-pi-ip:8098/readData
- **MQTT**: mqtt://your-pi-ip:1883
- **Configuration**: http://your-pi-ip:8098

## Feature Flags (Phase 1-5 Refactoring)

GivTCP includes new implementations that can be enabled via feature flags. All flags default to `false` for backward compatibility.

### Available Feature Flags

| Flag | Phase | Description | Status |
|------|-------|-------------|--------|
| `USE_NEW_CACHE` | 2 | Thread-safe cache repository | ✅ Ready |
| `USE_NEW_LOCKS` | 5 | ThreadLockManager (eliminates TOCTOU) | ✅ Ready |
| `USE_NEW_SERVICES` | 3 | Service layer extraction | ✅ Ready |

### Recommended Rollout Strategy

Enable features gradually to ensure stability:

#### Step 1: Enable Cache Repository
```yaml
environment:
  - USE_NEW_CACHE=true
  - USE_NEW_LOCKS=false
  - USE_NEW_SERVICES=false
```

Monitor for 24-48 hours. Check logs for errors.

#### Step 2: Enable Lock Manager
```yaml
environment:
  - USE_NEW_CACHE=true
  - USE_NEW_LOCKS=true
  - USE_NEW_SERVICES=false
```

Monitor for 24-48 hours. Verify no lock-related errors.

#### Step 3: Enable Service Layer
```yaml
environment:
  - USE_NEW_CACHE=true
  - USE_NEW_LOCKS=true
  - USE_NEW_SERVICES=true
```

Monitor for stability. This is the full refactored implementation.

### Instant Rollback

If issues arise, simply set the flag back to `false`:
```yaml
environment:
  - USE_NEW_SERVICES=false  # Instant rollback
```

Then restart:
```bash
docker-compose up -d
```

No code deployment needed - the container includes both implementations.

## Configuration

### Environment Variables

Full list available in `.env.example`. Key settings:

**Inverter:**
```bash
INVERTOR_IP=192.168.1.100
INVERTOR_NUM_BATTERIES=1
```

**MQTT:**
```bash
MQTT_ADDRESS=127.0.0.1
MQTT_TOPIC=GivEnergy
```

**Home Assistant:**
```bash
HA_AUTO_D=True
```

**Logging:**
```bash
LOG_LEVEL=Info                # Debug, Info, Warning, Error, Critical
PRINT_RAW=False
```

**Application:**
```bash
SELF_RUN_LOOP_TIMER=5         # Poll interval (seconds)
QUEUE_RETRIES=2
DATASMOOTHER=High             # Off, Low, Medium, High
```

### Volumes

- `./config:/config` - Configuration and cache storage (persists across restarts)

### Ports

- `1883` - MQTT broker
- `3000` - Web dashboard
- `6379` - Redis (optional external access)
- `8098` - REST API and configuration interface

## Home Assistant Integration

### Automatic Discovery

GivTCP automatically publishes MQTT discovery messages for Home Assistant when `HA_AUTO_D=True`.

### Manual Configuration

If using manual MQTT configuration:

```yaml
# configuration.yaml
mqtt:
  sensor:
    - name: "Solar Power"
      state_topic: "GivEnergy/Power/Power/PV_Power"
      unit_of_measurement: "W"
      device_class: power
```

## Monitoring and Logs

### View Logs
```bash
docker-compose logs -f givtcp
```

### Check Container Status
```bash
docker-compose ps
```

### Health Check
```bash
curl http://localhost:6345/readData
```

### Restart Container
```bash
docker-compose restart givtcp
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs givtcp
```

Common issues:
- Inverter IP incorrect
- Network connectivity
- Port conflicts

### No Data in Home Assistant

1. Check MQTT broker is running:
   ```bash
   docker-compose exec givtcp mosquitto_sub -t 'GivEnergy/#' -v
   ```

2. Verify `HA_AUTO_D=True` in environment

3. Check Home Assistant MQTT integration is configured

### Performance Issues

Increase poll interval:
```yaml
environment:
  - SELF_RUN_LOOP_TIMER=10  # Increase from 5 to 10 seconds
```

Reduce data smoothing:
```yaml
environment:
  - DATASMOOTHER=Low  # Change from High to Low
```

## Upgrading

### Pull New Version
```bash
docker-compose pull
docker-compose up -d
```

### Backup Configuration
```bash
cp -r ./config ./config.backup
```

### Rollback to Previous Version
```bash
docker-compose down
docker-compose up -d rpi-matthew.fritz.box:5000/givtcp:v2.4.0
```

## Building from Source

### Build for Local Testing
```bash
docker build -t givtcp:dev .
docker run -d --name givtcp-test givtcp:dev
```

### Build for Specific Architecture
```bash
docker buildx build --platform linux/arm64 -t givtcp:arm64 .
```

## Security Considerations

### MQTT Authentication

If exposing MQTT externally, enable authentication:
```yaml
environment:
  - MQTT_USERNAME=your_username
  - MQTT_PASSWORD=your_password
```

### Network Isolation

Consider using Docker networks:
```yaml
networks:
  givtcp_net:
    driver: bridge
```

### Registry Authentication

If your registry requires authentication:
```bash
docker login rpi-matthew.fritz.box:5000
```

## Support

- **Issues**: https://github.com/britkat1980/giv_tcp/issues
- **Documentation**: https://github.com/britkat1980/giv_tcp
- **Community**: Home Assistant forums

## License

See LICENSE file in repository.
