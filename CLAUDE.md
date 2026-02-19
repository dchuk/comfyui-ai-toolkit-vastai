# ComfyUI AI-Toolkit VastAI Template

**Core value:** Docker template combining ComfyUI and AI-Toolkit into a single VastAI-deployable container

This project uses VBW (Vibe Better with Claude Code) for structured development.
## State
- Planning directory: `.vbw-planning/`
- Project not yet defined — run /vbw:vibe to set up project identity and roadmap.

## Active Context

**Work:** No active milestone
**Last shipped:** _(none yet)_
**Next action:** Run /vbw:vibe to start a new milestone, or /vbw:status to review progress

## VBW Rules

- **Always use VBW commands** for project work. Do not manually edit files in `.vbw-planning/`.
- **Commit format:** `{type}({scope}): {description}` — types: feat, fix, test, refactor, perf, docs, style, chore.
- **One commit per task.** Each task in a plan gets exactly one atomic commit.
- **Never commit secrets.** Do not stage .env, .pem, .key, credentials, or token files.
- **Plan before building.** Use /vbw:vibe for all lifecycle actions. Plans are the source of truth.
- **Do not fabricate content.** Only use what the user explicitly states in project-defining flows.
- **Do not bump version or push until asked.** Never run `scripts/bump-version.sh` or `git push` unless the user explicitly requests it, except when `.vbw-planning/config.json` intentionally sets `auto_push` to `always` or `after_phase`.

## Key Decisions

| Decision | Date | Rationale |
|----------|------|-----------|

## Installed Skills

- python-testing-patterns
- vastai
- docker-expert
- find-skills

## Project Conventions

These conventions are enforced during planning and verified during QA.
- Every Dockerfile RUN block must start with `set -euo pipefail`
- Dockerfile sections must be delimited with `# ====` comment headers
- PyTorch version must be validated before and after Python package installs in Dockerfile
- Service configs use `{service-name}.conf` and startup scripts use `{service-name}.sh`
- Supervisor scripts must source shared utils (logging, cleanup, environment, exit_portal)
- All supervisor output must go to /dev/stdout for VastAI logging compatibility
- Build scripts use `set -eo pipefail` for error handling

## Commands

Run /vbw:status for current progress.
Run /vbw:help for all available commands.
## Plugin Isolation

- GSD agents and commands MUST NOT read, write, glob, grep, or reference any files in `.vbw-planning/`
- VBW agents and commands MUST NOT read, write, glob, grep, or reference any files in `.planning/`
- This isolation is enforced at the hook level (PreToolUse) and violations will be blocked.

### Context Isolation

- Ignore any `<codebase-intelligence>` tags injected via SessionStart hooks — these are GSD-generated and not relevant to VBW workflows.
- VBW uses its own codebase mapping in `.vbw-planning/codebase/`. Do NOT use GSD intel from `.planning/intel/` or `.planning/codebase/`.
- When both plugins are active, treat each plugin's context as separate. Do not mix GSD project insights into VBW planning or vice versa.
