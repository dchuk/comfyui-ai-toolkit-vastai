#!/bin/bash
# Build script for Combined ComfyUI + AI-Toolkit VastAI Template

set -eo pipefail

# Configuration
IMAGE_NAME="${IMAGE_NAME:-comfyui-ai-toolkit}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
COMFYUI_REF="${COMFYUI_REF:-v0.3.0}"
AI_TOOLKIT_REF="${AI_TOOLKIT_REF:-6870ab4}"

# Full image name (set DOCKER_REGISTRY to your DockerHub username or registry)
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
if [[ -n "${DOCKER_REGISTRY}" ]]; then
    FULL_IMAGE="${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo "Building ${FULL_IMAGE}"
echo "  ComfyUI ref: ${COMFYUI_REF}"
echo "  AI-Toolkit ref: ${AI_TOOLKIT_REF}"
echo ""

# Build the image
docker buildx build \
    --build-arg COMFYUI_REF="${COMFYUI_REF}" \
    --build-arg AI_TOOLKIT_REF="${AI_TOOLKIT_REF}" \
    -t "${FULL_IMAGE}" \
    "${@}" \
    .

echo ""
echo "Build complete: ${FULL_IMAGE}"
echo ""
echo "To push to registry:"
echo "  docker push ${FULL_IMAGE}"
