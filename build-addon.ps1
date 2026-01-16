#!/usr/bin/env pwsh
# Build script for GivTCP Home Assistant Add-on (PowerShell)
# Builds multi-architecture Docker images and pushes to registry

param(
    [switch]$Push = $false,
    [string]$Version = "2.5.1",
    [string]$Tag = "",
    [string]$Architecture = "linux/arm64",
    [string]$Registry = "ghcr.io",
    [string]$Repository = "yourusername/giv_tcp",
    [switch]$Help = $false
)

# Show help if requested
if ($Help) {
    Write-Host @"
Usage: .\build-addon.ps1 [OPTIONS]

Options:
  -Push                  Push images to registry after build
  -Version VERSION       Set version (default: 2.5.0)
  -Tag TAG              Set Docker tag (default: same as version)
  -Architecture ARCH    Architecture (default: linux/arm64 for RPi4)
  -Registry REG         Docker registry (default: ghcr.io)
  -Repository REPO      Repository name (default: yourusername/giv_tcp)
  -Help                 Show this help message

Examples:
  .\build-addon.ps1                                    # Build only (no push)
  .\build-addon.ps1 -Push                              # Build and push to registry
  .\build-addon.ps1 -Push -Tag dev                     # Build and push with 'dev' tag
  .\build-addon.ps1 -Push -Version 2.5.1               # Build version 2.5.1 and push
"@
    exit 0
}

# Set tag to version if not specified
if ([string]::IsNullOrEmpty($Tag)) {
    $Tag = $Version
}

$BuildDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$FullImage = "${Registry}/${Repository}"

# Color output functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

Write-ColorOutput "========================================" -Color Green
Write-ColorOutput "GivTCP Home Assistant Add-on Builder" -Color Green
Write-ColorOutput "========================================" -Color Green
Write-Host ""
Write-ColorOutput "Configuration:" -Color Yellow
Write-Host "  Registry:       $Registry"
Write-Host "  Repository:     $Repository"
Write-Host "  Version:        $Version"
Write-Host "  Tag:            $Tag"
Write-Host "  Architecture:   $Architecture"
Write-Host "  Build Date:     $BuildDate"
Write-Host "  Push:           $Push"
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed"
    }
} catch {
    Write-ColorOutput "Error: Docker is not running" -Color Red
    exit 1
}

# Check if buildx is available
try {
    docker buildx version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker buildx not available"
    }
} catch {
    Write-ColorOutput "Error: Docker buildx is not available" -Color Red
    Write-Host "Please install Docker buildx or update Docker to a newer version"
    exit 1
}

# Create or use existing buildx builder
$BuilderName = "givtcp-builder"
try {
    docker buildx inspect $BuilderName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Builder not found"
    }
    Write-ColorOutput "Using existing buildx builder: $BuilderName" -Color Yellow
    docker buildx use $BuilderName
} catch {
    Write-ColorOutput "Creating buildx builder: $BuilderName" -Color Yellow
    docker buildx create --name $BuilderName --use
}

# Bootstrap builder if needed
docker buildx inspect --bootstrap

# Build arguments
$BuildArgs = @(
    "buildx", "build",
    "--platform", $Architecture,
    "--file", "Dockerfile.hassio",
    "--build-arg", "BUILD_VERSION=$Version",
    "--build-arg", "BUILD_DATE=$BuildDate",
    "--build-arg", "BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.19",
    "--tag", "${FullImage}:${Tag}"
)

# Add latest tag for version releases
if ($Tag -eq $Version -and $Version -match '^\d+\.\d+\.\d+$') {
    $BuildArgs += @("--tag", "${FullImage}:latest")
}

# Add push or load option
if ($Push) {
    $BuildArgs += "--push"
    Write-ColorOutput "Building and pushing image to registry..." -Color Yellow
} else {
    $BuildArgs += "--load"
    Write-ColorOutput "Building local image..." -Color Yellow
}

$BuildArgs += "."

Write-Host ""
Write-ColorOutput "Build command:" -Color Yellow
Write-Host "docker $($BuildArgs -join ' ')"
Write-Host ""

# Execute build
try {
    & docker $BuildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-ColorOutput "========================================" -Color Green
    Write-ColorOutput "Build completed successfully!" -Color Green
    Write-ColorOutput "========================================" -Color Green
    Write-Host ""

    if ($Push) {
        Write-ColorOutput "Image pushed to registry:" -Color Green
        Write-Host "  ${FullImage}:${Tag}"
        if ($Tag -ne "latest" -and $Version -match '^\d+\.\d+\.\d+$') {
            Write-Host "  ${FullImage}:latest"
        }
    } else {
        Write-ColorOutput "Image available locally:" -Color Green
        Write-Host "  ${FullImage}:${Tag}"
    }

    Write-Host ""
    Write-ColorOutput "Next steps:" -Color Green
    if ($Push) {
        Write-Host "  1. Deploy to Home Assistant on RPi4"
        Write-Host "  2. Test the add-on functionality"
    } else {
        Write-Host "  1. Test the image locally"
        Write-Host "  2. Run with -Push when ready to deploy"
    }
} catch {
    Write-Host ""
    Write-ColorOutput "========================================" -Color Red
    Write-ColorOutput "Build failed!" -Color Red
    Write-ColorOutput "========================================" -Color Red
    Write-ColorOutput $_.Exception.Message -Color Red
    exit 1
}
