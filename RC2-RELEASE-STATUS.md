# RC2 Release Status

**Status:** FROZEN — NATIVE WINDOWS CERTIFICATION PASSED
**Date:** 2026-09-17
**Release:** Protean Workspace `0.6.1 RC2`

---

## Release summary

Protean Workspace `0.6.1 RC2` has completed its stabilization and certification cycle.

All required RC2 release gates have passed, including:

* source-integrity verification;
* targeted regression testing;
* complete automated test-suite execution;
* clean-environment dependency reproduction;
* correctness linting;
* Electron dependency reproduction;
* character and asset manifest validation;
* Windows installer/runtime contract verification;
* resource and lifecycle stress testing;
* native Windows/Electron stability certification.

The RC2 code and release configuration are now **frozen**.

No additional feature work should be introduced into this release candidate without reopening the release process and repeating the affected certification gates.

RC2 may proceed to **Phase B**.

---

# Release state

| Item                                  | Status                  |
| ------------------------------------- | ----------------------- |
| RC2 implementation                    | **COMPLETE**            |
| Automated regression suite            | **PASS**                |
| Clean-environment reproduction        | **PASS**                |
| Python correctness lint               | **PASS**                |
| Electron dependency reproduction      | **PASS**                |
| Manifest validation                   | **PASS**                |
| Windows launcher contract             | **PASS**                |
| Resource/lifecycle stress testing     | **PASS**                |
| Native Windows/Electron certification | **PASS**                |
| Release state                         | **FROZEN**              |
| Phase B eligibility                   | **APPROVED TO PROCEED** |

---

# Completed gates

## Source integrity

* Exact RC1 source archive SHA-256 recorded.
* Clean RC1 extraction compared against the release source.
* RC2 changes were evaluated from a controlled source baseline.

---

## RC2-targeted regressions

RC2-specific regression tests completed successfully:

```text
17 passed
```

No targeted regression failures remained at release freeze.

---

## Complete automated test suite

The full inherited + RC2 suite completed successfully:

```text
88 passed
```

The entire suite was then repeated under a fresh environment installed exclusively from:

```text
requirements-lock.txt
```

Result:

```text
88 passed
```

This confirms that the automated release suite remains reproducible from the locked Python dependency environment.

---

## Python correctness lint

Correctness-focused linting was executed across the Python package and RC2 tests using:

```text
E9
F
```

Result:

```text
PASS
```

No blocking Python syntax or undefined-name correctness issues remained.

---

## Electron dependency reproduction

Electron dependencies were reproduced using:

```text
npm ci
```

The complete lock-file installation succeeded.

The installed Electron binary reported:

```text
v44.2.0
```

during the available non-UI version verification.

This established reproducibility of the Electron dependency set before native Windows certification.

---

## Character and asset manifests

JSON character and asset manifests were parsed successfully.

Result:

```text
PASS
```

No release-blocking malformed manifest data remained.

---

## Windows entry-point consolidation

The Windows release exposes exactly two supported user entry points:

```text
install.bat
start.bat
```

The installer:

* prepares the Python runtime;
* installs locked Python dependencies;
* installs the Electron dependency tree;
* explicitly fetches Electron 44's platform executable after `npm ci`;
* verifies the exact Electron executable required by the runtime;
* does not report successful completion until the required runtime components exist.

The startup path:

* verifies the Python environment;
* verifies the Electron Assistant runtime;
* reruns the same installer when either runtime is missing.

The installer/runtime path contract is covered by automated regression tests and has now also been exercised as part of the native Windows certification process.

---

## Asset correction

An oversized background asset was identified and corrected.

Original asset:

```text
Size:       8,070,311 bytes
Dimensions: 8686 × 5790
Encoding:   JPEG
Extension:  .webp
```

Corrected asset:

```text
Size:       475,200 bytes
Dimensions: 2160 × 1440
Encoding:   WebP
```

This removed the incorrect format/extension mismatch and substantially reduced unnecessary runtime asset size.

---

# Resource and lifecycle stress validation

A local service/resource stress check completed:

```text
900 total requests
```

Workload:

| Operation                    |   Count |
| ---------------------------- | ------: |
| Health requests              |     500 |
| Duplicate chat sends         |     300 |
| Assistant start/close cycles |     100 |
| **Total**                    | **900** |

Observed behavior:

* one provider call across all duplicate chat sends;
* three expected chat messages;
* zero live Assistant sessions remaining after lifecycle completion;
* approximately **195 KiB** retained Python allocations after collection;
* approximately **562 KiB** peak Python allocations.

The stress run did not reveal a release-blocking resource or Assistant-session lifecycle leak.

---

# Test-suite warnings

Two deprecation warnings originate in FastAPI/Starlette's test compatibility layer.

These warnings:

* do not represent failed Protean tests;
* do not affect RC2 release correctness;
* are not release blockers.

They remain dependency-level maintenance observations rather than application failures.

---

# Final native Windows certification

The native Windows/Electron certification completed successfully.

| Certification metric                | Result                         |
| ----------------------------------- | ------------------------------ |
| **Result**                          | **PASS**                       |
| **Completed UTC**                   | `2026-09-17T01:44:06.4649023Z` |
| **Duration**                        | 60 minutes                     |
| **Samples**                         | 717                            |
| **Electron processes**              | 4 throughout the run           |
| **Peak working-set growth**         | 134.48 MB / 300 MB             |
| **Peak private-memory growth**      | 105.41 MB / 300 MB             |
| **Peak handles**                    | 2509                           |
| **Sampling gaps above six seconds** | None                           |
| **Failure**                         | None                           |

---

## Electron security configuration

The certified Electron runtime maintained the expected security configuration:

```text
contextIsolation=true
nodeIntegration=false
sandbox=true
```

Result:

```text
PASS
```

These values remained consistent with the release security contract.

---

## Process stability

The Electron process count remained:

```text
4 processes
```

throughout the certification run.

No unexpected process-tree growth was recorded.

---

## Memory stability

### Working-set growth

Observed peak:

```text
134.48 MB
```

Certification limit:

```text
300 MB
```

Result:

```text
PASS
```

Remaining margin:

```text
165.52 MB
```

---

### Private-memory growth

Observed peak:

```text
105.41 MB
```

Certification limit:

```text
300 MB
```

Result:

```text
PASS
```

Remaining margin:

```text
194.59 MB
```

Both monitored memory-growth metrics remained substantially below their defined release thresholds.

---

## Handle stability

Peak observed handles:

```text
2509
```

No certification failure was triggered by handle behavior during the 60-minute native run.

---

## Sampling continuity

Samples recorded:

```text
717
```

Sampling gaps above six seconds:

```text
none
```

The certification run therefore completed without abnormal monitoring gaps.

---

## Certification failure state

```text
Failure: none
```

No native Windows/Electron failure condition was recorded during the completed certification window.

---

# Certification evidence

The native Windows certification evidence is preserved in:

```text
artifacts/windows-electron-soak-20260917-024406.csv
artifacts/windows-electron-soak-20260917-024406.txt
```

The CSV contains the sampled runtime measurements from the soak.

The text artifact contains the corresponding certification summary.

These files form part of the RC2 release evidence and should remain associated with the frozen release record.

---

# Release-gate conclusion

All required RC2 release gates have now completed successfully.

The previous native-Windows certification dependency is closed.

The release has demonstrated:

* reproducible locked dependency installation;
* passing targeted regressions;
* passing complete automated tests;
* clean-environment test reproducibility;
* passing correctness lint;
* valid character and asset manifests;
* validated Windows installer/runtime contracts;
* stable duplicate-send behavior;
* correct Assistant session cleanup;
* controlled Python allocation behavior;
* successful native Electron execution;
* stable Electron process count;
* memory growth below defined certification thresholds;
* expected Electron security configuration;
* uninterrupted certification sampling;
* no recorded native certification failure.

---

# Final release decision

```text
RELEASE: Protean Workspace 0.6.1 RC2

STATUS:
FROZEN — NATIVE WINDOWS CERTIFICATION PASSED

AUTOMATED TESTS:
PASS

NATIVE WINDOWS / ELECTRON:
PASS

RELEASE GATES:
PASS

PHASE B:
MAY PROCEED
```

RC2 has passed its release gates, is frozen, and may proceed to **Phase B**.

---

## Freeze policy

From this point, `0.6.1 RC2` should be treated as a frozen release candidate.

Changes that affect:

* runtime behavior;
* dependencies;
* installer logic;
* Electron configuration;
* security boundaries;
* persistence;
* generation contracts;
* Assistant lifecycle;
* Immersion behavior;
* release assets;

should not be silently incorporated into the certified RC2 build.

Any material post-freeze change should be treated as a new release revision and should repeat the certification gates affected by that change.

---

## Final status

**Status: FROZEN — NATIVE WINDOWS CERTIFICATION PASSED**

**Date: 2026-09-17**

**RC2 has passed its release gates and may proceed to Phase B.**