# GivTCP Quick Start Guide

Get GivTCP running on your Raspberry Pi in 5 minutes.

## Step 1: Build the Image (On Your Development Machine)

**Windows (PowerShell):**
```powershell
.\build.ps1
```

**Linux/Mac:**
```bash
chmod +x build.sh
./build.sh
```

This builds and pushes the image to `rpi-matthew.fritz.box:5000/givtcp:latest`

Build time: 10-20 minutes (first time)

## Step 2: Deploy on Raspberry Pi

SSH to your Raspberry Pi:
```bash
ssh pi@your-pi-ip
```

Create deployment directory:
```bash
mkdir -p ~/givtcp
cd ~/givtcp
```

Create `docker-compose.yml`:
```yaml
version: "3.9"

services:
  givtcp:
    image: rpi-matthew.fritz.box:5000/givtcp:latest
    container_name: givtcp
    ports:
      - "1883:1883"   # MQTT
      - "8098:8099"   # REST API
      - "3000:3000"   # Dashboard
    volumes:
      - ./config:/config
    restart: unless-stopped
    privileged: true
    environment:
      - TZ=Europe/London
      - INVERTOR_IP=192.168.1.100          # ← Change this
      - INVERTOR_NUM_BATTERIES=1           # ← Change this
      - MQTT_ADDRESS=127.0.0.1
      - MQTT_TOPIC=GivEnergy
      - HA_AUTO_D=True
      - LOG_LEVEL=Info
      - SELF_RUN_LOOP_TIMER=5
      # Feature flags (all false = legacy code)
      - USE_NEW_CACHE=false
      - USE_NEW_LOCKS=false
      - USE_NEW_SERVICES=false
```

## Step 3: Start Container

```bash
docker-compose pull
docker-compose up -d
```

## Step 4: Verify It's Working

Check logs:
```bash
docker-compose logs -f
```

Look for:
```
✓ Invertor connection successful
✓ MQTT broker started
✓ Redis started
```

Press `Ctrl+C` to exit logs.

## Step 5: Access Services

- **Web Dashboard**: http://your-pi-ip:3000
- **Configuration**: http://your-pi-ip:8098
- **REST API**: http://your-pi-ip:8098/readData

## Home Assistant Integration

GivTCP auto-discovers in Home Assistant:

1. Go to **Settings** → **Devices & Services**
2. Look for **MQTT** device with GivEnergy sensors
3. All sensors should appear automatically

If not showing:
1. Check MQTT integration is configured
2. Check `HA_AUTO_D=True` in environment
3. Restart Home Assistant

## Enable New Features (Optional)

The refactored code is available but disabled by default.

### Test in Stages

Edit `docker-compose.yml` and enable one flag at a time:

**Stage 1 - Cache Repository:**
```yaml
environment:
  - USE_NEW_CACHE=true
  - USE_NEW_LOCKS=false
  - USE_NEW_SERVICES=false
```

```bash
docker-compose up -d
docker-compose logs -f  # Monitor for 24 hours
```

**Stage 2 - Lock Manager:**
```yaml
environment:
  - USE_NEW_CACHE=true
  - USE_NEW_LOCKS=true
  - USE_NEW_SERVICES=false
```

```bash
docker-compose up -d
docker-compose logs -f  # Monitor for 24 hours
```

**Stage 3 - Service Layer (Full Refactoring):**
```yaml
environment:
  - USE_NEW_CACHE=true
  - USE_NEW_LOCKS=true
  - USE_NEW_SERVICES=true
```

```bash
docker-compose up -d
docker-compose logs -f  # Monitor for stability
```

### Instant Rollback

If issues arise:
```yaml
environment:
  - USE_NEW_SERVICES=false  # ← Just set to false
```

```bash
docker-compose up -d
```

## Common Issues

### Can't Connect to Inverter

Check:
- Inverter IP is correct
- Raspberry Pi can ping inverter: `ping 192.168.1.100`
- No firewall blocking

### MQTT Not Working

Check:
- MQTT broker is running: `docker-compose ps`
- MQTT topic is correct: `mosquitto_sub -h localhost -t 'GivEnergy/#' -v`

### Port Already in Use

Change ports in docker-compose.yml:
```yaml
ports:
  - "1884:1883"  # Changed from 1883
  - "8099:8099"  # REST API
  - "3001:3000"  # Changed from 3000
```

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart container
docker-compose restart

# Stop container
docker-compose stop

# Remove container
docker-compose down

# Update to latest version
docker-compose pull
docker-compose up -d

# Check container status
docker-compose ps

# Open shell in container
docker-compose exec givtcp /bin/sh
```

## Getting Help

- Check logs: `docker-compose logs`
- Check health: `curl http://localhost:6345/readData`
- GitHub Issues: https://github.com/britkat1980/giv_tcp/issues

## What's Next?

- Configure tariff settings
- Set up InfluxDB (optional)
- Enable PALM features (optional)
- Create Home Assistant automations

See `DOCKER_DEPLOYMENT.md` for full documentation.
