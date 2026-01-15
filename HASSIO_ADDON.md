# GivTCP Home Assistant Add-on Guide

Complete guide for installing and configuring GivTCP as a Home Assistant OS add-on.

## Overview

GivTCP is now available as a Home Assistant add-on, providing seamless integration with your Home Assistant installation. This eliminates the need for manual Docker configuration and provides a user-friendly configuration interface.

## Features

- **Native Home Assistant Integration**: Automatic MQTT discovery
- **Easy Configuration**: Configure via Home Assistant UI
- **Multi-Architecture Support**: Works on all Raspberry Pi models (2, 3, 4, 5)
- **Automatic Updates**: Update via Home Assistant supervisor
- **Feature Flags**: Enable Phase 1-5 refactoring improvements via UI

## Installation Methods

### Method 1: Add Custom Repository (Recommended)

1. **Add Repository** to Home Assistant:
   - Navigate to **Settings** → **Add-ons** → **Add-on Store**
   - Click the **⋮** (three dots) in the top right
   - Select **Repositories**
   - Add: `https://github.com/andrewbuckingham/giv_tcp`
   - Click **Add** then **Close**

2. **Install GivTCP**:
   - Refresh the Add-on Store page
   - Find **GivTCP** in the list
   - Click on it and press **Install**
   - Wait 10-20 minutes for installation to complete

3. **Configure** (see Configuration section below)

4. **Start** the add-on and check logs

### Method 2: Manual Installation (Advanced)

1. **Clone Repository** to your Home Assistant:
   ```bash
   cd /addons
   git clone https://github.com/andrewbuckingham/giv_tcp
   ```

2. **Reload Add-ons**:
   - Go to **Settings** → **Add-ons**
   - Click **⋮** → **Check for updates**

3. **Install** GivTCP from the local add-on list

## Configuration

### Required Settings

Navigate to the add-on **Configuration** tab:

```yaml
invertor_ip: 192.168.1.100        # Your inverter IP address
num_batteries: 1                   # Number of batteries (0-3)
mqtt_address: core-mosquitto       # Use Home Assistant's MQTT broker
mqtt_topic: GivEnergy             # MQTT topic prefix
ha_auto_discovery: true           # Enable auto-discovery
log_level: Info                   # Debug, Info, Warning, Error, Critical
self_run_loop_timer: 5            # Poll interval in seconds
```

### MQTT Configuration

#### Using Home Assistant's Built-in MQTT Broker (Recommended)

1. Install **Mosquitto broker** add-on if not already installed
2. In GivTCP configuration, set:
   ```yaml
   mqtt_address: core-mosquitto
   mqtt_username: ""              # Leave empty
   mqtt_password: ""              # Leave empty
   ```

#### Using External MQTT Broker

If using an external MQTT broker:
```yaml
mqtt_address: 192.168.1.50
mqtt_username: your_username
mqtt_password: your_password
```

### Optional Settings

```yaml
# Logging
print_raw: false                  # Print raw register data

# Application
queue_retries: 2                  # Number of queue retries
datasmoother: High                # Off, Low, Medium, High

# PALM (Power Arbitrage Load Management)
palm_winter: false
palm_shoulder: false
palm_min_soc_target: 75
palm_max_soc_target: 100
palm_batt_reserve: 4
palm_batt_utilisation: 0.85

# InfluxDB (Optional)
influx_output: false
influx_url: http://influxdb:8086
influx_token: your_token
influx_bucket: homeassistant
influx_org: home
```

### Feature Flags (Phase 1-5 Refactoring)

Enable new implementations via the configuration UI:

```yaml
feature_flags:
  use_new_cache: false      # Phase 2: Thread-safe cache repository
  use_new_locks: false      # Phase 5: ThreadLockManager (eliminates TOCTOU)
  use_new_services: false   # Phase 3: Service layer extraction
```

#### Recommended Rollout

1. **Initial Installation**: All flags `false` (most stable)
2. **After 24 hours**: Set `use_new_cache: true`
3. **After 24 hours**: Set `use_new_locks: true`
4. **After 24 hours**: Set `use_new_services: true`

**Benefits:**
- Phase 2: Eliminates pickle file race conditions
- Phase 5: Eliminates TOCTOU vulnerabilities
- Phase 3: Better code organization and testability

**Rollback:**
- Simply set flags back to `false` and restart the add-on

## Network Configuration

### Ports

The add-on exposes these ports:

| Port | Service | Host Port | Description |
|------|---------|-----------|-------------|
| 1883 | MQTT | 1883 | MQTT broker for Home Assistant |
| 3000 | Dashboard | 3000 | Web dashboard |
| 8099 | REST API | 6345 | REST API and configuration |

To access from outside Home Assistant:
- Dashboard: `http://homeassistant.local:3000`
- REST API: `http://homeassistant.local:6345`

### Network Mode

The add-on runs in bridge mode by default. If you need host network mode, edit the configuration:

**Not recommended** unless you have connectivity issues.

## Usage

### Starting the Add-on

1. Navigate to **Settings** → **Add-ons** → **GivTCP**
2. Click **Start**
3. Check the **Log** tab for startup messages
4. Look for: `Invertor connection successful`

### Viewing Logs

Real-time logs are available in the **Log** tab of the add-on page.

For detailed debugging:
1. Set `log_level: Debug` in configuration
2. Restart the add-on
3. View logs

### Accessing Services

#### Web Dashboard
- From Home Assistant: Click **Open Web UI** button on add-on page
- Direct: `http://homeassistant.local:3000`

#### REST API
- `http://homeassistant.local:6345/readData` - Get current data
- `http://homeassistant.local:6345` - Configuration interface

## Home Assistant Integration

### Automatic Discovery

With `ha_auto_discovery: true`, GivTCP automatically creates entities in Home Assistant:

**Sensors:**
- `sensor.givtcp_pv_power`
- `sensor.givtcp_load_power`
- `sensor.givtcp_grid_power`
- `sensor.givtcp_battery_soc`
- `sensor.givtcp_battery_power`
- And many more...

**Controls:**
- `switch.givtcp_enable_charge`
- `switch.givtcp_enable_discharge`
- `number.givtcp_target_soc`
- And more...

### Finding Entities

1. Go to **Settings** → **Devices & Services**
2. Look for **MQTT** integration
3. Find devices prefixed with **GivEnergy** or **GivTCP**
4. All entities should be listed there

### Example Automations

**Charge Battery During Cheap Rate:**
```yaml
automation:
  - alias: "Charge Battery Cheap Rate"
    trigger:
      - platform: time
        at: "02:30:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.givtcp_target_soc
        data:
          value: 100
      - service: switch.turn_on
        target:
          entity_id: switch.givtcp_enable_charge
```

**Stop Charging After Cheap Rate:**
```yaml
automation:
  - alias: "Stop Charge After Cheap Rate"
    trigger:
      - platform: time
        at: "05:30:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.givtcp_enable_charge
```

## Troubleshooting

### Add-on Won't Start

**Check logs:**
1. Go to add-on page
2. Click **Log** tab
3. Look for error messages

**Common issues:**
- Inverter IP incorrect or unreachable
- MQTT broker not running
- Port conflicts with other add-ons

**Solutions:**
- Verify inverter IP: `ping <inverter_ip>` from SSH
- Install Mosquitto broker add-on
- Change ports in configuration if conflicts occur

### No Entities in Home Assistant

**Check:**
1. MQTT integration is configured and running
2. `ha_auto_discovery: true` in add-on configuration
3. MQTT broker address is correct (`core-mosquitto` for built-in)

**Verify MQTT messages:**
1. Install **MQTT Explorer** add-on
2. Subscribe to `GivEnergy/#`
3. Should see messages appearing

**Force rediscovery:**
1. Restart the GivTCP add-on
2. Restart Home Assistant
3. Check **Settings** → **Devices & Services** → **MQTT**

### Connection to Inverter Fails

**Check network:**
```bash
# From Home Assistant SSH/Terminal
ping 192.168.1.100  # Your inverter IP
```

**Verify inverter is accessible:**
- Check inverter is powered on
- Verify IP address hasn't changed (use DHCP reservation)
- Check no firewall is blocking port 8899

### Performance Issues

**Slow updates:**
- Increase `self_run_loop_timer` from 5 to 10 seconds
- Reduce `datasmoother` from High to Medium or Low

**High CPU usage:**
- Check logs for connection errors/retries
- Verify inverter connectivity is stable
- Consider enabling feature flags for improved performance

### Feature Flags Not Working

**Verify configuration:**
1. Check add-on configuration tab
2. Ensure flags are under `feature_flags:` section
3. Restart add-on after changes

**Check logs for confirmation:**
```
Feature Flags:
  USE_NEW_CACHE=true
  USE_NEW_LOCKS=true
  USE_NEW_SERVICES=true
```

## Updating

### Automatic Updates

Home Assistant will notify when updates are available:
1. Go to **Settings** → **Add-ons**
2. Click **Update** on GivTCP card
3. Wait for update to complete
4. Restart the add-on

### Manual Update

If using a Git repository:
```bash
cd /addons/giv_tcp
git pull
# Rebuild in Home Assistant UI
```

### Backup Before Update

**Recommended before major updates:**
1. Go to **Settings** → **System** → **Backups**
2. Create a new backup
3. Ensure it includes the GivTCP add-on
4. Proceed with update

## Advanced Configuration

### Custom Paths

Configuration is stored in:
- Add-on config: `/config` (Home Assistant config directory)
- Logs: `/config/GivTCP/logs`
- Cache: `/config/GivTCP/*.pkl`

### SSH Access

For debugging, enable SSH add-on:
1. Install **Terminal & SSH** add-on
2. Access add-on container:
   ```bash
   docker exec -it addon_<slug>_givtcp /bin/bash
   ```

### Ingress Support

Home Assistant Ingress allows accessing the dashboard without port exposure:
- Click **Open Web UI** on add-on page
- Uses Home Assistant authentication
- No need to expose port 3000

## Migration from Standalone Docker

If migrating from standalone Docker to Home Assistant add-on:

1. **Backup existing configuration:**
   ```bash
   tar -czf givtcp-backup.tar.gz config/
   ```

2. **Stop standalone Docker container:**
   ```bash
   docker-compose down
   ```

3. **Install Home Assistant add-on** (see Installation section)

4. **Transfer configuration:**
   - Copy settings from `.env` to add-on configuration UI
   - Copy any custom settings from `settings.json`

5. **Start add-on and verify**

6. **Remove standalone installation** once confirmed working

## Support

### Getting Help

**Check logs first:**
- Add-on **Log** tab shows real-time logs
- Look for error messages and warnings

**Community support:**
- Home Assistant Community Forum
- GitHub Issues: https://github.com/andrewbuckingham/giv_tcp/issues

**When asking for help, provide:**
1. Add-on version
2. Home Assistant version
3. Inverter model and firmware version
4. Relevant log excerpts
5. Configuration (redact passwords)

### Known Issues

**Issue:** MQTT entities not appearing
- **Solution:** Ensure Mosquitto broker add-on is installed and running

**Issue:** Slow response times
- **Solution:** Increase `self_run_loop_timer` or enable `use_new_services` flag

**Issue:** Connection timeouts
- **Solution:** Check network stability to inverter, consider enabling `use_new_locks` flag

## Technical Details

### Architecture

```
┌───────────────────────────────────────┐
│     Home Assistant Supervisor         │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │      GivTCP Add-on              │  │
│  │                                 │  │
│  │  ├─ Python Application          │  │
│  │  ├─ Redis Server                │  │
│  │  ├─ Mosquitto MQTT Broker       │  │
│  │  ├─ RQ Workers                  │  │
│  │  ├─ REST API                    │  │
│  │  └─ Web Dashboard               │  │
│  └─────────────────────────────────┘  │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │   Mosquitto Broker Add-on       │  │
│  └─────────────────────────────────┘  │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │   Home Assistant Core           │  │
│  │   (MQTT Integration)            │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
         │
         │ Modbus TCP
         ▼
   ┌─────────────┐
   │  GivEnergy  │
   │  Inverter   │
   └─────────────┘
```

### Data Flow

1. GivTCP polls inverter every `self_run_loop_timer` seconds
2. Data processed through service layer (if enabled)
3. Published to MQTT broker
4. Home Assistant MQTT integration receives messages
5. Entities updated in Home Assistant
6. Dashboard and API serve current data

## License

See LICENSE file in repository.

## Credits

- Original Author: britkat1980
- Contributors: See GitHub repository
- Home Assistant Community
