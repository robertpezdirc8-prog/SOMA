# Phase 2: cq_warehouse POC — isolated proof of concept

**Date:** 25 November 2026 · **Method:** isolated GitHub-hosted runner (temporary test branch `test/phase2-cqwarehouse` in the fork), no local checkout, no changes to SOMA code
**Tested:** `gumyr/cq_warehouse` **v0.8.0** (Apache-2.0) on SOMA's pinned stack · **Runs:** [45709166909](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45709166909), [45709469808](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45709469808) (final) · **Raw data:** `phase2-results.json` (artifact) · **Test script:** `poc/phase2_poc.py` on the test branch

**Verdict: POC successful with two geometry caveats. Integration is worthwhile — but as an optional project package with a SOMA adapter, keeping `soma.fasteners` as the primary API.**

---

## 1. Compatibility with SOMA's stack — PASS

| Check | Result |
|---|---|
| cadquery 2.8.0 (SOMA pin) | ✅ works, no version conflict |
| cadquery-ocp 7.9.3.1.1 (SOMA pin) | ✅ works, OCP untouched |
| cq_warehouse `install_requires` | **empty** (`setup.cfg`) — pulls no transitive deps, cannot break SOMA's pins |
| Python 3.12 | ✅ (`python_requires >=3.9`) |
| Installed size | **0.92 MB** (pure Python + CSV tables) |
| Import cost | `cq_warehouse.fastener` 0.007 s, `.bearing` 0.002 s (after `cadquery` import 1.5 s which SOMA already pays) |
| License | Apache-2.0 — GPL-3.0+ compatible; its CSV tables share the **bd_warehouse** origin SOMA already documents in `THIRD_PARTY_NOTICES.md` |

No install conflicts, no OCP 8.x risk (that risk exists only for `mesh2cad`, not here — cq_warehouse has no OCP pin of its own).

## 2. Available standard parts (runtime inventory)

| Family | Classes | Types | Notes |
|---|---|---|---|
| Screws | **12** (Socket/Hex/HexFlange/Button/ButtonCollar/Cheese/RaisedCheese/CounterSunk/RaisedCounterSunk/Pan/PanCollar/SetScrew) | metric ISO + imperial `asme_b18.3` | sizes `M1.6-0.35` … `M20-2.5` |
| Nuts | **7** (Hex, HexFlange, UnchamferedHex, Square, DomedCap, BradTee, HeatSet) | iso4032/4033/4035 + imperial | |
| Washers | **3** (Plain, Chamfered, CheeseHead) | iso7089/7091/7093/7094 | ⚠️ PlainWasher geometry broken, see §5 |
| Bearings | **5** (DeepGroove, CappedDeepGroove, AngularContact, CylindricalRoller, TaperedRoller) | size `M3-10-4` … `M10-35-11` | **SOMA has no bearings at all** |
| Threads | **4** (IsoThread, Acme, MetricTrapezoidal, PlasticBottle) | real helical threads | SOMA screws are thread-less by design |
| Drive | Sprocket + Chain | bicycle-chain defaults | none in SOMA |

## 3. Parametric creation — 8/8 PASS

All parts are generated on demand from CSV parameter tables (same data style as SOMA's `data/fasteners/`):

| Test | Time | Volume | BBox | Valid |
|---|---|---|---|---|
| `SocketHeadCapScrew(M6-1, 20.0)` (iso4762) | 0.05 s | 805.72 mm³ | 10.22×10.22×26 | ✅ |
| `HexNut(M6-1)` (iso4032) | 0.05 s | 302.30 mm³ | 11.55×10×5.2 | ✅ |
| `PlainWasher(M6-1)` (iso7089) | 0.005 s | 291.34 mm³ | 12×12×1.8 | ❌ **invalid solid** |
| `HeatSetNut(M3-0.5-8)` (Hilitchi) | 0.36 s | 97.05 mm³ | 8×8×10 | ✅ |
| `SingleRowDeepGrooveBallBearing(M3-10-4)` | 0.65 s | 253.38 mm³ | 13×13×3.5 | ✅ (Compound) |
| `IsoThread(M6×10, simple=True)` | ~0 s | calculation only (by design) | — | — |
| `IsoThread(M6×10, simple=False)` real thread | 0.07 s | solid | ✅ | ✅ |
| `Sprocket(num_teeth=18)` | 0.76 s | solid | ✅ | ✅ |

Generation is fast (0.005–0.8 s/part), total POC run **5.8 s** including everything.

## 4. Assembly + STEP export and re-import

**Assembly export** (`cq.Assembly`, 5 parts with names, colors, locations → STEP, 2.39 MB) works; export 0.064 s, re-import 0.234 s.

**Per-part round-trip** (export → `importStep` → compare):

| Part | Δ volume (rel) | Solids out | Valid after | Verdict |
|---|---|---|---|---|
| Screw | 1.0e-13 | 1 | ✅ | **perfect** |
| Nut | 1.5e-11 | 1 | ✅ | **perfect** |
| **Washer** | **1.0 (all lost)** | **0** | — | ❌ **broken: invalid source solid exports as nothing** |
| HeatSetNut | 2.9e-5 | 1 | ✅ | ✅ within tolerance |
| **Bearing** | **9.8e-2** | 1 (was Compound) | ❌ | ⚠️ compound (races + balls) degrades on round-trip |

## 5. Geometry validity — two real defects found

1. **`PlainWasher` creates an invalid solid** (`isValid() == False`) and it **disappears in STEP export** (0 solids re-imported). The reported volume (291 mm³) is also implausible for an ISO 7089 M6 washer (~130 mm³ expected; SOMA's own washer computes 145.7 mm³ with the same 12×12×1.8 bbox). The washer profile construction in `fastener.py:2302` is defective at least for iso7089/M6. **Impact for SOMA: never trust cq_warehouse parts without an `isValid()` + round-trip gate.** SOMA's own `Washer` covers iso7089/7091/7093 and is sound.
2. **Bearing STEP round-trip changes geometry** (+9.8% volume, becomes invalid). The bearing is a multi-solid Compound; STEP handling of the compound/interferences between races and balls is lossy. Usable for visualization/BOM; for export-critical assemblies re-check after write.

## 6. Comparison with SOMA `fasteners.py` (same runner, same env)

| Aspect | SOMA `soma.fasteners` | cq_warehouse v0.8.0 |
|---|---|---|
| Screw standards | 7 (ISO 4762/7380/10642/4017/4014, DIN 931, ISO 4026) | 12 head classes, ISO + **imperial** |
| Nut / washer standards | 4 / 3 | 7 / 3 (⚠️ PlainWasher invalid) |
| Heat-set inserts | **5 brands** (ruthex, CNCKitchen, Hilitchi, McMaster-Carr, AE-SamZhihui) | 2 (Hilitchi, McMaster-Carr) |
| Bearings / threads / sprockets | none | **5 / 4 / 2 classes** |
| Placement API | ✅ `at`, `direction`, `on`, `sunk`, `angle`, `check_length`; seats on real faces (`_surface_hit`) | ❌ none (raw solids) |
| Hole tables | ✅ ISO 273 clearance (`fine/medium/coarse`), tap drills, drill sizes | ✅ same CSV family, not exposed as helpers |
| STEP naming | ✅ ASCII-safe names, groups, roles ("hardware"), colors | generic |
| Thread-less model | ✅ deliberate (fast, robust `cut()`) | `simple=True` default, optional real threads |
| Like-for-like M6×20 socket screw | 983.8 mm³, bbox 10.22×10.22×26 | 805.7 mm³, **identical bbox** — same dimensions, ~18% less volume (deeper socket recess / no thread relief) |
| Creation time | ~0.001 s | 0.05 s |

**Both libraries agree on outer dimensions** (bbox identical to 0.01 mm), so parts are dimensionally interchangeable; the volume difference is internal detail (socket recess modelling). SOMA's placement API and hole helpers are a superset cq_warehouse lacks; cq_warehouse's bearings/threads/drive parts are a superset SOMA lacks. **They complement each other — there is little redundancy worth removing.**

## 7. Verdict: is integration sensible?

**Yes, conditionally — for exactly the gaps it fills:**

Worth taking:
- **Bearings (5 classes)** — no SOMA equivalent; useful for shaft/gearbox models.
- **Real threads** (`IsoThread`, trapezoidal, Acme) — for renders and thread-critical parts where SOMA's thread-less simplification is not enough.
- **Extra screw/nut head types + imperial sizes** — extends catalog coverage.
- **Sprocket + Chain** — niche but free.

Do **not** replace `soma.fasteners`:
- SOMA's placement API (`at`/`on`/`sunk`), hole tables, 5 heat-set brands, ASCII STEP naming, roles/colors and the `cqexport.py` embedded-table export are production-critical and have no cq_warehouse equivalent.
- cq_warehouse's PlainWasher is geometrically broken; bearing round-trip is lossy.

Risks and mitigations:
- Geometry defects (§5) → **mandatory validity + STEP round-trip gate** on any part before it enters a model (this doubles as the Phase 6 QA gate).
- Upstream is a one-maintainer project (last release v0.8.0, tag activity to 16 Oct 2026) → vendor the exact version, never float.
- API mismatch (raw solids vs SOMA `_Part`) → adapter layer (§8), no direct user-facing exposure.

## 8. Proposed integration architecture (awaits approval — not implemented)

```
model.py
   │
   ├─ soma.fasteners        (unchanged, primary API)
   │
   └─ soma.ext.cqwarehouse  (NEW thin adapter, optional)
         │  wraps cq_warehouse parts with SOMA placement:
         │  Screw(standard, size, length, at=, on=, sunk=, ...) → _Part-compatible
         │  validates: isValid(), STEP round-trip, volume sanity
         │  registers via add_part(..., role="hardware", color=STEEL)
         ▼
   project env .soma/env (E67)     ← cq_warehouse installed HERE only,
         │                            listed in requirements.txt, never in
         ▼                            the base runtime (plan §1.3 rule)
   cq_warehouse 0.8.0 (Apache-2.0, vendored pin)
```

Concrete steps when approved:
1. **`soma.ext.cqwarehouse`** module (~200 lines): mapping SOMA-style calls to cq_warehouse classes; every part passes `isValid()` + bbox sanity + STEP write/read check before registration; failed parts raise a clear error naming the defect (e.g. "cq_warehouse PlainWasher is invalid — use Washer ISO 7089 from soma.fasteners").
2. **Feature map in the adapter:** `Bearing(608ZZ-style size)` → `SingleRowDeepGrooveBallBearing`; `Thread(iso, d, pitch, length)` → `IsoThread`; screws map 1:1 where standards overlap (ISO 4762/7380/10642/4017/4026…), new head types get new names in the SOMA catalog.
3. **Distribution:** project-level opt-in — `soma install cq-warehouse==0.8.0` style via the existing `packages.ts`/`env.py` requirements mechanism; `cqexport.py` gets an exclusion so exported CadQuery scripts don't silently depend on it (or embed a fallback import notice).
4. **Licensing:** add cq_warehouse to `THIRD_PARTY_NOTICES.md` (Apache-2.0, upstream URL, version, SHA of the vendored copy); note shared bd_warehouse data lineage already documented.
5. **Tests (in `app/test/` style):** adapter mapping tests, validity-gate regression (the washer defect must keep failing loudly), STEP round-trip test per part class — this is the first concrete instance of the Phase 6 geometry QA.
6. **Not in this step:** no MCP exposure yet (Phase 3 tools `soma_list_available_packages` / `soma_install_project_package` in the plan §5.1 fit later).

## 9. Reproducibility

- Workflow: `.github/workflows/phase2-poc.yml` on `test/phase2-cqwarehouse` (push-triggered, temporary; delete branch when the phase closes).
- Script: `poc/phase2_poc.py` — environment report, inventory, 8 creation tests, per-part + assembly STEP round-trip, SOMA comparison, timings.
- Runs: [45709469808](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45709469808) (final, success), artifact `phase2-results.json`.
- Pinned: `cadquery==2.8.0`, `cadquery-ocp==7.9.3.1.1`, `cq_warehouse @ v0.8.0` (git tag), Python 3.12, ubuntu-latest.
