#!/bin/bash
# Build script for Combined ComfyUI + AI-Toolkit VastAI Template

set -eo pipefail

# Configuration
IMAGE_NAME="${IMAGE_NAME:-comfyui-ai-toolkit}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

# Full image name (set DOCKER_REGISTRY to your DockerHub username or registry)
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
if [[ -n "${DOCKER_REGISTRY}" ]]; then
    FULL_IMAGE="${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo "Building ${FULL_IMAGE}"
echo "  Platform: ${PLATFORM}"
echo ""

# Build the image
docker buildx build \
    --platform "${PLATFORM}" \
    -t "${FULL_IMAGE}" \
    "${@}" \
    .

echo ""
echo "Build complete: ${FULL_IMAGE}"
echo ""
echo "To push to registry:"
echo "  docker push ${FULL_IMAGE}"
