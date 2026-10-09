# Bug Log

Bugs found during the build, logged when they are found. This log feeds the "iterations" and
"learnings" sections of the Google Doc. Real problems are kept, not cleaned away.

## Entry format

```
### B-001 · 2026-10-09 · Phase 4 Dashboard

**Symptom:** what went wrong, as seen.
**Cause:** why it happened.
**Fix:** what changed.
**Lesson:** what to remember next time.
**Found by:** test, eval, manual check, or review. Related prompt: P-00X.
```

## Entries

### B-001 · 2026-10-09 · Phase 1 Setup

**Symptom:** `brew install uv` ran for more than ten minutes without finishing. It was compiling
cmake from source instead of downloading a ready-made package.
**Cause:** the build machine is an Intel Mac. Homebrew no longer ships ready-made packages
("bottles") for it, so it builds uv and its build tools from source.
**Fix:** stopped the Homebrew build and installed uv with Astral's official installer, which
downloads a ready-made binary for Intel Macs into `~/.local/bin`. It finished in seconds.
**Lesson:** check whether a package manager will download or compile before relying on it under a
deadline. On this machine, prefer the vendor's own installer for developer tools.
**Found by:** manual check of the stalled install. Related prompt: P-001.
