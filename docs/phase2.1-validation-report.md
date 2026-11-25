# Phase 2.1 — Validation report: cq_warehouse 0.8.0 for SOMA

**Status: COMPLETE — all sections filled; independent review (section 6) applied.**

Scope: additional validation of `cq_warehouse` 0.8.0 (commit `a307044f91c9cc5433fde92cb1fa145c01b2bde7`,
tag v0.8.0) before any integration into SOMA, per the Phase 2.1 brief. **No integration code was
written and no SOMA source was modified** (evidence only). All tests ran on GitHub-hosted
runners in the fork `robertpezdirc12-design/SOMA`; upstream `robertpezdirc8-prog/SOMA:main`
remains at `cf8e629ef0dc1c2c54ee3fb62d50a208aa938c27`; PR #1 and PR #2 remain open Drafts.

Pinned stack everywhere: Python 3.12, `cadquery==2.8.0`, `cadquery-ocp==7.9.3.1.1`,
`cadquery-ocp-proxy==7.9.3.1.1`; cq_warehouse installed only via
`git+https://github.com/gumyr/cq_warehouse.git@a307044f91c9cc5433fde92cb1fa145c01b2bde7`.

Evidence index (fork branches / Actions runs):

| Test | Branch | Workflow run(s) | Findings |
|---|---|---|---|
| A. Geometry QA | `test/phase21-geometry` | [45719310714](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45719310714) (+3 earlier) | `phase21/sp1-geometry/findings.md` |
| B. SOMA comparison | `test/phase21-compare` | [45717603143](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45717603143) | `phase21/soma-compare/findings.md` |
| C. Project env / packages | `test/phase21-env` | [45714622726](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45714622726), [45715371639](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45715371639) | `phase21/sp2-env/findings.md` |
| D. Licenses & distribution | `test/phase21-license` | [45719557961](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45719557961) | `phase21/sp4-licenses/findings.md` |
| Windows compatibility | `test/phase21-windows` | [45718295431](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45718295431) | `phase21/sp3-windows/findings.md` |

---

## 1. Geometry QA (Test A) — COMPLETE (Specialist 1)

Evidence: `phase21/sp1-geometry/` (findings, raw JSON, source dump); authoritative run
[45719310714](https://github.com/robertpezdirc12-design/SOMA/actions/runs/45719310714).
18/18 parts created; both STEP export paths (Shape.exportStep and named cq.Assembly, XCAF
name inspection) tested per part.

**Acceptance gate (proposed for SOMA's Phase 6 QA gate):** ≥1 solid after re-import with body
count preserved, all solids `isValid()`, relative volume delta ≤ **1e-4**, bbox delta ≤
**1e-3 mm**; a zero/empty body count after re-import is always FAIL.

**Per-type results:** SocketHeadCapScrew iso4762 ✅ exact round-trip (ΔV 0.0) · HexNut iso4032
✅ exact · HeatSetNut Hilitchi ✅ within tolerance (3.27e-5/2.86e-5) · IsoThread simple=False
✅ exact (thread survives, 8 B-spline faces) · Sprocket 18t ✅ exact (110 faces) ·
**Washers (ALL 3 classes × M6/M10 = 6/6) BLOCKED** · **DeepGrooveBallBearing BLOCKED as
single solid** · other 4 bearing classes CONDITIONAL (multi-body) · IsoThread simple=True =
null shape by design (never a geometry source).

**Defect 1 — Washers (root cause PROVEN, systematic):** volume is **double-counted** —
PlainWasher M6 measured 291.3387 = exactly 2.000000× analytic 145.6694 (M10 likewise; per
review D1 the other two classes measure 1.92–1.96× the plain-ring reference because their
profiles legitimately include chamfers — the halved-profile proof covers the plain profile,
the doubled-topology signature covers all three) — NOT self-intersecting
geometry. The solid's topology contains every sub-shape twice (faces 8 raw/4 unique, wires
12/6, edges 24/6); BRepCheck: `NotConnected` + `InvalidImbricationOfShells`. Mechanism
(measured step-by-step, source-cited): cadquery `close()`→`wire()` auto-pends the profile wire
(`cq.py:2735/2345/2291`), `Washer.make_washer`'s redundant `.toPending()` (`fastener.py:2272`)
appends the same wire again → `Face.makeFromWires(w,[w])` doubles the face → doubled solid →
STEP writer collapses it, reader rebuilds **0 solids** (both paths). **Proven workaround**
(control C6): `profile.revolve()` without `toPending()` gives exactly the analytic volume and
is valid. Remediation options: use SOMA's washer, or wrapper fix; never ship the raw class.

**Defect 2 — Bearings:** `make_bearing` fuses races+rollers+caps/cage into one solid
(`bearing.py:223-262`). Fused export deforms: DeepGroove M3-10-4 → **+3.19 % volume, turns
invalid** (`BRepCheck_BadOrientationOfSubshape`); the other 4 classes round-trip exactly on
tested sizes. Named-components export is **exact** (14 separate bodies, per-component volumes
identical to 4 decimals, names survive XCAF). Conclusion: **adapters must treat bearings as
multi-body named assemblies** (components rebuilt from the class's section/roller/cap methods);
fused single-solid export blocked/gated.

**Volume tolerance — justified:** relative ΔV ≤ **1e-4**, bbox ≤ **1e-3 mm**. Analytic-surface
parts round-trip exactly (0.0); only B-spline-heavy parts drift (HeatSetNut 3.27e-5 max,
Tapered 1.44e-6, Angular 2.2e-7) → 1e-4 gives ≥3× margin over the worst observed and still
catches real loss (washer defect 1e-1–1e0, bearing 3e-2). **HeatSetNut's 2.9e-5 explicitly
PASSES** (≥3× margin); drift comes from its 80–89 knurl/thread B-spline faces (face counts and
bbox exactly preserved → surface re-representation/integration sensitivity; exact
micro-mechanism marked speculation). A stricter analytic-only sub-gate at 1e-6 is possible.

**IsoThread/Sprocket:** exact round-trips; `IsoThread(simple=True)` is a null shape by design
(`thread.py:513-517`) — 0 bodies, must never be exported.

## 2. SOMA comparison (Test B) — COMPLETE

Evidence: `phase21/soma-compare/` (script, workflow, raw `phase21-compare-results.json`).

1. **Parameter tables are identical between the libraries** (shared bd_warehouse lineage):
   `socket_head_cap_parameters.csv` M6-1 → `dk=10.22, k=6, s=5, t=3`; `plain_washer_parameters.csv`
   M6 → `iso7089: d1=6.4, d2=12, h=1.8`. (Note per review D3: `dk=10.22` is the ISO 4762
   **knurled-head maximum** — ISO 4762 gives dk 9.78–10.00 for plain heads and ≤10.22 for
   knurled heads. Both libraries build the head at 10.22, i.e. at the knurled-head limit,
   0.22 mm above the plain-head max. Cross-library equivalence unaffected.)
2. **The 18.1 % screw volume difference (M6×20, ISO 4762) is predominantly the shank, not the
   head** (per review D4: the shank explains 104.97 mm³ of the 100.55 mm³ net gap; the head
   contributes +4.43 mm³ ≈ 1 % — an edge treatment at the head top; z-slabs cannot distinguish
   an outer top-edge chamfer from a socket-mouth chamfer). Head cross-sections are identical
   between the libraries over the main slabs (82.034 mm² disc d=10.22 for z 0–3; 60.383 mm² =
   disc − hexagon s=5 for z 3–5.25 → same socket, depth 3). Decomposition (mm³): head SOMA
   421.45 / cq 425.88; shank SOMA 562.32 (smooth Ø6 cylinder — **no thread modeled**, d_eq
   5.98) / cq 457.35 (real ISO 68 thread, d_eq 5.40, 39 faces) / cq `simple=True` 379.84
   (cylinder ≈ minor diameter, d_eq 4.92). Totals: 983.77 / 883.23 / 805.72. The Phase 2
   "18.1 %" was measured against `simple=True`; against the realistic variant the difference is
   **−10.2 %** (ratio 0.8978). Timing: `simple=False` 1.5 s vs `simple=True` 0.069 s vs SOMA
   0.001 s per part. **Interpretation: modeling-fidelity difference (thread vs no thread), not
   a defect.** Practical rule: cq screws are not volume-equivalents of SOMA screws; never mix
   fidelities in BOM sums unlabeled.
3. **Washer M6 vs ISO 7089:** both libraries' shared table says `h=1.8` where ISO 7089 nominal
   is `h=1.6` (d1=6.4 ✓, d2=12 ✓). Per review D2, the ISO 7089 limits for M6 are **h 1.4–1.8**,
   so h=1.8 is **at the upper tolerance limit — in-tolerance but max-material** (+12.5 % vs
   nominal; M10 h=2.2 at the 1.8–2.2 limit likewise) — a systematic modeling choice in both
   libraries, not a data defect; document wherever washer thickness matters in fits. SOMA builds
   the table exactly (volume 145.6694 = analytic ring to 4 decimals). cq `PlainWasher` volume
   291.3387 = **exactly 2×** the correct ring (verified ratio = IEEE 2.0; the other two washer
   classes measure 1.92–1.96× the plain-ring reference — their profiles legitimately contain
   chamfers, and the halved-profile check was done on the plain profile; the duplicated-topology
   signature (raw/unique sub-shapes = 2×) and BLOCKED verdict hold for all three classes).

## 3. SOMA project environment & package mechanism (Test C) — COMPLETE

Evidence: `phase21/sp2-env/` (findings + raw logs, runs above). Mechanism citations at
`cf8e629`: `env.ensure()` (`python/soma/env.py:82`, `venv.EnvBuilder(with_pip=False)` env.py:101,
`_soma_base.pth` env.py:104–110, `base-constraints.txt` env.py:112–121); install via
`PIP_PYTHON` (`app/src/main/terminals.ts:17–24`); restore via `installMissing()`
(`app/src/main/packages.ts:161–175`); recording via `record_requirements()`
(`python/soma/env.py:165–210`, called from `build.py:368–375`).

Verified on ubuntu-latest (and on Windows by SP3): env creation via the real mechanism ✅;
git-pinned install into the project env ✅; **base runtime unchanged, no leak** ✅; `soma build`
with a cq_warehouse part ✅; env removal clean ✅.

**Findings (failures of the current mechanism, documented — NOT fixed in this phase):**

- **F1 — source/SHA lost:** `record_requirements()` writes only `cq_warehouse==0.8.0`
  (env.py:181/201/207) and never reads pip's `direct_url.json`, even though pip recorded
  `{url: …/cq_warehouse.git, vcs_info.commit_id: a307044f…}`.
- **F2 — manual pin overwritten:** a hand-written PEP 508 git line is replaced by the next
  build (env.py:203 keeps old lines only for names not installed).
- **F3 — reinstall round-trip FAILS:** after env deletion + rebuild, `cq_warehouse==0.8.0`
  cannot be restored — **`cq-warehouse` does not exist on PyPI at all** (404; `pip index
  versions` empty) → the model stops building. Even if it existed, restore would come from the
  index, not the pinned commit (silent source drift).

**Required fixes before integration (recommendation only):** (1) `record_requirements()` should
emit PEP 508 direct references `cq-warehouse @ git+https://…@<commit_id>` from
`direct_url.json` (PEP 610), falling back to `name==version`; (2) merge logic (env.py:201–204)
should prefer an existing direct reference when its commit still matches; (3) `missingLines()`
(packages.ts:139–158) should compare commit/hash for direct references; (4) optional build
warning when VCS provenance cannot be recorded. The rest of the pipeline already handles such
lines (`_parse_requirements` env.py:153–163; `parseRequirements`/`installMissing` packages.ts).

## 4. Licenses & distribution (Test D) — COMPLETE

Evidence: `phase21/sp4-licenses/` (findings + raw API captures + `license-dist-report.txt`).

- cq_warehouse 0.8.0 = **Apache-2.0** (`LICENSE` 11,358 B; `setup.cfg` classifier); no
  `install_requires`; 34 CSV data tables shipped via `package_data`.
- Table lineage: `plain_washer_parameters.csv` and `hex_nut_parameters.csv` are **byte-identical**
  to SOMA's `python/soma/data/fasteners/` copies; `socket_head_cap_parameters.csv` differs only
  because SOMA extended it (`t`/`ls` columns). Shared origin **bd_warehouse (Apache-2.0)** —
  SOMA already ships `LICENSE-bd_warehouse.txt` for this data. cq_warehouse carries no separate
  NOTICE for the CSVs.
- **Installed distribution** (git install at the pinned SHA) carries the full Apache-2.0 text in
  `cq_warehouse-0.8.0.dist-info/licenses/LICENSE`; METADATA `License` field empty (modern
  setuptools) but classifier present; pip `direct_url.json` records the exact commit. The
  distribution notice is correct for the actually installed package.
- GPL-3.0+ compatibility: Apache-2.0 is GPLv3-compatible (same convention SOMA already applies
  to cadquery/OCP in THIRD_PARTY_NOTICES.md lines 93–94). Required attribution if integrated:
  one row in THIRD_PARTY_NOTICES.md (`cq_warehouse | 0.8.0 | Apache-2.0 | … | yes`) + keep the
  dist-info license text convention; bd_warehouse lineage already covered.

## 5. Windows compatibility — COMPLETE

Evidence: `phase21/sp3-windows/` (findings + raw logs, run above; windows-latest + ubuntu
baseline job).

- Exact pins verified on Windows-2025Server (CPython 3.12.10): cadquery 2.8.0, cadquery-ocp /
  -proxy 7.9.3.1.1 (binary wheels, no compiler), cq_warehouse 0.8.0 via the **primary
  git+https pinned install** (commit provenance via `direct_url.json`).
- 9/9 parts created (whole shape and each solid) except the upstream-invalid washer and the
  no-geometry `IsoThread(simple=True)`; STEP round-trips within tolerance **for the non-bearing
  parts**; washer 1→0 solids FAIL on both platforms. Bearings: raw `sp3-results-windows.json`
  shows fused DeepGroove bearings coming out of STEP deformed and **invalid**
  (`solid_valid: [False]`, rel ΔV 3.19e-2 / 9.79e-2) — same as SP1 and Phase 2 (review D8;
  SP3's narrative sentence "the solid stays valid" and its PASS/suite-passed labels are refuted
  by its own raw JSON and superseded here). Multi-body named-component export is the required
  path (section 1).
- Cross-platform deltas (review D9): screw/nut/washer/sprocket ~1e-16/0.0; HeatSetNut 1.8e-12;
  bearing family ~4e-8; IsoThread 7.3e-6 — relevant for byte-wise cross-OS shape caching.
  Run-to-run reproducibility was not measured (one run per script per OS; Python patch levels
  3.12.10 vs 3.12.16) — platform effect vs run noise cannot be fully separated.
- SOMA project-env mechanism works end-to-end on Windows (`.soma\env` with `Scripts\python.exe`,
  `pip.ini`, path-with-spaces project OK). No Windows-specific defects found.
- Note: the Phase 2 brief's "HexNut 246.4 mm³" baseline figure is stale; authoritative value
  **302.298 mm³**. Per review D10: Phase 2's POC label "HeatSetNut(M3-0.5-8)" actually measured
  **M6-1-10** (97.053 mm³, 8×8×10 — matches SP3's M6-1-10 exactly); the real Hilitchi M3-0.5-8
  is 58.12 mm³, 5×5×8 (SP1). Phase 2's `PlainWasher(M6-1)` call string is impossible (raises
  ValueError); the value was produced with size `M6`. Measurements themselves are consistent.

## 6. Independent review — COMPLETE (Specialist 4)

Evidence: `phase21/sp4-review/findings.md` (adversarial review; raw numbers recomputed from all
five raw datasets; upstream CSV independently re-fetched, git blob SHA matched).

**Verified (recomputed):** washer mechanism and the PlainWasher exact-2× numbers (IEEE 2.0);
tolerance arithmetic (1e-4 = 3.06× margin over max passing 3.269e-5); Test B decomposition sums
and ratios; SP2 F1–F3 against the real `env.py`/`packages.ts` code and the PEP 508 fix pattern;
Apache-2.0 verdict + installed-dist evidence + CSV byte-identity (blob SHA `55390e9b4da2…`);
HexNut 302.298 correction.

**Disputed / overstated — corrections adopted in this report (D1–D12, full list in the review):**
D1 washer "exactly 2×" applies to PlainWasher only (others 1.92–1.96× plain-ring reference) ·
D2 ISO 7089 h=1.8 is at the upper tolerance limit (1.4–1.8), in-tolerance max-material — NOT
"outside ±0.14" · D3 `dk=10.22` is the ISO 4762 knurled-head max · D4 "predominantly the shank"
(head +4.43 mm³) · D5 −10.2 % · D6 timing comparison clarified · D7 "exact" round-trips are
≤1e-13 machine noise in other measurement codes · D8 SP3 bearing PASS labels refuted by its own
raw JSON (superseded here) · D9 heatset cross-platform 1.8e-12, not ~1e-16 · D10 Phase 2 heatset
label was M6-1-10, not M3-0.5-8 · D11 face-counter convention (SP1's raw-vs-unique is
authoritative) · D12 Phase 2's `all_valid: true` on the zero-solid washer round-trip is the
vacuous-`all([])` failure mode — no automation may consume that flag.

**Caveats required in this report (review §c):** tolerance gate rests on effectively 10 distinct
part measurements over 6 families (1–2 sizes each) — untested sizes could drift more; the
1e-3 mm bbox tolerance is a chosen round bound (observed deltas ≤4.4e-14), not empirically
anchored; all SAFE verdicts are limited to the tested type×size (e.g. HexNut = iso4032 M6-1
only; SocketHeadCapScrew = iso4762 M6-1×20 only; 11 other head classes untested); bearing
"tangential contact" explanation is an observation over n=5 (speculation marker kept); SP2's
fixes were code-inspected, not executed end-to-end (and `git+https` restore needs git + network
on the target machine); IsoThread drift micro-mechanism unproven (speculation kept); license
statements are practice guidance, not legal advice (Apache-2.0 has no NOTICE file to carry —
obligations are license-text + copyright retention + change statements).

**Reviewer's verdict recommendation: (2) integration makes sense — with specific fixes** —
adopted as section 9.

## 7. Safe / blocked function lists (per SP1 + review; **all verdicts limited to tested
type × size** — e.g. HexNut iso4032 M6-1 only, SocketHeadCapScrew iso4762 M6-1×20 only,
IsoThread M6×10, Sprocket 18t, HeatSetNut Hilitchi M3-0.5-8/M6-1-10; untested types (11 other
head classes, iso4033/4035/…) not covered)

- **SAFE as-is:** `SocketHeadCapScrew` (iso4762) , `HexNut` (iso4032), `IsoThread(simple=False)`,
  `Sprocket` — exact STEP round-trips; `HeatSetNut` (Hilitchi) — SAFE within the 1e-4 volume
  tolerance (expect 2.9–3.3e-5 drift).
- **BLOCKED:** `PlainWasher`, `ChamferedWasher`, `CheeseHeadWasher` (all tested sizes) — invalid
  solid, exactly 2× volume, zero-body STEP loss; use SOMA's washer or the proven wrapper fix.
  `IsoThread(simple=True)` — null shape by design, never a geometry source.
  `SingleRowDeepGrooveBallBearing` as a single solid — deforms +3.19 % and turns invalid through
  STEP; SAFE only as named multi-body.
- **CONDITIONAL:** `CappedDeepGroove`/`AngularContact`/`CylindricalRoller`/`TaperedRoller`
  bearings — wrap as multi-body named assemblies (fused form passed on tested sizes but is
  proven non-robust).
- **Fidelity caveat (Test B):** cq screws are not volume-equivalents of SOMA screws (thread vs
  no thread); never mix fidelities in BOM sums unlabeled.
- **Mechanism prerequisite:** any integration must ship the section 3 fix (PEP 508 direct
  reference recording), otherwise project env rebuilds cannot restore the package at all.
- The creation + validity + STEP round-trip gate must run on **every** generated part regardless
  of class (the library ships invalid geometry silently).

## 8. Exact changes needed before integration (so far)

1. `record_requirements()` + merge/missing-lines fixes (section 3, F1–F3) — documented, not
   implemented.
2. Adapter gate: validity + STEP round-trip check per produced part (0 bodies = failure).
3. `PlainWasher`/washer classes: block raw classes; use SOMA washer or wrapper fix
   (`profile.revolve()` without `toPending()` — proven exact).
4. Bearings: rebuild components and export as named multi-body assemblies (fused single-solid
   export blocked).
5. Size-vocabulary mapping in the adapter: SOMA/cq call strings like `M6-1` do not exist in
   cq_warehouse washer sizes (`PlainWasher.sizes("iso7089")` returns `M6`, `M10`, …) — map or
   validate the size strings (review caveat 8).
6. THIRD_PARTY_NOTICES.md row including the pinned commit SHA
   `a307044f91c9cc5433fde92cb1fa145c01b2bde7` (review caveat 7; bd_warehouse table lineage
   already covered by `LICENSE-bd_warehouse.txt`).
5. THIRD_PARTY_NOTICES.md entry (section 4).
6. Document the ISO 7089 h=1.8 vs 1.6 table deviation (both libraries) wherever washer
   thickness matters.

## 9. Verdict: **(2) integration makes sense — with specific fixes**

- **Not (1) safe/ready:** three hard blockers as measured — the entire washer family ships
  invalid geometry that vanishes in STEP; the fused DeepGroove bearing export deforms and turns
  invalid; and SOMA's `record_requirements()` cannot restore cq_warehouse at all on a fresh
  machine (no PyPI project) while silently losing the source provenance.
- **Not (3) not recommended:** the library's core value (screws, nuts, real threads, sprocket,
  heat-set inserts, 4/5 bearings as multi-body) passes a strict validity + STEP round-trip gate
  on Linux **and** Windows; every defect is root-caused to source level with a *proven*
  workaround; licensing is clean and attribution cheap; the env fix is in SOMA's code with its
  correct pattern identified.
- **Hard prerequisites (all documented, none implemented — correct for this phase):**
  1. `record_requirements()` PEP 508 direct-reference fix + merge/missing-lines commit
     comparison (SP2 F1–F3) — otherwise the package cannot be restored anywhere;
  2. block all washer classes as-is (use SOMA washer or the proven wrapper fix);
  3. bearings as named multi-body assemblies, never fused single solids;
  4. mandatory per-part gate: ≥1 solid after re-import with body count preserved, all solids
     `isValid()`, ΔV ≤ 1e-4 (analytic-only sub-gate 1e-6 optional), bbox ≤ 1e-3 mm — **zero
     bodies always FAIL** (no vacuous `all([])` flags);
  5. `IsoThread(simple=True)` never reaches export;
  6. adopt the D1–D12 corrections (two were wrong standard-conformance claims);
  7. size-vocabulary mapping + THIRD_PARTY_NOTICES entry with pinned SHA.

With those in place the residual risk is ordinary (untested sizes/types — mitigated by running
the gate on every generated part = the Phase 6 QA gate).

**Evidence-lifecycle note:** all test branches (`test/phase21-*`, `test/phase2-cqwarehouse`,
`test/phase1-checks`) and their temporary workflows are disposable and should be deleted when
the phase is closed.
