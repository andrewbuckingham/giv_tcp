#!/bin/bash
# Build script for GivTCP Home Assistant Add-on
# Builds multi-architecture Docker images and pushes to registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY:-rpi-matthew.fritz.box:5000}"
REPOSITORY="${REPOSITORY:-giv_tcp}"
VERSION="${VERSION:-2.5.0}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Parse command line arguments
PUSH=false
ARCHITECTURES="linux/arm64"
TAG="${VERSION}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --version)
            VERSION="$2"
            TAG="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --arch)
            ARCHITECTURES="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --repository)
            REPOSITORY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --push              Push images to registry after build"
            echo "  --version VERSION   Set version (default: 2.5.0)"
            echo "  --tag TAG          Set Docker tag (default: same as version)"
            echo "  --arch ARCH        Architecture (default: linux/arm64 for RPi4)"
            echo "  --registry REG     Docker registry (default: rpi-matthew.fritz.box:5000)"
            echo "  --repository REPO  Repository name (default: giv_tcp)"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Build only (no push)"
            echo "  $0 --push                             # Build and push to registry"
            echo "  $0 --push --tag dev                   # Build and push with 'dev' tag"
            echo "  $0 --push --version 2.5.1             # Build version 2.5.1 and push"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Derived variables
FULL_IMAGE="${REGISTRY}/${REPOSITORY}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GivTCP Home Assistant Add-on Builder${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Registry:       ${REGISTRY}"
echo "  Repository:     ${REPOSITORY}"
echo "  Version:        ${VERSION}"
echo "  Tag:            ${TAG}"
echo "  Architectures:  ${ARCHITECTURES}"
echo "  Build Date:     ${BUILD_DATE}"
echo "  Push:           ${PUSH}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker buildx is not available${NC}"
    echo "Please install Docker buildx or update Docker to a newer version"
    exit 1
fi

# Create or use existing buildx builder
BUILDER_NAME="givtcp-builder"
if ! docker buildx inspect ${BUILDER_NAME} > /dev/null 2>&1; then
    echo -e "${YELLOW}Creating buildx builder: ${BUILDER_NAME}${NC}"
    docker buildx create --name ${BUILDER_NAME} --use
else
    echo -e "${YELLOW}Using existing buildx builder: ${BUILDER_NAME}${NC}"
    docker buildx use ${BUILDER_NAME}
fi

# Bootstrap builder if needed
docker buildx inspect --bootstrap

# Build command
BUILD_CMD="docker buildx build"
BUILD_CMD="${BUILD_CMD} --platform ${ARCHITECTURES}"
BUILD_CMD="${BUILD_CMD} --file Dockerfile.hassio"
BUILD_CMD="${BUILD_CMD} --build-arg BUILD_VERSION=${VERSION}"
BUILD_CMD="${BUILD_CMD} --build-arg BUILD_DATE=${BUILD_DATE}"
BUILD_CMD="${BUILD_CMD} --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.19"

# Add tags
BUILD_CMD="${BUILD_CMD} --tag ${FULL_IMAGE}:${TAG}"
if [[ "${TAG}" == "${VERSION}" ]] && [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Also tag as 'latest' for version releases
    BUILD_CMD="${BUILD_CMD} --tag ${FULL_IMAGE}:latest"
fi

# Add push or load option
if [[ "${PUSH}" == "true" ]]; then
    BUILD_CMD="${BUILD_CMD} --push"
    echo -e "${YELLOW}Building and pushing image to registry...${NC}"
else
    BUILD_CMD="${BUILD_CMD} --load"
    echo -e "${YELLOW}Building local image...${NC}"
fi

BUILD_CMD="${BUILD_CMD} ."

echo ""
echo -e "${YELLOW}Build command:${NC}"
echo "${BUILD_CMD}"
echo ""

# Execute build
if eval ${BUILD_CMD}; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    if [[ "${PUSH}" == "true" ]]; then
        echo -e "${GREEN}Image pushed to registry:${NC}"
        echo "  ${FULL_IMAGE}:${TAG}"
        if [[ "${TAG}" != "latest" ]] && [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "  ${FULL_IMAGE}:latest"
        fi
    else
        echo -e "${GREEN}Image available locally:${NC}"
        echo "  ${FULL_IMAGE}:${TAG}"
    fi

    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    if [[ "${PUSH}" == "true" ]]; then
        echo "  1. Deploy to Home Assistant on RPi4"
        echo "  2. Test the add-on functionality"
    else
        echo "  1. Test the image locally"
        echo "  2. Run with --push when ready to deploy"
    fi
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Build failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
