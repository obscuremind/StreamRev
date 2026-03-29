# XC_VM vs StreamRev — Reality Check (2026-03-28)

This document answers: **"Is everything implemented like XC_VM?"**

## Short answer

**No.** StreamRev has compatibility scaffolding, but it is **not** feature/behavior parity with XC_VM yet.

## What is implemented

- XC-style entrypoints and directories exist (`src.bootstrap`, `src.service`, `src.update`, `src/content`, `src/tmp`, etc.).
- Multi-process orchestration baseline exists (`src/core/process/orchestrator.py`).
- DRM key endpoint is no longer placeholder-only and supports configurable provider modes (`off|static|http`).
- Module manifest support and parity tests were added.

## What is still missing for true XC_VM parity

1. **Service orchestration depth**
   - Current orchestrator launches a few Python commands, but does not replicate XC_VM's full daemon ecosystem and supervision behavior.

2. **Bootstrap semantics parity**
   - Context names exist, but XC_VM bootstrap side-effects (full init ordering, host/flood/session behavior parity) are not fully mirrored.

3. **Installer/provisioning parity**
   - Ubuntu installer script is baseline-only and does not cover complete production provisioning equivalence.

4. **DRM production parity**
   - Provider abstraction exists, but no built-in vendor integrations or key rotation workflows are implemented in-repo.

5. **End-to-end parity validation**
   - Current tests are baseline/unit-level; full XC-compatible integration and migration-grade acceptance coverage is still pending.

## Conclusion

The repo has **substantial parity groundwork**, but **not complete XC_VM equivalence**. Treat current state as: **partial parity implementation**.
