# GivTCP Docker Build and Push Script (PowerShell)
# Builds multi-architecture Docker image and pushes to custom registry
#
# Usage:
#   .\build.ps1 [version_tag]
#
# Examples:
#   .\build.ps1          # Builds and pushes as 'latest'
#   .\build.ps1 v2.5.0   # Builds and pushes as 'v2.5.0' and 'latest'
#

param(
    [string]$VersionTag = "latest"
)

# Configuration
$REGISTRY = "rpi-matthew.fritz.box:5000"
$IMAGE_NAME = "givtcp"

Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "  GivTCP Docker Build Script" -ForegroundColor Blue
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker is not running. Please start Docker and try again." -ForegroundColor Red
    exit 1
}

# Check if buildx is available
try {
    docker buildx version | Out-Null
    Write-Host "✓ Docker Buildx is available" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker Buildx is not available. Please install Docker Buildx." -ForegroundColor Red
    exit 1
}

# Create and use buildx builder
Write-Host ""
Write-Host "► Creating Docker Buildx builder..." -ForegroundColor Yellow

try {
    docker buildx create --name givtcp-builder --use 2>$null
}
catch {
    docker buildx use givtcp-builder
}

# Inspect builder
docker buildx inspect --bootstrap

# Build image for ARM architectures (Raspberry Pi)
Write-Host ""
Write-Host "► Building Docker image for ARM architectures..." -ForegroundColor Yellow
Write-Host "   Registry: $REGISTRY"
Write-Host "   Image: $IMAGE_NAME"
Write-Host "   Version: $VersionTag"
Write-Host ""

# Build for linux/arm/v7 (Raspberry Pi 2/3) and linux/arm64 (Raspberry Pi 4/5)
docker buildx build `
    --platform linux/arm/v7,linux/arm64 `
    --tag "${REGISTRY}/${IMAGE_NAME}:${VersionTag}" `
    --tag "${REGISTRY}/${IMAGE_NAME}:latest" `
    --push `
    --progress=plain `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ Build and push completed successfully!" -ForegroundColor Green
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Images pushed to registry:" -ForegroundColor Blue
    Write-Host "  • ${REGISTRY}/${IMAGE_NAME}:${VersionTag}"
    Write-Host "  • ${REGISTRY}/${IMAGE_NAME}:latest"
    Write-Host ""
    Write-Host "Deploy with:" -ForegroundColor Blue
    Write-Host "  docker-compose pull && docker-compose up -d"
    Write-Host ""
}
else {
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  ✗ Build failed!" -ForegroundColor Red
    Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Red
    exit 1
}

# Cleanup (optional)
# docker buildx rm givtcp-builder
