# libInteractions.py
# Utilities for inspecting YADE scenes: colliders (Bo1), InteractionLoop functors (Ig2/Ip2/Law2),
# materials + body counts, interaction-type summary, and writing everything to JSON.

import json, sys, datetime
from pprint import pformat

# ------------------------------
# Helpers for robust introspection
# ------------------------------

def _safe_to_dict(obj):
    """
    Return a dictionary of serializable parameters for a YADE object.
    YADE's Python wrappers expose 'Serializable' objects so that dict(obj) yields parameters.
    Falls back to a best-effort attribute crawl if dict(obj) fails.
    """
    try:
        return dict(obj)
    except Exception:
        out = {}
        for k in dir(obj):
            if k.startswith('_'):
                continue
            try:
                v = getattr(obj, k)
                if not callable(v):
                    out[k] = v
            except Exception:
                pass
        return out

def _extract_functor_list_from_dispatcher(dispatcher):
    """Try common attributes to retrieve functor lists from YADE dispatchers."""
    if dispatcher is None:
        return []
    # Typical attribute names across dispatchers
    for attr in ('functors', 'functors2d', 'functors_2d', 'functorList'):
        if hasattr(dispatcher, attr):
            try:
                return list(getattr(dispatcher, attr))
            except Exception:
                pass
    # Sometimes available via dict()
    try:
        d = dict(dispatcher)
        for key in ('functors', 'functors2d', 'functorList'):
            if key in d and isinstance(d[key], (list, tuple)):
                return list(d[key])
    except Exception:
        pass
    return []

def _extract_bo1_from_collider(collider):
    """
    Get list of Bo1_* functors from an InsertionSortCollider-like engine.
    We try several likely attributes and then fallback to dict() inspection.
    """
    # Common attribute in YADE is 'boundDispatcher'
    cand = getattr(collider, 'boundDispatcher', None)
    if cand is not None:
        fl = _extract_functor_list_from_dispatcher(cand)
        if fl:
            return fl
    # Other possible attribute names to try defensively
    for name in ('bo1Dispatcher', 'dispatcher', 'boundFunctors'):
        if hasattr(collider, name):
            fl = _extract_functor_list_from_dispatcher(getattr(collider, name))
            if fl:
                return fl
    # Fallback via dict()
    try:
        d = dict(collider)
        for key in ('boundDispatcher', 'bo1Dispatcher', 'dispatcher', 'boundFunctors'):
            if key in d:
                fl = _extract_functor_list_from_dispatcher(d[key])
                if fl:
                    return fl
    except Exception:
        pass
    return []

def _get_interaction_loops():
    """Return list of (index, loopEngine) for every InteractionLoop in O.engines."""
    loops = []
    for idx, eng in enumerate(O.engines):
        if eng.__class__.__name__ == 'InteractionLoop':
            loops.append((idx, eng))
    return loops

def _get_insertion_sort_colliders():
    """Return list of (index, colliderEngine) for every InsertionSortCollider in O.engines."""
    cols = []
    for idx, eng in enumerate(O.engines):
        if eng.__class__.__name__ == 'InsertionSortCollider':
            cols.append((idx, eng))
    return cols

def _get_loop_functors(loop):
    """Return dict with keys 'Ig2','Ip2','Law2' listing functor objects from an InteractionLoop."""
    geomDisp = getattr(loop, 'geomDispatcher', None)
    physDisp = getattr(loop, 'physDispatcher', None)
    lawDisp  = getattr(loop, 'lawDispatcher',  None)
    return {
        'Ig2': _extract_functor_list_from_dispatcher(geomDisp),
        'Ip2': _extract_functor_list_from_dispatcher(physDisp),
        'Law2': _extract_functor_list_from_dispatcher(lawDisp),
    }

def _label_of(obj, default=''):
    return getattr(obj, 'label', default) or default

def _class_name(obj):
    return obj.__class__.__name__

# ------------------------------
# Public printers
# ------------------------------

def print_insertion_sort_colliders_first():
    """
    Print list of InsertionSortCollider engines (first) with their Bo1_* functors and parameters.
    This is requested to appear FIRST in your inspection output.
    """
    cols = _get_insertion_sort_colliders()
    print("\n=== InsertionSortCollider(s) and Bo1_* functors ===")
    if not cols:
        print("  (no InsertionSortCollider found in O.engines)")
        return
    for idx, col in cols:
        print(f"\n[InsertionSortCollider] label='{_label_of(col)}' at O.engines[{idx}]")
        # Collider parameters
        params = _safe_to_dict(col)
        if params:
            print("  Collider parameters:")
            for line in pformat(params, width=100).splitlines():
                print("    " + line)
        # Bo1 functors
        bo1s = _extract_bo1_from_collider(col)
        print("  Bo1 functors:")
        if not bo1s:
            print("    (no Bo1 functors found or dispatcher not introspectable)")
        else:
            for f in bo1s:
                print(f"    - {_class_name(f)}" + (f"  (label='{_label_of(f)}')" if _label_of(f) else ""))
                fparams = _safe_to_dict(f)
                if fparams:
                    for line in pformat(fparams, width=100).splitlines():
                        print("        " + line)

def print_contact_functors():
    """
    Print Ig2 / Ip2 / Law2 functors (names + parameters) for each InteractionLoop in O.engines.
    """
    print("\n=== YADE contact functors in current scene ===")
    loops = _get_interaction_loops()
    if not loops:
        print("  (no InteractionLoop found in O.engines)")
        return
    for idx, loop in loops:
        print(f"\n[InteractionLoop] label='{_label_of(loop)}' at O.engines[{idx}]")
        functors = _get_loop_functors(loop)
        def _print_cat(cat, items):
            print(f"  {cat}:")
            if not items:
                print("    (no functors found or dispatcher not introspectable)")
                return
            for f in items:
                head = f"    - {_class_name(f)}"
                if _label_of(f):
                    head += f"  (label='{_label_of(f)}')"
                print(head)
                params = _safe_to_dict(f)
                params = {k:v for k,v in params.items() if not k.startswith('_')}
                if params:
                    for line in pformat(params, width=100).splitlines():
                        print("        " + line)
                else:
                    print("        (no serializable parameters)")
        _print_cat('Ig2 (geometry functors)', functors['Ig2'])
        _print_cat('Ip2 (physics functors)',  functors['Ip2'])
        _print_cat('Law2 (contact laws)',     functors['Law2'])

def print_materials_summary(sample_ids=10):
    """
    Print list of materials in O.materials, their parameters, and count of bodies using each.
    Shows up to 'sample_ids' example body ids per material.
    """
    print("\n=== Materials in scene (with body counts) ===")
    try:
        mats = list(O.materials)
    except Exception:
        print("  (unable to access O.materials)")
        return
    if not mats:
        print("  (no materials defined)")
        return
    # Map material object identity to index
    mat_idx_by_addr = {id(m): i for i, m in enumerate(mats)}
    counts = [0]*len(mats)
    samples = [[] for _ in mats]
    # Count bodies per material
    for b in O.bodies:
        try:
            mobj = b.material
            # Sometimes material might be passed by id; be robust
            m_idx = None
            if isinstance(mobj, int):
                if 0 <= mobj < len(mats):
                    m_idx = mobj
            else:
                m_idx = mat_idx_by_addr.get(id(mobj), None)
            if m_idx is not None:
                counts[m_idx] += 1
                if len(samples[m_idx]) < sample_ids:
                    samples[m_idx].append(b.id)
        except Exception:
            pass
    # Print
    for i, m in enumerate(mats):
        print(f"\n- Material #{i}: {_class_name(m)}" + (f"  (label='{_label_of(m)}')" if _label_of(m) else ""))
        mparams = _safe_to_dict(m)
        if mparams:
            for line in pformat(mparams, width=100).splitlines():
                print("    " + line)
        print(f"    bodies_using_this_material: {counts[i]}")
        if samples[i]:
            print(f"    sample_body_ids: {samples[i]}")

def print_contact_types_from_interactions(limit=20):
    """
    After at least one O.step(), list distinct (geomClass, physClass) pairs
    found in real interactions, plus a few example (id1,id2) tuples.
    """
    pairs = {}
    for I in O.interactions:
        if not I.isReal:
            continue
        g = I.geom.__class__.__name__ if I.geom else None
        p = I.phys.__class__.__name__ if I.phys else None
        key = (g, p)
        if key not in pairs: pairs[key] = []
        if len(pairs[key]) < limit:
            pairs[key].append((I.id1, I.id2))
    print("\n=== Distinct (geom, phys) pairs in real interactions ===")
    if not pairs:
        print("  (no real interactions yet; run O.step() a few times)")
        return
    for (g, p), ex in pairs.items():
        suffix = " ..." if len(ex) > 3 else ""
        print(f"  - {g}  /  {p}   (examples: {ex[:3]}{suffix})")
    print("  Tip: ensure a matching Law2_* exists for each (geom, phys) pair.")

# ------------------------------
# JSON serialization helpers
# ------------------------------

def _make_jsonable(value):
    """
    Recursively convert YADE/NumPy/Vector-like objects into JSON-serializable
    structures (dict, list, float, int, str).
    """
    # Basic types
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    # dict-like
    if isinstance(value, dict):
        return {str(k): _make_jsonable(v) for k, v in value.items()}
    # list/tuple/set
    if isinstance(value, (list, tuple, set)):
        return [_make_jsonable(v) for v in value]
    # YADE Serializable?
    try:
        d = dict(value)
        return _make_jsonable(d)
    except Exception:
        pass
    # Fallback to string representation
    try:
        return str(value)
    except Exception:
        return "<unserializable>"

# ------------------------------
# Collectors and JSON writer
# ------------------------------

def collect_simulation_summary(sample_ids=10):
    """
    Collect a comprehensive summary:
      - colliders (first) with Bo1 functors
      - interaction loops with Ig2/Ip2/Law2 functors
      - materials with parameters and body counts (+samples)
      - distinct (geom, phys) interaction pairs (after at least one step)
      - basic scene info
    Returns a Python dict (JSON-serializable).
    """
    # 0) Scene basics
    scene = {
        "iter": int(O.iter),
        "time": float(O.time),
        "dt": float(O.dt) if hasattr(O, 'dt') else None,
        "numBodies": int(len(O.bodies)),
        "numMaterials": int(len(O.materials)) if hasattr(O, 'materials') else None,
        "numInteractions": int(len(O.interactions)),
        "timestamp": datetime.datetime.now().isoformat(),
    }

    # 1) Colliders (first)
    colliders = []
    for idx, col in _get_insertion_sort_colliders():
        entry = {
            "engineIndex": idx,
            "class": _class_name(col),
            "label": _label_of(col),
            "parameters": _safe_to_dict(col),
            "bo1Functors": []
        }
        for f in _extract_bo1_from_collider(col):
            entry["bo1Functors"].append({
                "class": _class_name(f),
                "label": _label_of(f),
                "parameters": _safe_to_dict(f)
            })
        colliders.append(entry)

    # 2) Interaction loops (Ig2 / Ip2 / Law2)
    loops = []
    for idx, loop in _get_interaction_loops():
        functors = _get_loop_functors(loop)
        loops.append({
            "engineIndex": idx,
            "class": _class_name(loop),
            "label": _label_of(loop),
            "Ig2": [{"class": _class_name(f), "label": _label_of(f), "parameters": _safe_to_dict(f)} for f in functors['Ig2']],
            "Ip2": [{"class": _class_name(f), "label": _label_of(f), "parameters": _safe_to_dict(f)} for f in functors['Ip2']],
            "Law2": [{"class": _class_name(f), "label": _label_of(f), "parameters": _safe_to_dict(f)} for f in functors['Law2']],
        })

    # 3) Materials + body counts
    materials = []
    try:
        mats = list(O.materials)
    except Exception:
        mats = []
    mat_idx_by_addr = {id(m): i for i, m in enumerate(mats)}
    counts = [0]*len(mats)
    samples = [[] for _ in mats]
    for b in O.bodies:
        try:
            mobj = b.material
            m_idx = None
            if isinstance(mobj, int):
                if 0 <= mobj < len(mats):
                    m_idx = mobj
            else:
                m_idx = mat_idx_by_addr.get(id(mobj), None)
            if m_idx is not None:
                counts[m_idx] += 1
                if len(samples[m_idx]) < sample_ids:
                    samples[m_idx].append(int(b.id))
        except Exception:
            pass
    for i, m in enumerate(mats):
        materials.append({
            "index": i,
            "class": _class_name(m),
            "label": _label_of(m),
            "parameters": _safe_to_dict(m),
            "bodyCount": counts[i],
            "sampleBodyIds": samples[i],
        })

    # 4) Distinct (geom, phys) interaction pairs (+ examples)
    interPairs = {}
    for I in O.interactions:
        if not I.isReal:
            continue
        g = I.geom.__class__.__name__ if I.geom else None
        p = I.phys.__class__.__name__ if I.phys else None
        key = f"{g}__{p}"
        interPairs.setdefault(key, {"geom": g, "phys": p, "examples": []})
        ex = interPairs[key]["examples"]
        if len(ex) < sample_ids:
            ex.append([int(I.id1), int(I.id2)])

    # 5) Engines (optional: compact info for reference)
    engines = []
    for idx, eng in enumerate(O.engines):
        try:
            engines.append({
                "engineIndex": idx,
                "class": _class_name(eng),
                "label": _label_of(eng),
                "parameters": _safe_to_dict(eng)
            })
        except Exception:
            engines.append({
                "engineIndex": idx,
                "class": _class_name(eng),
                "label": _label_of(eng),
                "parameters": "<unavailable>"
            })

    # Build final structure (colliders first as requested)
    summary = {
        "scene": scene,
        "colliders_first": colliders,
        "interactionLoops": loops,
        "materials": materials,
        "interactionPairs": list(interPairs.values()),
        "engines_all": engines
    }

    # Make sure everything is JSON-serializable
    return _make_jsonable(summary)

def write_simulation_summary_json(path="yade_sim_summary.json", sample_ids=10):
    """
    Collect a simulation summary and write it to a JSON file.
    Returns the path on success.
    """
    data = collect_simulation_summary(sample_ids=sample_ids)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Wrote simulation summary to: {path}")
    return path
