# Phase 1: Complete inventory of SOMA

**Date:** 25 November 2026 · **Base commit:** `cf8e629ef0` (`main`) · **Method:** remote review via GitHub API (no local checkout)
**Purpose:** inventory of everything SOMA has today, so that the ecosystem extensions plan (SOMA-ECOSYSTEM-EXTENSIONS-AND-MCP-IMPLEMENTATION-PLAN.md) adds nothing twice. Findings are separated into **existing**, **partial**, **missing**, **suggested improvements**. Every claim names the file it comes from.

---

## 1. Baseline state

| Item | Value | Source |
|---|---|---|
| Version | `1.0.0`, one number for app and `soma` (E68) | `app/package.json`, `python/soma/__init__.py` |
| API version | `API_VERSION = 1` in `.soma/project.json` (E36) | `python/soma/__init__.py` |
| License | GPL-3.0-or-later + SOMA Model Exception | `LICENSE`, `MODEL-EXCEPTION.md` |
| App stack | Electron + TypeScript, esbuild | `app/esbuild.config.mjs`, `app/tsconfig.json` |
| Python | `requires-python >= 3.11` | `python/pyproject.toml` |
| CAD kernel | CadQuery 2.8.0, `cadquery-ocp` 7.9.3.1.1 (pinned) | `python/requirements-base.txt` |
| Branches | `main` only, not protected, 0 open PRs at review time | GitHub API |
| CI | `checks.yml` (typecheck + unit tests on PR/push), `dist.yml` (installers for 3 OS) | `.github/workflows/` |
| Local-only docs | `PLAN.md`, `DECISIONS.md`, `IDEA.md` are in `.gitignore` (present in history up to `v0.5.0`) | `CLAUDE.md` |

---

## 2. Desktop application (`app/`)

### 2.1 Main process (`app/src/main/`, 34 modules)

**Projects and files** — `projects.ts` (76 KB; `.soma` project = ZIP with Git, E79: save, open, history, export), `git.ts`, `zip.ts`, `workspace.ts`, `folders.ts` ("Open folder" as a model, E103), `files.ts`, `watcher.ts`, `storage.ts`, `dialogs.ts`.

**Build and display** — `build.ts` (prewarmed Python process for builds), `previews.ts` (previews of versions and STEP files), `measure.ts`, `dxf.ts` (E80), `drawings.ts` (document "Drawings", E97), `render.ts` + `bridge.ts` (`soma render`, E58), `animations.ts`, `about.ts` (E81), `help.ts` (E83), `updates.ts` (E98).

**Agent and skills** — `terminals.ts`, `agents.ts` (agent detection), `somaai.ts` (SOMA AI, see §6), `somaaiauth.ts` (sign-in), `voice.ts` + `voiceworker.ts` (voice input via sherpa-onnx), `skills.ts` (34 KB) + `skilllibrary.ts` (own skills, E78).

**Environment** — `packages.ts` (project env, E67), `params.ts` (parameter panel, E74), `paths.ts`, `settings.ts`, `log.ts` (`logs/soma.log`, also captures `console.*`).

### 2.2 Renderer (`app/src/renderer/`), preload, shared

Viewer: `viewer.ts`, `viewcube.ts`, `tree.ts` (E82), tools `sectiontool.ts`, `explodetool.ts`, `measuretool.ts`, `markup.ts`. Panels: `code.ts` (CodeMirror), `pdfview.ts`, `dxfview.ts`, `drawings.ts` + `drawlink.ts`, `markdown.ts`, `filetree.ts`, `versions.ts`, `fileview.ts`, `terminals.ts`, `chat.ts`, `voice.ts`, `aiparts.ts`, `params.ts`, `skills.ts`, `help.ts`, `settings.ts` + `settingspages.ts` + `aisettings.ts`, `tutorial.ts` (E94), `compact.ts`. Animation/analysis: `animtool.ts`, `animpanel.ts`, `animdata.ts`, `overlay.ts`, `resulttool.ts`, `resultview.ts`, `analysispanel.ts`, `videoview.ts`. `src/shared/`: `types.ts` (IPC contract), `somaai.ts`, `voice.ts`, `settings.ts`, `editable.ts`, `help.ts`, `skillname.ts`, `version.ts`.

### 2.3 Resources

- `resources/template/` — user project template incl. `AGENTS.md`, `CLAUDE.md`, `model.py`.
- `resources/skills/` — 21 bundled skills (§4).
- `resources/somaai/` — SOMA AI prompt additions, pi extension, model/conversation lists, pi license.
- `resources/help/` — guide images.

### 2.4 Tests (`app/test/`, 37 suites)

`smoke`, `unit`, `versions`, `editor`, `measure`, `stepview`, `cadquery`, `folder`, `groups`, `section`, `explode`, `skills`, `params`, `fasteners`, `drawing`, `drawview`, `dxf`, `animation`, `packages`, `settings`, `tutorial`, `somaai`, `aichat`, `updates`, `voice`, `buildlock`, `parmesh`, `meshexport`, `fem`, `helpshots` + harness (`harness.mjs`, `cdp.mjs`, `mockllm.mjs`). `npm test` = build + `run-all.mjs`; `SOMA_TEST_EXE` runs them against a packaged app. Suites needing the real app + Python env run locally only; CI runs typecheck + `test:unit` (`checks.yml`).

---

## 3. Python library and CLI (`python/`)

### 3.1 Library modules (`python/soma/`)

| Module | Size | Function |
|---|---|---|
| `build.py` | 18 KB | runs `model.py`, writes STEP/GLB/mapping |
| `registry.py` | 9 KB | `add_part`, `import_step`, `import_assembly`, `ascii_name`, groups, colors, roles |
| `params.py` | 13 KB | `param()` values, user panel values |
| `fasteners.py` | 40 KB | `Screw`, `Nut`, `Washer`, `HeatSetInsert`, `lengths`, `pick_length`, `standards` |
| `cqruntime.py` / `cqcompat.py` | 7 / 9 KB | CadQuery runtime and compatibility |
| `cqexport.py` | 20 KB | export model as plain CadQuery script (single file or `parts/` folder) |
| `drawing.py` | 84 KB | technical drawings, ISO 5457 frame + ISO 7200 title block → `output/drawings/<id>.pdf` + `.dxf` + `.soma/drawings/<id>.png`, combined `output/drawings.pdf` |
| `drawrun.py` | 40 KB | drawing runner |
| `fem.py` | 87 KB | meshing, loads, checks, stresses (E84) |
| `ccx.py` | 21 KB | CalculiX bridge: input file, run, read `.dat`/`.frd`; found via `SOMA_CCX`, bundled `<sys.prefix>/ccx/`, or PATH |
| `analysis.py` | 25 KB | overhang, thickness, clearance analysis |
| `anim.py` / `animrun.py` | 27 / 44 KB | `Animation` API and runner (`animations/*.py`) |
| `measure.py` | 14 KB | measuring service (face/edge IDs from GLB) |
| `mesher.py` / `meshview.py` / `parmesh.py` | 9 / 14 / 13 KB | own mesher with face/edge IDs, mesh view, parallel meshing |
| `meshexport.py` | 18 KB | `MESH_FORMATS = ("3mf", "amf", "stl", "obj", "glb", "gltf")`, units/up/detail options |
| `gltf.py` | 5 KB | GLB writing |
| `stepimport.py` | 5 KB | STEP/assembly import (`read_shape`, `read_assembly`) |
| `dxfview.py` | 12 KB | DXF for the code panel view (E80) |
| `render.py` | 8 KB | `soma render`: pictures/videos through the app, `VIEWS = (iso, front, back, left, right, top, bottom)`, `MAX_SIDE = 3840`, out `renders/<id>.mp4` |
| `env.py` | 10 KB | project environment `.soma/env` (E25/E67), `requirements.txt` tracking, `FORMAT` = 1 |
| `cli.py` | 31 KB | command line (§3.2) |
| `preview.py`, `progress.py` | small | previews, progress output |
| `data/fasteners/*` | 13 CSV + 2 docs | standard part tables from **bd_warehouse** (Apache-2.0, `LICENSE-bd_warehouse.txt`, `QUELLE.md`): screw/nut/washer/heat-set parameters, clearance & tap hole sizes, drill sizes, nominal lengths |

### 3.2 CLI (`soma …`, `python/soma/cli.py`)

| Command | Status | Purpose / outputs |
|---|---|---|
| `build` | public | runs `model.py`, writes STEP, GLB and mapping |
| `export` | public | parts or whole model; `EXPORT_FORMATS = ["step","stl","3mf","amf","brep","iges","obj","vrml","glb","gltf","dxf","svg"]`, out `exports/`; `--units`, `--up`, `--detail`, `--tolerance` for mesh formats; `--assembly` STEP with groups/names/colors |
| `cadquery` | public | export plain CadQuery script / import one (round trip) |
| `glb` | public | STEP or mesh (STL, 3MF, AMF, OBJ) → GLB (basic mode) |
| `anim` | public | build, list, describe, check animations |
| `drawing` | public | build, list, describe drawings (DXF, PDF, PNG) |
| `analyze` | public | `overhang`, `thickness`, `clearance`, `fem`, `list`; `--parts`, `--threshold`, `--up`, `--name`, `--json` |
| `render` | public | picture/video through the app, to `renders/` |
| `serve` | app-facing | measuring service (JSON lines on stdin/stdout) |
| `warm`, `env`, `dxfview` | hidden (app) | prewarmed process, project env creation, DXF view |

### 3.3 Project environment (E25/E67)

`.soma/env` per model: small venv seeing the base environment (~0.6 MB), pip redirected via `PIP_PYTHON` (`terminals.ts`), auto re-install of `requirements.txt` before build when missing (`packages.ts`, `env.py`, `INSTALL_TIMEOUT_MS = 10 min`). Never in ZIP or Git.

---

## 4. Skills (21 bundled, `app/resources/skills/`)

**Format (own):** YAML frontmatter `title`, `name`, `summary`, `order`, `category`, `default` (`always`/`on-demand`), `when`, `topics` (see `cadquery.md`).

| Category | Skills (order) |
|---|---|
| Way of working | design-workflow (1, always), cadquery — clean modeling (2, always), parametric (3, always), cadquery-scripts (7), shell-environment (8), soma-app (9) |
| Manufacturing | 3d-printing (10), resin-powder (11), cnc (12), laser (13), sheet-metal (14), plasma (15) |
| Design knowledge | tolerances (20), joints (21), standard-parts (22, always), strength (23), assemblies (24) |
| Check and present | analysis (30), animation (31), fem (32), drawings (33) |

**Own skills (E78):** `skilllibrary.ts` + `skills.ts` — create own skills, edit bundled ones, import files; `checkSkillText`, `isSkillId`, `MAX_BYTES`, `backupText`, `writeAtomic`; bundled and user skills kept separate (upgrade must not overwrite user changes). Test: `app/test/skills.mjs`.

---

## 5. Bridge (local, NOT MCP) — `app/src/main/bridge.ts`

HTTP service on **127.0.0.1**, port 0 (random), token `crypto.randomBytes(24)` per app start. Token in `SOMA_APP` / `SOMA_APP_TOKEN` env vars and `bridge.json` in app data (mode `0600`, never in project/Git). POST only, routes `/v1/*`, `MAX_BODY = 1 MB`, `timingSafeEqual` token check, 403/404/413/400 error codes. Consumer: `soma render` (`python/soma/render.py`) — used for rendering through the app window. **Confirmed: no general code-execution endpoint; not an MCP server.**

---

## 6. Agents and SOMA AI

- **Known CLI agents** (`app/src/shared/settings.ts` `KNOWN_AGENTS`): Claude Code, OpenCode, Codex, Gemini CLI — detected via `where`/`which` (`agents.ts`), version logged once per session. Other agents run in a plain terminal.
- **SOMA AI** (`somaai.ts`, `somaaiauth.ts`): bundled **pi** (`@earendil-works/pi-coding-agent` 1.6.0, MIT) in RPC mode (JSON lines stdin/stdout), one process per open model, with `@gotgenes/pi-permission-system` 42.0.2. Runs with **`--no-mcp`** (line 290 of `somaai.ts`) — MCP deliberately disabled for the internal agent today.
- **Voice:** sherpa-onnx in a utility process, speech model downloaded on first use.

**Partial:** there is no MCP server, no MCP client, and no typed tool layer anywhere in the codebase (only the `--no-mcp` flag).

---

## 7. Export/import capabilities (existing)

- 12 export formats via `soma export` (§3.2) + combined STEP assembly with groups, names, colors (`--assembly`, reference parts under "Reference").
- STEP import with structure: `import_step` (merged single shape), `import_assembly` (parts, names, colors, sub-assemblies as groups) — `registry.py`, `stepimport.py`.
- Basic mode: any STEP/mesh → GLB for viewing without code link (`soma glb`).
- CadQuery round trip: `soma cadquery` export/import.
- Drawings: DXF + PDF + PNG per sheet, ISO frame/title block.

---

## 8. Feature status summary

### 8.1 Existing (confirmed by code)

1. Parametric CadQuery modeling (`param()`, `add_part`, groups, colors, roles) — `registry.py`, `params.py`.
2. 12 export formats + assembly STEP with names/colors.
3. STEP import with structure (single + assembly).
4. 21 bundled skills + own skill library with checks/backups.
5. Project environment per model (`.soma/env`, `requirements.txt` tracking).
6. FEM with CalculiX (meshing, loads, contact, own stress computation) — `fem.py`, `ccx.py`.
7. Technical drawings (ISO frame/title block, DXF/PDF/PNG).
8. Analysis: overhang, thickness, clearance.
9. Animations + rendering (pictures/videos through the app).
10. Standard parts library (screws, nuts, washers, heat-set inserts; bd_warehouse tables).
11. Measuring service with face/edge IDs (own mesher, `mesher.py`).
12. Local bridge for `soma render` (127.0.0.1 + token).
13. CLI agent detection (4 known agents) + SOMA AI (pi, RPC mode).
14. 37 test suites + CI (typecheck/unit) + dist for 3 OS.

### 8.2 Partial

1. **MCP support** — only `--no-mcp` on SOMA AI; no server, no client, no tool schemas.
2. **External packages** — pip installs work per project, but no catalog/browser, no curated add-on library (cq_warehouse & co. not integrated).
3. **Component reuse** — `import_step`/`import_assembly` exist, but no component browser (STEP.Parts), no parametric parts catalog beyond fasteners.
4. **Geometry QA** — build checks exist in `fem.py`/`build.py`, but no dedicated BREP-validity suite, no STEP round-trip verification tool, no geometry diff/CI gate (argus-diff class).
5. **Scan/reverse engineering** — none; mesh import only for viewing/export.
6. **Skills standard** — own frontmatter only; no Agent Skills (agentskills.io) importer, no provenance/registry (source, license, SHA-256, trust levels).

### 8.3 Missing (for Phases 2–8 of the plan)

| # | Missing feature | Plan phase |
|---|---|---|
| 1 | SOMA typed MCP server (stdio, strict schemas, read-only first) | Phase 3 |
| 2 | Agent Skills standard compatibility layer + safe importer + trust registry | Phase 4 |
| 3 | cq_warehouse integration POC (isolated project) | Phase 2 |
| 4 | PartCAD POC (`pc mcp`, STEP/metadata exchange) | Phase 5 |
| 5 | Geometry QA: BREP validity, STEP round-trip, units check, volume/mass delta, interference, 4-view render check | Phase 6 |
| 6 | Draftwright specification format + parametric profile library (WPC/aluminum/…) | Phase 7 |
| 7 | Mesh2CAD POC (STL/OBJ/PLY → STEP + parametric) | P0 (plan §17) |
| 8 | STEP.Parts Component Browser (per-part license + SHA-256) | P0 (plan §17) |
| 9 | Evidence/provenance model (Measured / Reconstructed / Inferred / Designed / Unknown) | P1 (plan §16.2) |
| 10 | Open3D scan preprocessing, COLMAP photos→3D (optional modules) | P1 |
| 11 | argus-diff / geometry diff benchmark in CI | P1 |
| 12 | SALib design exploration, CAMotics, IfcOpenShell (optional, later) | P2/P3 |
| 13 | Documentation updates (MCP config examples, third-party notices for new deps) | Phase 8 |

### 8.4 Suggested improvements (small, independent of plan)

1. `soma export` could grow a `--check` flag re-importing the written STEP (foundation for Phase 6 round-trip test) — natural extension of `cmd_export` (`cli.py:112`).
2. Skill frontmatter could gain an optional `source`/`license` field early (cheap now, needed for Phase 4 importer).
3. `requirements-base.txt` pinning discipline is already good; document the `cadquery-ocp <8` constraint explicitly (plan warns about OCP 8.x breakage).

---

## 9. Dependencies and license risks

**License posture:** GPL-3.0-or-later + Model Exception (user's models/outputs freely licensed). `THIRD_PARTY_NOTICES.md` already tracks: Electron + npm packages, bundled Python runtime, native tools, assets — each with SPDX and a "GPL-3.0+ compatible" column. Fastener tables: **bd_warehouse**, Apache-2.0 (kept in `data/fasteners/` with license file). pi + permission system: MIT (`@earendil-works/pi-coding-agent`, `@gotgenes/pi-permission-system`).

**Risks before adding anything new (from plan + this review):**

| Risk | Detail | Mitigation |
|---|---|---|
| OCP version clash | `cadquery-ocp` 7.9.3.1.1 pinned; mesh2cad wants `cadquery-ocp >=7.8,<8` (OK for now) but any 8.x pull breaks CQ 2.8.0 | pin in isolated venvs only; never change base runtime in a POC |
| GPL contamination | CAMotics is GPL-2.0-or-later; SOMA is GPL-3.0+ — combination only as separate process | keep as external app, no code import |
| LGPL | IfcOpenShell LGPL-3.0-or-later | separate optional module, dynamic only |
| Unclear commercial terms | **pymoo** requires contact for profit-making use | do not bundle; use SciPy instead (plan §15.7) |
| Model weights | VGGT-class checkpoints may be CC BY-NC | license of weights ≠ license of code; never bundle NC weights |
| Big libraries | FreeCAD-library ~5 GB, CC-BY 3.0 attribution | cherry-pick only, never mirror |
| EPL plugins in solver stack | casadi wheel ships optional EPL solver plugins (noted in `THIRD_PARTY_NOTICES.md` §Notes) | already documented; keep notice updated |
| Code-execution surface | CadQuery MCP and Mesh2CAD MCP accept code/file paths | typed SOMA adapter instead; strict schemas, project-scoped paths (plan §5.2) |

---

## 10. Proposed priorities for continuation

1. **Phase 2 (next):** `cq_warehouse` isolated POC — smallest, self-contained, exercises the project-env mechanism (`packages.ts`/`env.py`) with zero base-runtime risk. Deliverable: compatibility table vs. `fasteners.py`.
2. **Phase 3:** SOMA typed MCP POC, read-only tools first (`soma_project_info`, `soma_list_parts`, `soma_list_parameters`, `soma_inspect_part`), stdio transport, on top of existing CLI (`cli.py` already has `--json` output on `analyze`).
3. **Phase 6 essentials early:** STEP round-trip check (`soma export --check`) — cheap, unlocks quality gates for everything else.
4. Then Phase 4 (Skills importer), Phase 5 (PartCAD POC), Phase 7 (Draftwright library), per plan §14.

Test strategy without local checkout: Phase 2–3 POCs run on a dedicated test branch in the fork via `workflow_dispatch` GitHub-hosted runners (temporary venv, pinned deps, artifacts = test logs + tables); nothing merges without review.
