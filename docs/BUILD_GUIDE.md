# GivTCP Home Assistant Add-on Build Guide

This guide explains how to build and publish the GivTCP Home Assistant add-on for **Raspberry Pi 4** (linux/arm64).

## Prerequisites

1. **Docker with buildx support** (Docker Desktop or Docker Engine 19.03+)
2. **Git** for version control
3. **Access to self-hosted registry** at rpi-matthew.fritz.box:5000
4. **VS Code** (optional, for using build tasks)

## Quick Start

### Option 1: Using VS Code Tasks (Recommended)

1. Open the project in VS Code
2. Press `Ctrl+Shift+B` for default build, or:
3. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
4. Type "Tasks: Run Task"
5. Select one of the build tasks:
   - **Build Add-on: Local (RPi4)** - Local build for testing (default, Ctrl+Shift+B)
   - **Build and Push Add-on: Latest** - Build and push with version tag + latest
   - **Build and Push Add-on: Dev Tag** - Build and push with 'dev' tag
   - **Build and Push Add-on: Custom Version** - Prompts for version number

### Option 2: Using Command Line

**Linux/Mac:**
```bash
# Local build for RPi4
./build-addon.sh

# Build and push to registry
./build-addon.sh --push

# Build specific version and push
./build-addon.sh --push --version 2.5.1

# Build with dev tag
./build-addon.sh --push --tag dev
```

**Windows (PowerShell):**
```powershell
# Local build for RPi4
.\build-addon.ps1

# Build and push to registry
.\build-addon.ps1 -Push

# Build specific version and push
.\build-addon.ps1 -Push -Version 2.5.1

# Build with dev tag
.\build-addon.ps1 -Push -Tag dev
```

## Build Scripts

### build-addon.sh (Linux/Mac)

Bash script for building Docker images for Raspberry Pi 4.

**Features:**
- Builds for linux/arm64 (Raspberry Pi 4)
- Automatic buildx builder creation
- Version tagging
- Push to registry
- Color-coded output

**Usage:**
```bash
./build-addon.sh [OPTIONS]

Options:
  --push              Push images to registry after build
  --version VERSION   Set version (default: 2.5.0)
  --tag TAG          Set Docker tag (default: same as version)
  --arch ARCH        Comma-separated architectures
  --registry REG     Docker registry (default: rpi-matthew.fritz.box:5000)
  --repository REPO  Repository name (default: giv_tcp)
  --help             Show help message
```

### build-addon.ps1 (Windows)

PowerShell script with identical functionality to the bash version.

**Usage:**
```powershell
.\build-addon.ps1 [OPTIONS]

Parameters:
  -Push                  Push images to registry after build
  -Version VERSION       Set version (default: 2.5.0)
  -Tag TAG              Set Docker tag (default: same as version)
  -Architectures ARCH   Comma-separated architectures
  -Registry REG         Docker registry (default: rpi-matthew.fritz.box:5000)
  -Repository REPO      Repository name (default: giv_tcp)
  -Help                 Show help message
```

## Build Architecture

This add-on is built specifically for **Raspberry Pi 4** with 64-bit Home Assistant OS:

- **linux/arm64** (aarch64) - Raspberry Pi 4 with 64-bit OS

The default architecture is `linux/arm64`. You can override this with the `--arch` parameter if needed for testing on other platforms.

## Registry Configuration

### Default: Self-Hosted Registry

The default configuration pushes to a self-hosted Docker registry:

```
rpi-matthew.fritz.box:5000/giv_tcp
```

**Authentication:**
```bash
# Log in to self-hosted registry (if authentication required)
docker login rpi-matthew.fritz.box:5000
```

**Note:** If your registry uses HTTP instead of HTTPS, you may need to configure Docker to allow insecure registries. Add to `/etc/docker/daemon.json`:

```json
{
  "insecure-registries": ["rpi-matthew.fritz.box:5000"]
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

### Alternative Registries

To use a different registry (Docker Hub, GitHub Container Registry, etc.):

```bash
# GitHub Container Registry
./build-addon.sh --push --registry ghcr.io --repository yourusername/givtcp

# Docker Hub
./build-addon.sh --push --registry docker.io --repository yourusername/givtcp

# Another private registry
./build-addon.sh --push --registry registry.example.com --repository givtcp
```

## Version Management

### Semantic Versioning

GivTCP follows semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes
- **MINOR** - New features (backwards compatible)
- **PATCH** - Bug fixes

### Version Tags

When building a release version (e.g., 2.5.0), two tags are created:

1. **Version tag** - `2.5.0`
2. **Latest tag** - `latest`

Example:
```bash
./build-addon.sh --push --version 2.5.0
# Creates: rpi-matthew.fritz.box:5000/giv_tcp:2.5.0
#      and rpi-matthew.fritz.box:5000/giv_tcp:latest
```

### Development Builds

For development/testing, use custom tags:

```bash
# Development tag
./build-addon.sh --push --tag dev

# Feature branch
./build-addon.sh --push --tag feature-mqtt-improvements

# Test build
./build-addon.sh --push --tag test-$(date +%Y%m%d)
```

## Build Workflow

### Development Workflow

1. **Make changes** to code
2. **Build locally** for testing:
   ```bash
   ./build-addon.sh
   ```
3. **Test** the local image
4. **Push dev build** when ready:
   ```bash
   ./build-addon.sh --push --tag dev
   ```
5. **Test in Home Assistant** with dev tag

### Release Workflow

1. **Update version** in `config.json`
2. **Build and push** release:
   ```bash
   ./build-addon.sh --push --version 2.5.0
   ```
3. **Create Git tag**:
   ```bash
   git tag v2.5.0
   git push origin v2.5.0
   ```
4. **Create GitHub release** with changelog
5. **Announce** to users

## Testing Builds

### Local Container Testing

Run the built container locally for testing:

```bash
docker run --rm -it \
  -p 1883:1883 \
  -p 3000:3000 \
  -p 6345:8099 \
  -e INVERTOR_IP=192.168.1.100 \
  -e INVERTOR_NUM_BATTERIES=1 \
  -e MQTT_ADDRESS=localhost \
  -e MQTT_TOPIC=GivEnergy \
  -e HA_AUTO_D=False \
  -e LOG_LEVEL=Debug \
  -e SELF_RUN_LOOP_TIMER=5 \
  rpi-matthew.fritz.box:5000/giv_tcp:local-test
```

Or use the VS Code task: **Test: Run Add-on Container Locally**

### Home Assistant Testing

1. **Install add-on** from custom repository
2. **Point to dev tag** (if testing dev builds):
   - Edit `config.json` temporarily
   - Change image tag to `dev`
3. **Configure** the add-on
4. **Start** and check logs
5. **Verify** functionality

## VS Code Tasks

The `.vscode/tasks.json` provides convenient build tasks:

### Build Tasks

| Task | Description | Shortcut |
|------|-------------|----------|
| Build Add-on: Local (RPi4) | Local build for Raspberry Pi 4 | Ctrl+Shift+B (default) |
| Build and Push Add-on: Latest | Build and push release | - |
| Build and Push Add-on: Dev Tag | Build and push dev version | - |
| Build and Push Add-on: Custom Version | Prompts for version | - |

### Utility Tasks

| Task | Description |
|------|-------------|
| Docker: Clean Buildx Cache | Remove build cache |
| Docker: Remove Buildx Builder | Remove builder instance |
| Docker: Show Local Images | List GivTCP images |
| Git: Add All Addon Files | Stage addon files for commit |

### Running Tasks

1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type "Tasks: Run Task"
3. Select the desired task
4. Follow any prompts (for custom version builds)

## Troubleshooting

### Build Fails: "buildx: command not found"

**Solution:**
- Update Docker to version 19.03 or later
- Enable Docker BuildKit
- Install buildx plugin

### Push Fails: Authentication Error

**Solution:**
```bash
# Self-hosted registry
docker login rpi-matthew.fritz.box:5000

# GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Docker Hub
docker login
```

### Slow Build Times

**Solutions:**
1. **Use BuildKit cache:**
   ```bash
   export DOCKER_BUILDKIT=1
   ```

2. **Clean old images:**
   ```bash
   docker buildx prune -f
   docker system prune -a
   ```

### Image Not Loading in Home Assistant

**Check:**
1. **Image tag** matches in config.json
2. **Registry is accessible** from Home Assistant host
3. **Authentication** is configured (for private registries)
4. **Pull image manually** to test:
   ```bash
   docker pull rpi-matthew.fritz.box:5000/giv_tcp:2.5.0
   ```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/build-addon.yml`:

```yaml
name: Build and Publish Add-on

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract version from tag
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Build and push
        run: |
          chmod +x build-addon.sh
          ./build-addon.sh --push --version ${{ steps.version.outputs.VERSION }}
```

## Advanced Topics

### Custom Base Images

To use different base images, modify `build.json`:

```json
{
  "build_from": {
    "amd64": "ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.19",
    "armv7": "ghcr.io/home-assistant/armv7-base-python:3.11-alpine3.19",
    "aarch64": "ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.19"
  }
}
```

### Build Arguments

Customize build with additional arguments in the build scripts:

- `BUILD_VERSION` - Version number
- `BUILD_DATE` - Build timestamp
- `BUILD_FROM` - Base image

### Cache Optimization

For faster rebuilds, use cache mounts in Dockerfile:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

## Summary

**Quick Commands:**

```bash
# Development (local test for RPi4)
./build-addon.sh

# Development (push dev build)
./build-addon.sh --push --tag dev

# Production (release)
./build-addon.sh --push --version 2.5.1
```

**VS Code:**
- Press `Ctrl+Shift+B` for default build
- Use Task Runner for other builds

**Key Files:**
- `build-addon.sh` - Linux/Mac build script
- `build-addon.ps1` - Windows build script
- `.vscode/tasks.json` - VS Code build tasks
- `Dockerfile.hassio` - Add-on Dockerfile
- `build.json` - Build configuration
- `config.json` - Add-on metadata

For more information, see:
- [HASSIO_ADDON.md](HASSIO_ADDON.md) - Add-on usage guide
- [DEPLOYMENT_METHODS.md](DEPLOYMENT_METHODS.md) - Deployment comparison
