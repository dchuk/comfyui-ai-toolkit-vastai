# Auto-update utility functions
# Sourced by boot scripts — no shebang

# Fetch the latest release tag from a GitHub repository
# Usage: fetch_latest_github_release_tag <owner> <repo>
# Returns: tag string on stdout (e.g., "v0.3.1")
fetch_latest_github_release_tag() {
    local owner="$1"
    local repo="$2"
    local url="https://api.github.com/repos/${owner}/${repo}/releases/latest"
    local response
    local tag

    response=$(curl -fsSL --max-time 30 "$url" 2>/dev/null) || {
        echo "ERROR: Failed to fetch releases from ${url}" >&2
        return 1
    }

    tag=$(echo "$response" | grep -m1 '"tag_name"' | sed 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/') || {
        echo "ERROR: Failed to parse tag_name from GitHub API response" >&2
        return 1
    }

    if [[ -z "$tag" ]]; then
        echo "ERROR: Empty tag_name in GitHub API response for ${owner}/${repo}" >&2
        return 1
    fi

    echo "$tag"
}

# Safely update a git repository to a target ref with rollback on failure
# Usage: safe_git_update <dir> <ref>
# Returns: 0 on success, 1 on failure (rolls back to original HEAD)
safe_git_update() {
    local dir="$1"
    local ref="$2"
    local original_head

    if [[ ! -d "$dir/.git" ]]; then
        echo "ERROR: ${dir} is not a git repository" >&2
        return 1
    fi

    original_head=$(git -C "$dir" rev-parse HEAD 2>/dev/null) || {
        echo "ERROR: Failed to get current HEAD in ${dir}" >&2
        return 1
    }

    if ! git -C "$dir" fetch origin 2>&1; then
        echo "ERROR: git fetch failed in ${dir}, keeping current version" >&2
        return 1
    fi

    if ! git -C "$dir" checkout "$ref" 2>&1; then
        echo "ERROR: git checkout ${ref} failed in ${dir}, rolling back to ${original_head}" >&2
        git -C "$dir" checkout "$original_head" 2>/dev/null
        return 1
    fi

    return 0
}

# Validate that the current PyTorch version matches the expected version
# Usage: validate_pytorch_version <expected_version>
# Returns: 0 if match, 1 if mismatch
validate_pytorch_version() {
    local expected="$1"
    local actual

    actual=$(python -c 'import torch; print(torch.__version__)' 2>/dev/null) || {
        echo "ERROR: Failed to import torch to check version" >&2
        return 1
    }

    if [[ "$actual" != "$expected" ]]; then
        echo "CRITICAL: PyTorch version mismatch — expected ${expected} but got ${actual}" >&2
        return 1
    fi

    return 0
}

# Retry a command up to N times with a delay between attempts
# Usage: retry_command <max_retries> <cmd...>
# Returns: exit code of the last attempt
retry_command() {
    local max_retries="$1"
    shift
    local attempt=1
    local rc

    while [[ $attempt -le $max_retries ]]; do
        if "$@"; then
            return 0
        fi
        rc=$?
        echo "WARNING: Command failed (attempt ${attempt}/${max_retries}): $*" >&2
        if [[ $attempt -lt $max_retries ]]; then
            sleep 5
        fi
        attempt=$((attempt + 1))
    done

    echo "ERROR: Command failed after ${max_retries} attempts: $*" >&2
    return "${rc}"
}
