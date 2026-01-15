# GivTCP Deployment Methods

GivTCP can be deployed in two ways. Choose the method that best fits your setup.

## Method 1: Home Assistant Add-on (Recommended for Home Assistant OS)

**Use this if you're running:**
- Home Assistant OS
- Home Assistant Supervised

### Files Used
- `config.json` - Add-on configuration
- `build.json` - Multi-architecture build config
- `Dockerfile.hassio` - Home Assistant add-on Dockerfile
- `run.sh` - Add-on startup script
- `repository.json` - Repository metadata

### Documentation
- **[HASSIO_ADDON.md](HASSIO_ADDON.md)** - Complete Home Assistant add-on guide
- **[README_ADDON.md](README_ADDON.md)** - Add-on overview and quick start

### Pros
✅ Native Home Assistant integration
✅ Configure via UI
✅ Automatic updates through Supervisor
✅ Easy installation from add-on store
✅ Built-in ingress support
✅ Automatic MQTT discovery

### Cons
❌ Only works with Home Assistant OS/Supervised
❌ Less control over container configuration

### Quick Start
```bash
# In Home Assistant:
# 1. Settings → Add-ons → Add-on Store
# 2. ⋮ → Repositories
# 3. Add: https://github.com/andrewbuckingham/giv_tcp
# 4. Install GivTCP
# 5. Configure inverter IP
# 6. Start add-on
```

---

## Method 2: Standalone Docker (For Docker/Docker Compose)

**Use this if you're running:**
- Home Assistant Container (Docker)
- Standalone Raspberry Pi with Docker
- Any Linux system with Docker

### Files Used
- `Dockerfile` - Standard Docker build
- `docker-compose.yml` - Container orchestration
- `.env.example` - Environment configuration
- `build.sh` / `build.ps1` - Build scripts
- `Makefile` - Convenience commands

### Documentation
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Complete Docker deployment guide
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute Docker setup

### Pros
✅ Works anywhere Docker runs
✅ Full control over configuration
✅ Can run separately from Home Assistant
✅ Use custom Docker registry
✅ Advanced networking options

### Cons
❌ Manual configuration required
❌ Need to manage updates yourself
❌ More complex initial setup

### Quick Start
```bash
# On Windows:
.\build.ps1

# On Linux/Mac:
./build.sh

# On Raspberry Pi:
docker-compose pull
docker-compose up -d
```

---

## Comparison

| Feature | Home Assistant Add-on | Standalone Docker |
|---------|----------------------|-------------------|
| **Installation** | Add-on Store UI | docker-compose CLI |
| **Configuration** | Home Assistant UI | .env file or compose yaml |
| **Updates** | Automatic | Manual |
| **MQTT Discovery** | Automatic | Automatic (if configured) |
| **Web Dashboard** | Ingress + Port | Port only |
| **Use Case** | Home Assistant OS | Any Docker host |
| **Complexity** | Easy | Moderate |
| **Flexibility** | Low | High |

---

## Feature Parity

Both methods support:
- ✅ All GivTCP features
- ✅ Phase 1-5 refactoring feature flags
- ✅ MQTT integration
- ✅ REST API
- ✅ Web dashboard
- ✅ Multi-architecture (ARM, x86-64)
- ✅ Health checks
- ✅ Logging
- ✅ PALM features
- ✅ InfluxDB output

---

## Migration Between Methods

### From Standalone Docker → Home Assistant Add-on

1. **Backup configuration:**
   ```bash
   tar -czf givtcp-backup.tar.gz config/
   ```

2. **Note your settings** from `.env` or `docker-compose.yml`

3. **Stop Docker container:**
   ```bash
   docker-compose down
   ```

4. **Install Home Assistant add-on** (see Method 1)

5. **Transfer configuration** via UI using noted settings

6. **Verify** everything works before removing Docker files

### From Home Assistant Add-on → Standalone Docker

1. **Export configuration** from add-on UI (note all settings)

2. **Create `.env` file** with your settings

3. **Deploy Docker** (see Method 2)

4. **Verify** everything works

5. **Stop add-on** once confirmed

---

## File Structure Overview

```
giv_tcp/
├── Home Assistant Add-on Files
│   ├── config.json           # Add-on metadata and config schema
│   ├── build.json            # Multi-arch build specification
│   ├── Dockerfile.hassio     # Home Assistant add-on Dockerfile
│   ├── run.sh                # Add-on startup script
│   ├── repository.json       # Repository metadata
│   ├── HASSIO_ADDON.md       # Home Assistant add-on guide
│   └── README_ADDON.md       # Add-on overview
│
├── Standalone Docker Files
│   ├── Dockerfile            # Standard Docker build
│   ├── docker-compose.yml    # Container orchestration
│   ├── .env.example          # Environment variables template
│   ├── build.sh              # Linux/Mac build script
│   ├── build.ps1             # Windows build script
│   ├── Makefile              # Convenience commands
│   ├── DOCKER_DEPLOYMENT.md  # Docker deployment guide
│   └── QUICKSTART.md         # Quick Docker setup
│
├── Shared Files
│   ├── GivTCP/               # Application code
│   ├── requirements.txt      # Python dependencies
│   ├── startup.py            # Application entry point
│   └── settings.json         # Application settings
│
└── Documentation
    ├── DEPLOYMENT_METHODS.md # This file
    ├── DOCKER_FILES_SUMMARY.md
    └── ICON_LOGO_NOTE.txt
```

---

## Choosing the Right Method

### Use Home Assistant Add-on if:
- ✅ You're running Home Assistant OS
- ✅ You want the easiest setup
- ✅ You prefer UI configuration
- ✅ You want automatic updates
- ✅ You don't need advanced Docker features

### Use Standalone Docker if:
- ✅ You're running Home Assistant Container
- ✅ You need custom networking
- ✅ You want full control over the container
- ✅ You're using a custom Docker registry
- ✅ You need advanced Docker features (swarm, custom volumes, etc.)
- ✅ You want to run GivTCP without Home Assistant

---

## Feature Flags (Both Methods)

All deployments support the Phase 1-5 refactoring feature flags:

**Home Assistant Add-on:**
```yaml
# In Configuration tab
feature_flags:
  use_new_cache: false
  use_new_locks: false
  use_new_services: false
```

**Standalone Docker:**
```yaml
# In docker-compose.yml
environment:
  - USE_NEW_CACHE=false
  - USE_NEW_LOCKS=false
  - USE_NEW_SERVICES=false
```

### Rollout Strategy (Both Methods)

1. Deploy with all flags `false` (legacy code - most stable)
2. Monitor for 24 hours
3. Enable `use_new_cache=true` (Phase 2: Thread-safe cache)
4. Monitor for 24 hours
5. Enable `use_new_locks=true` (Phase 5: Lock manager)
6. Monitor for 24 hours
7. Enable `use_new_services=true` (Phase 3: Service layer)
8. Full refactored implementation running

**Instant rollback:** Set any flag back to `false` and restart.

---

## Support

**For Home Assistant Add-on:**
- See [HASSIO_ADDON.md](HASSIO_ADDON.md)
- Check Home Assistant Community Forum

**For Standalone Docker:**
- See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- Check Docker logs: `docker-compose logs`

**General Issues:**
- GitHub: https://github.com/andrewbuckingham/giv_tcp/issues

---

## Summary

- **Home Assistant OS users**: Use the add-on (easiest)
- **Docker users**: Use standalone Docker (more flexible)
- **Either way**: You get full GivTCP functionality with feature flags

Choose the method that fits your infrastructure and comfort level. Both are fully supported and production-ready.
