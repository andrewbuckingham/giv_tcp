#!/bin/bash
#
# GivTCP Docker Build and Push Script
# Builds multi-architecture Docker image and pushes to custom registry
#
# Usage:
#   ./build.sh [version_tag]
#
# Examples:
#   ./build.sh          # Builds and pushes as 'latest'
#   ./build.sh v2.5.0   # Builds and pushes as 'v2.5.0' and 'latest'
#

set -e  # Exit on error

# Configuration
REGISTRY="rpi-matthew.fritz.box:5000"
IMAGE_NAME="givtcp"
VERSION_TAG="${1:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GivTCP Docker Build Script${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker Buildx is not available. Please install Docker Buildx.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker Buildx is available${NC}"

# Create and use buildx builder
echo ""
echo -e "${YELLOW}► Creating Docker Buildx builder...${NC}"
docker buildx create --name givtcp-builder --use 2>/dev/null || docker buildx use givtcp-builder

# Inspect builder
docker buildx inspect --bootstrap

# Build image for ARM architectures (Raspberry Pi)
echo ""
echo -e "${YELLOW}► Building Docker image for ARM architectures...${NC}"
echo -e "   Registry: ${REGISTRY}"
echo -e "   Image: ${IMAGE_NAME}"
echo -e "   Version: ${VERSION_TAG}"
echo ""

# Build for linux/arm/v7 (Raspberry Pi 2/3) and linux/arm64 (Raspberry Pi 4/5)
docker buildx build \
    --platform linux/arm/v7,linux/arm64 \
    --tag "${REGISTRY}/${IMAGE_NAME}:${VERSION_TAG}" \
    --tag "${REGISTRY}/${IMAGE_NAME}:latest" \
    --push \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Build and push completed successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Images pushed to registry:${NC}"
    echo -e "  • ${REGISTRY}/${IMAGE_NAME}:${VERSION_TAG}"
    echo -e "  • ${REGISTRY}/${IMAGE_NAME}:latest"
    echo ""
    echo -e "${BLUE}Deploy with:${NC}"
    echo -e "  docker-compose pull && docker-compose up -d"
    echo ""
else
    echo ""
    echo -e "${RED}════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ✗ Build failed!${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════${NC}"
    exit 1
fi

# Cleanup (optional)
# docker buildx rm givtcp-builder
