# GivTCP Home Assistant Add-on

![GivTCP Logo](logo.png)

GivEnergy integration for Home Assistant - read and control your GivEnergy inverter and batteries.

## About

GivTCP provides seamless integration between GivEnergy inverters and Home Assistant, allowing you to monitor and control your solar PV and battery storage system directly from your Home Assistant dashboard.

## Features

- 📊 **Real-time Monitoring**: Solar generation, battery status, grid import/export, and home consumption
- 🎛️ **Full Control**: Set charge/discharge schedules, target SOC, and operating modes
- 🏠 **Native Integration**: Automatic MQTT discovery for all sensors and controls
- 📈 **Historical Data**: Track energy production and consumption over time
- 🔄 **Automatic Updates**: Update directly through Home Assistant
- 🚀 **Performance**: Optional Phase 1-5 refactoring for improved stability

## Installation

1. Navigate to **Settings** → **Add-ons** → **Add-on Store** in Home Assistant
2. Click the **⋮** (three dots) menu → **Repositories**
3. Add this repository: `https://github.com/andrewbuckingham/giv_tcp`
4. Find **GivTCP** in the add-on store and click **Install**
5. Configure the add-on (see Configuration section)
6. Start the add-on and check the logs

**Full installation guide:** See [HASSIO_ADDON.md](HASSIO_ADDON.md)

## Configuration

### Required Settings

```yaml
invertor_ip: 192.168.1.100        # Your inverter IP address
num_batteries: 1                   # Number of batteries (0-3)
mqtt_address: core-mosquitto       # Use Home Assistant's MQTT broker
ha_auto_discovery: true           # Enable auto-discovery
```

### Feature Flags (Optional)

Enable improved implementations from Phase 1-5 refactoring:

```yaml
feature_flags:
  use_new_cache: false      # Thread-safe cache (eliminates race conditions)
  use_new_locks: false      # Improved locking (eliminates TOCTOU vulnerabilities)
  use_new_services: false   # Service layer (better code organization)
```

**Recommended rollout:** Enable one flag at a time, monitor for 24 hours between changes.

## Quick Start

1. **Install the add-on** (see Installation above)

2. **Configure your inverter IP:**
   - Go to add-on **Configuration** tab
   - Set `invertor_ip` to your inverter's IP address
   - Set `num_batteries` to your battery count

3. **Start the add-on:**
   - Click **Start**
   - Monitor the **Log** tab for successful connection

4. **Verify entities:**
   - Go to **Settings** → **Devices & Services** → **MQTT**
   - Look for GivEnergy devices and entities

5. **Access dashboard:**
   - Click **Open Web UI** button on add-on page
   - Or visit: `http://homeassistant.local:3000`

## Available Entities

Once configured, you'll have access to:

**Sensors:**
- PV Power (W)
- Battery SOC (%)
- Battery Power (W)
- Grid Power (W)
- Load Power (W)
- Import/Export Energy (kWh)
- And 50+ more sensors

**Controls:**
- Enable Charge Schedule
- Enable Discharge Schedule
- Target SOC
- Battery Reserve
- Charge/Discharge Rates
- Force Charge/Discharge

## Supported Hardware

- **Inverters**: All GivEnergy hybrid inverters
- **Batteries**: All GivEnergy battery modules (1-3 batteries)
- **Platforms**:
  - Raspberry Pi 2/3/4/5
  - x86-64 systems
  - ARM-based systems

## Documentation

- **[Full Add-on Guide](HASSIO_ADDON.md)** - Complete installation and configuration
- **[Docker Deployment](DOCKER_DEPLOYMENT.md)** - Standalone Docker setup
- **[Quick Start](QUICKSTART.md)** - 5-minute deployment guide

## Troubleshooting

### Add-on won't start
- Check logs for error messages
- Verify inverter IP is correct
- Ensure MQTT broker add-on is installed

### No entities appearing
- Check `ha_auto_discovery` is `true`
- Verify MQTT integration is configured
- Restart the add-on

### Connection issues
- Ping inverter: `ping <inverter_ip>`
- Check inverter is on same network
- Verify no firewall blocking port 8899

**More help:** See [Troubleshooting](HASSIO_ADDON.md#troubleshooting) in the full guide.

## Advanced Features

### PALM (Power Arbitrage Load Management)
Optimize battery charging/discharging for time-of-use tariffs (e.g., Octopus Agile):

```yaml
palm_winter: true
palm_min_soc_target: 75
palm_max_soc_target: 100
```

### InfluxDB Integration
Store historical data in InfluxDB:

```yaml
influx_output: true
influx_url: http://influxdb:8086
influx_token: your_token
influx_bucket: homeassistant
```

## Support

- **Issues**: [GitHub Issues](https://github.com/andrewbuckingham/giv_tcp/issues)
- **Community**: [Home Assistant Community Forum](https://community.home-assistant.io/)
- **Documentation**: See [HASSIO_ADDON.md](HASSIO_ADDON.md)

## Contributing

Contributions welcome! Please see the main repository for contribution guidelines.

## License

See [LICENSE](LICENSE) file.

## Changelog

### Version 2.5.0
- ✨ Home Assistant add-on support
- ✨ Phase 1-5 refactoring feature flags
- 🐛 Bug fixes and performance improvements
- 📚 Comprehensive documentation

See [CHANGELOG.md](CHANGELOG.md) for full history.

## Credits

- **Author**: britkat1980
- **Contributors**: See GitHub repository
- **Community**: Home Assistant users and testers

---

⭐ If you find this add-on useful, please star the repository!
