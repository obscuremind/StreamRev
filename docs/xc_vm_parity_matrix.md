# XC_VM Parity Matrix (Reality Status)

| Area | Status | Evidence |
|---|---|---|
| Runtime/service model | Partial | `src/core/process/orchestrator.py` provides baseline orchestration but not full XC daemon parity |
| Bootstrap behavior | Partial | `src/bootstrap.py` has contexts but limited semantic parity |
| Installer/provisioning | Partial | `infrastructure/scripts/install_ubuntu.sh` is baseline bootstrap, not full equivalence |
| Module contract | Implemented (baseline) | `src/core/module/loader.py` + module `MODULE_MANIFEST` declarations |
| DRM endpoint | Implemented (baseline) | `src/streaming/drm/provider.py` + `/live/.../key` integration |
| Parity tests | Partial | `tests/parity/test_baseline.py` covers baseline only |
| Full XC_VM equivalence | Not achieved | Aggregate of above partials |
