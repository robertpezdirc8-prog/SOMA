#!/usr/bin/env python3
"""Phase 2 POC: cq_warehouse 0.8.0 on SOMA's pinned stack (cadquery 2.8.0,
cadquery-ocp 7.9.3.1.1), side by side with SOMA's own fastener library.

Runs only on a temporary GitHub-hosted runner. Nothing here changes SOMA.
Writes phase2-results.json and prints a markdown summary.

Covers the agreed questions:
  1. available standard parts      5. geometry validity
  2. parametric creation           6. dependencies / size / performance
  3. assembly of components        7. compatibility with CQ 2.8.0 / OCP 7.9.3.1.1
  4. STEP export + re-import       (+ comparison with SOMA fasteners.py)
"""
import importlib.util
import inspect
import json
import platform
import sys
import time
import traceback
from pathlib import Path

RESULTS = {"env": {}, "inventory": {}, "tests": [], "roundtrip": {}, "soma": {}, "timings": {}}


# --- helpers -------------------------------------------------------------------------------

def part_stats(obj):
    sh = obj.val() if hasattr(obj, "val") else obj
    try:
        bb = sh.BoundingBox()
        bbox = [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)]
    except Exception as e:
        bbox = f"n/a ({type(e).__name__})"
    try:
        vol = round(sh.Volume(), 3)
    except Exception:
        vol = None
    try:
        valid = bool(sh.isValid())
    except Exception:
        valid = None
    return {"volume_mm3": vol, "bbox_mm": bbox, "valid": valid}


def pick_type(cls, prefer=("iso", "din")):
    """Prefer metric ISO/DIN fastener types (sets sort imperial 'asme' first)."""
    types = sorted(cls.types())
    for p in prefer:
        for t in types:
            if p in t.lower():
                return t, types
    return (types[0] if types else None), types


def try_variants(name, variants):
    """Try (label, callable) variants; record each attempt, return the first success."""
    for label, thunk in variants:
        t0 = time.perf_counter()
        try:
            out = thunk()
            dt = round(time.perf_counter() - t0, 3)
            RESULTS["tests"].append({"name": name, "variant": label, "ok": True, "seconds": dt})
            print(f"OK   {name} [{label}] {dt}s")
            return out
        except Exception as e:
            dt = round(time.perf_counter() - t0, 3)
            RESULTS["tests"].append(
                {"name": name, "variant": label, "ok": False, "seconds": dt,
                 "error": f"{type(e).__name__}: {e}"})
            print(f"FAIL {name} [{label}] {type(e).__name__}: {e}")
    return None


def first_sizes(cls, fastener_type, prefer="M6"):
    sizes = sorted(cls.sizes(fastener_type))
    for s in sizes:
        if s.startswith(prefer):
            return s, sizes
    for s in sizes:
        if s.startswith("M"):
            return s, sizes
    return (sizes[0] if sizes else None), sizes


# --- 0. environment ------------------------------------------------------------------------

def env_info():
    import importlib.metadata as md
    e = {"python": sys.version.split()[0], "platform": platform.platform()}
    for pkg in ("cadquery", "cadquery-ocp", "cadquery-ocp-proxy", "cq-warehouse", "multimethod", "ezdxf", "numpy"):
        try:
            e[pkg] = md.version(pkg)
        except Exception:
            e[pkg] = "not installed"
    RESULTS["env"] = e
    print("## Environment\n", json.dumps(e, indent=2))


def import_timings():
    for mod in ("cadquery", "cq_warehouse.fastener", "cq_warehouse.bearing", "cq_warehouse.thread"):
        t0 = time.perf_counter()
        try:
            __import__(mod)
            RESULTS["timings"][f"import {mod}"] = round(time.perf_counter() - t0, 3)
        except Exception as e:
            RESULTS["timings"][f"import {mod}"] = f"FAIL {e}"


def package_size():
    import importlib.metadata as md
    total = 0
    try:
        root = Path(md.distribution("cq-warehouse").locate_file("cq_warehouse"))
        for f in root.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        RESULTS["env"]["cq_warehouse_installed_bytes"] = total
        RESULTS["env"]["cq_warehouse_installed_mb"] = round(total / 1e6, 2)
    except Exception as e:
        RESULTS["env"]["cq_warehouse_installed_bytes"] = f"FAIL {e}"


# --- 1. inventory --------------------------------------------------------------------------

def inventory():
    from cq_warehouse.fastener import Screw, Nut, Washer
    from cq_warehouse.bearing import Bearing
    inv = {}
    for label, base in (("screws", Screw), ("nuts", Nut), ("washers", Washer), ("bearings", Bearing)):
        classes = {}
        for cls in base.__subclasses__():
            entry = {}
            for t in sorted(cls.types()):
                try:
                    entry[t] = len(cls.sizes(t))
                except Exception:
                    entry[t] = "?"
            classes[cls.__name__] = entry
        inv[label] = classes
    try:
        from cq_warehouse.thread import IsoThread, AcmeThread, MetricTrapezoidalThread, PlasticBottleThread
        inv["threads"] = ["IsoThread", "AcmeThread", "MetricTrapezoidalThread", "PlasticBottleThread"]
    except Exception as e:
        inv["threads"] = f"FAIL {e}"
    try:
        from cq_warehouse.sprocket import Sprocket
        from cq_warehouse.chain import Chain
        inv["drive"] = ["Sprocket", "Chain"]
    except Exception as e:
        inv["drive"] = f"FAIL {e}"
    RESULTS["inventory"] = inv
    counts = {k: (sum(len(v) if isinstance(n, int) else 1 for n in v.values()) if isinstance(v, dict) else len(v))
              for k, v in inv.items()}
    print("## cq_warehouse inventory (type-count per class)\n", json.dumps(counts, indent=2))


# --- 2. parametric creation -----------------------------------------------------------------

def creation_tests():
    from cq_warehouse.fastener import (SocketHeadCapScrew, HexNut, PlainWasher, HeatSetNut)
    from cq_warehouse.bearing import SingleRowDeepGrooveBallBearing

    def variants_for(cls, size, lengths):
        v = []
        params = inspect.signature(cls.__init__).parameters
        t, _ = pick_type(cls)
        for length in lengths:
            kw = {"size": size}
            if "length" in params:
                kw["length"] = length
            if "fastener_type" in params and t:
                kw["fastener_type"] = t
            if "simple" in params:
                kw["simple"] = True
            v.append((f"{cls.__name__}({size}, {length})", lambda kw=kw, cls=cls: cls(**kw)))
        return v

    parts = {}
    # screw
    screw_cls = SocketHeadCapScrew
    t, screw_types = pick_type(screw_cls)
    size, sizes = first_sizes(screw_cls, t)
    RESULTS.setdefault("inventory", {})["socket_head_cap_types"] = screw_types
    RESULTS["inventory"]["socket_head_cap_sizes_sample"] = sizes[:8]
    screw = try_variants("create SocketHeadCapScrew", variants_for(screw_cls, size, [20.0, 16.0, 12.0, 10.0]))
    if screw is not None:
        parts["screw"] = screw
        RESULTS["tests"][-1]["stats"] = part_stats(screw)

    # nut
    nut_cls = HexNut
    t, nut_types = pick_type(nut_cls)
    size, sizes = first_sizes(nut_cls, t)
    RESULTS["inventory"]["hex_nut_types"] = nut_types
    RESULTS["inventory"]["hex_nut_sizes_sample"] = sizes[:8]
    nut = try_variants("create HexNut", variants_for(nut_cls, size, [None]) if "length" not in inspect.signature(nut_cls.__init__).parameters else [])
    if nut is None:
        params = inspect.signature(nut_cls.__init__).parameters
        kw = {"size": size}
        if "fastener_type" in params:
            kw["fastener_type"] = t
        if "simple" in params:
            kw["simple"] = True
        nut = try_variants("create HexNut", [("direct", lambda: nut_cls(**kw))])
    if nut is not None:
        parts["nut"] = nut
        RESULTS["tests"][-1]["stats"] = part_stats(nut)

    # washer
    wash_cls = PlainWasher
    t, wash_types = pick_type(wash_cls)
    size, sizes = first_sizes(wash_cls, t)
    RESULTS["inventory"]["plain_washer_types"] = wash_types
    params = inspect.signature(wash_cls.__init__).parameters
    kw = {"size": size}
    if "fastener_type" in params:
        kw["fastener_type"] = t
    if "simple" in params:
        kw["simple"] = True
    washer = try_variants("create PlainWasher", [("direct", lambda: wash_cls(**kw))])
    if washer is not None:
        parts["washer"] = washer
        RESULTS["tests"][-1]["stats"] = part_stats(washer)

    # heat-set insert
    hs_cls = HeatSetNut
    try:
        t, hs_types = pick_type(hs_cls)
        size, sizes = first_sizes(hs_cls, t)
        RESULTS["inventory"]["heatset_types"] = hs_types
        RESULTS["inventory"]["heatset_sizes_sample"] = sizes[:8]
    except Exception:
        t, size = None, None
    if size:
        params = inspect.signature(hs_cls.__init__).parameters
        kw = {"size": size}
        if "fastener_type" in params and t:
            kw["fastener_type"] = t
        if "simple" in params:
            kw["simple"] = True
        hs = try_variants("create HeatSetNut", [("direct", lambda: hs_cls(**kw))])
        if hs is not None:
            parts["heatset"] = hs
            RESULTS["tests"][-1]["stats"] = part_stats(hs)

    # bearing
    b_cls = SingleRowDeepGrooveBallBearing
    try:
        b_types = sorted(b_cls.types())
        t = b_types[0]
        size, sizes = first_sizes(b_cls, t, prefer="M6")
        if not str(size).startswith("M"):
            size = next((s for s in sizes if s.startswith("M")), size)
        RESULTS["inventory"]["bearing_types"] = b_types
        RESULTS["inventory"]["bearing_sizes_sample"] = sizes[:8]
        bearing = try_variants("create SingleRowDeepGrooveBallBearing",
                               [("direct", lambda: b_cls(size=size, bearing_type=t))])
        if bearing is not None:
            parts["bearing"] = bearing
            RESULTS["tests"][-1]["stats"] = part_stats(bearing)
    except Exception:
        traceback.print_exc()

    return parts


def thread_tests():
    from cq_warehouse.thread import IsoThread
    out = {}
    th = try_variants("create IsoThread simple=True (calculation only, no solid)",
                      [("M6x10 simple", lambda: IsoThread(major_diameter=6.0, pitch=1.0, length=10.0,
                                                          external=True, simple=True))])
    if th is not None:
        out["simple"] = part_stats(th)  # expected: no bounding box (documented behaviour)
    th2 = try_variants("create IsoThread simple=False (real thread)",
                       [("M6x10 threaded", lambda: IsoThread(major_diameter=6.0, pitch=1.0, length=10.0,
                                                             external=True, simple=False))])
    if th2 is not None:
        out["threaded"] = part_stats(th2)
    return out


def sprocket_test():
    from cq_warehouse.sprocket import Sprocket
    sp = try_variants("create Sprocket (bicycle-chain defaults)",
                      [("18 teeth", lambda: Sprocket(num_teeth=18))])
    return part_stats(sp) if sp is not None else None


# --- 3 + 4. assembly and STEP round-trip ---------------------------------------------------

def roundtrip(parts):
    import cadquery as cq
    if not parts:
        RESULTS["roundtrip"] = "skipped: no parts created"
        return

    step = "poc_assembly.step"

    # per-part round-trip: catches which part changes
    per_part = {}
    for name, p in parts.items():
        sh = p.val() if hasattr(p, "val") else p
        v0 = sh.Volume()
        try:
            a = cq.Assembly()
            a.add(sh, name=name, color=cq.Color(0.8, 0.8, 0.8, 1.0))
            if hasattr(a, "export"):
                a.export(f"poc_{name}.step")
            else:
                a.save(f"poc_{name}.step")
            wp = cq.importers.importStep(f"poc_{name}.step")
            solids = wp.solids().vals()
            v1 = sum(s.Volume() for s in solids)
            per_part[name] = {
                "volume_before": round(v0, 3),
                "volume_after": round(v1, 3),
                "rel_delta": f"{abs(v1 - v0) / v0:.2e}" if v0 else None,
                "solids_out": len(solids),
                "all_valid": all(s.isValid() for s in solids),
            }
        except Exception as e:
            per_part[name] = {"error": f"{type(e).__name__}: {e}"}
    RESULTS["roundtrip_per_part"] = per_part

    try:
        from cq_warehouse.bearing import SingleRowDeepGrooveBallBearing
    except Exception:
        pass

    a = cq.Assembly()
    before_vol = 0.0
    for i, (name, p) in enumerate(parts.items()):
        sh = p.val() if hasattr(p, "val") else p
        before_vol += sh.Volume()
        a.add(sh, name=name, loc=cq.Location(cq.Vector(60 * i, 0, 0)),
              color=cq.Color(0.8, 0.8, 0.8, 1.0))
    t0 = time.perf_counter()
    try:
        if hasattr(a, "export"):
            a.export(step)
        else:
            a.save(step)
        RESULTS["roundtrip"]["export_seconds"] = round(time.perf_counter() - t0, 3)
        RESULTS["roundtrip"]["step_bytes"] = Path(step).stat().st_size
    except Exception as e:
        RESULTS["roundtrip"] = f"export FAIL {type(e).__name__}: {e}"
        traceback.print_exc()
        return

    t0 = time.perf_counter()
    wp = cq.importers.importStep(step)
    RESULTS["roundtrip"]["import_seconds"] = round(time.perf_counter() - t0, 3)
    solids = wp.solids().vals()
    after_vol = sum(s.Volume() for s in solids)
    invalid = [i for i, s in enumerate(solids) if not s.isValid()]
    bb = wp.val().BoundingBox() if hasattr(wp.val(), "BoundingBox") else None
    rel = abs(after_vol - before_vol) / before_vol if before_vol else None
    RESULTS["roundtrip"].update({
        "parts_in": len(parts),
        "solids_out": len(solids),
        "invalid_solid_indices": invalid,
        "volume_before_mm3": round(before_vol, 3),
        "volume_after_mm3": round(after_vol, 3),
        "volume_rel_delta": f"{rel:.2e}" if rel is not None else None,
        "bbox_after_mm": [round(bb.xlen, 3), round(bb.ylen, 3), round(bb.zlen, 3)] if bb else None,
        "all_solids_valid": not invalid,
        "pass_1e-6": bool(rel is not None and rel < 1e-6 and not invalid),
    })
    print("## STEP round-trip\n", json.dumps(RESULTS["roundtrip"], indent=2))


# --- 5. SOMA fasteners comparison ----------------------------------------------------------

def soma_comparison(parts):
    soma_py = Path("soma-src/python")
    soma_py = soma_py if soma_py.exists() else Path("../soma-src/python")
    loader = None
    try:
        sys.path.insert(0, str(soma_py.resolve()))
        import soma.fasteners as sf  # noqa
        loader = "package import"
    except Exception as e:
        print(f"package import failed ({e}); loading fasteners.py standalone")
        try:
            spec = importlib.util.spec_from_file_location(
                "soma_fasteners", soma_py / "soma" / "fasteners.py")
            sf = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sf)
            loader = "standalone module load"
        except Exception as e2:
            RESULTS["soma"] = f"FAIL both loaders: {e} / {e2}"
            traceback.print_exc()
            return

    res = {"loader": loader}

    def shape_of(part):
        sh = part.shape if hasattr(part, "shape") else part
        return sh.val() if hasattr(sh, "val") else sh

    t0 = time.perf_counter()
    try:
        stds = sf.standards()
        res["standards"] = stds if isinstance(stds, (dict, list)) else str(stds)[:500]
    except Exception as e:
        res["standards"] = f"FAIL {e}"
    res["standards_seconds"] = round(time.perf_counter() - t0, 3)

    for label, thunk in (
        ("SOMA Screw ISO 4762 M6x20", lambda: sf.Screw("ISO 4762", "M6", 20, at=(0, 0, 0))),
        ("SOMA Screw ISO 4762 M6x20 (size string)", lambda: sf.Screw("ISO 4762", "M6x20", at=(0, 0, 0))),
        ("SOMA Nut ISO 4032 M6", lambda: sf.Nut("ISO 4032", "M6", at=(0, 0, 0))),
        ("SOMA Washer ISO 7089 M6", lambda: sf.Washer("ISO 7089", "M6", at=(0, 0, 0))),
        ("SOMA HeatSetInsert M3x5.7", lambda: sf.HeatSetInsert("M3x5.7", at=(0, 0, 0))),
    ):
        t0 = time.perf_counter()
        try:
            p = thunk()
            dt = round(time.perf_counter() - t0, 3)
            res[label] = {"ok": True, "seconds": dt, "stats": part_stats(shape_of(p))}
            print(f"OK   {label} {dt}s")
        except Exception as e:
            res[label] = {"ok": False, "seconds": round(time.perf_counter() - t0, 3),
                          "error": f"{type(e).__name__}: {e}"}
            print(f"FAIL {label} {type(e).__name__}: {e}")

    # like-for-like volume/bbox comparison where both exist
    comp = {}
    try:
        soma_screw = shape_of(sf.Screw("ISO 4762", "M6", 20, at=(0, 0, 0)))
        ss = part_stats(soma_screw)
        comp["screw_M6x20"] = {"soma": ss}
        for key, obj in parts.items():
            if "screw" in key or key == "screw":
                comp["screw_M6x20"]["cq_warehouse"] = part_stats(obj.val() if hasattr(obj, "val") else obj)
        if "cq_warehouse" in comp["screw_M6x20"]:
            a = comp["screw_M6x20"]["soma"]
            b = comp["screw_M6x20"]["cq_warehouse"]
            comp["screw_M6x20"]["volume_ratio_cq_over_soma"] = (
                round(b["volume_mm3"] / a["volume_mm3"], 3) if a["volume_mm3"] else None)
    except Exception as e:
        comp["screw_M6x20"] = f"FAIL {e}"
    res["comparison"] = comp
    RESULTS["soma"] = res
    print("## SOMA comparison\n", json.dumps(res, indent=2, default=str)[:4000])


# --- main ----------------------------------------------------------------------------------

def main():
    t_start = time.perf_counter()
    env_info()
    import_timings()
    package_size()
    inventory()
    parts = creation_tests()
    RESULTS["threading"] = thread_tests()
    RESULTS["sprocket"] = sprocket_test()
    roundtrip(parts)
    soma_comparison(parts)
    RESULTS["env"]["total_run_seconds"] = round(time.perf_counter() - t_start, 2)

    ok = sum(1 for t in RESULTS["tests"] if t["ok"])
    fail = sum(1 for t in RESULTS["tests"] if not t["ok"])
    print(f"\n## Summary: {ok} passed, {fail} failed, "
          f"run {RESULTS['env']['total_run_seconds']}s")

    Path("phase2-results.json").write_text(
        json.dumps(RESULTS, indent=2, default=str), encoding="utf-8")
    print("results written to phase2-results.json")


if __name__ == "__main__":
    main()
