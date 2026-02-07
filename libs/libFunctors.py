import json
import os
import math
from yade import O, InteractionLoop, Sphere
from collections import Counter
from yade import MatchMaker

from yade import MatchMaker

def sanitize_value(val):
    # 1. Handle standard Python types
    if isinstance(val, (int, float, str, bool, type(None))):
        return val
    
    # 2. Handle Yade MatchMaker objects (Crucial for 'en', 'es', etc.)
    if isinstance(val, MatchMaker):
        # We try to get the constant value if it exists
        # Some Yade versions use 'val', others might not expose it easily
        constant_val = "N/A"
        try:
            # This is a trick to see if we can extract the scalar value 
            # if no matches are defined.
            constant_val = val.dict().get('val', "Global/Constant")
        except:
            pass

        return {
            "_type": "MatchMaker",
            "algo": val.algo,    # e.g., 'val' (constant) or 'average'
            "constant_default": constant_val, # Now you'll see the global number
            "matches": [list(m) for m in val.matches] # List of [id1, id2, value            "matches": [list(m) for m in val.matches]
        }
    
    # 3. Handle iterables (Lists, Vectors, Tuples)
    if isinstance(val, (list, tuple)):
        return [sanitize_value(v) for v in val]
    
    # 4. Handle Dictionaries
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
    
    # 5. Fallback for everything else (Vector3, Quaternions, etc.)
    return str(val)

def get_particle_stats(bins=10):
    # Filter for spheres only
    radii = [b.shape.radius for b in O.bodies if isinstance(b.shape, Sphere)]
    
    if not radii:
        return {"count": 0, "note": "No spheres found in simulation"}

    radii.sort()
    count = len(radii)
    rmin, rmax = radii[0], radii[-1]
    ravg = sum(radii) / count
    
    # Simple histogram logic
    hist_data = []
    if rmax > rmin:
        bin_size = (rmax - rmin) / bins
        for i in range(bins):
            low = rmin + i * bin_size
            high = low + bin_size
            # Count particles in this bin
            b_count = len([r for r in radii if low <= r < (high if i < bins-1 else high + 1e-9)])
            hist_data.append({
                "bin_range": [round(low, 6), round(high, 6)],
                "count": b_count,
                "percentage": round((b_count / count) * 100, 2)
            })

    return {
        "count": count,
        "min_radius": rmin,
        "max_radius": rmax,
        "mean_radius": ravg,
        "distribution": hist_data
    }

def export_sim_state_json(basename="sim_report"):
    data1 = {
        "simulation_info": {
            "iter": O.iter,
            "real_time": O.realtime,
            "virt_time": O.time,
            "num_bodies": len(O.bodies)
        },
        "particles": get_particle_stats(), # Added this
    }
    data = {
        "materials": [],
        "functors": {
            "geometry": [],
            "physics": [],
            "law": []
        }
    }

    # 1. Process Materials & Associations
    mat_id_counts = Counter(b.material.id for b in O.bodies if b.material)
    for m in O.materials:
        m_data = m.dict()
        m_data["_type"] = m.__class__.__name__
        m_data["_body_count"] = mat_id_counts.get(m.id, 0)
        data["materials"].append(sanitize_value(m_data))

    # 2. Process Functors
    try:
        iloop = [e for e in O.engines if isinstance(e, InteractionLoop)][0]
        mapping = {
            "geometry": iloop.geomDispatcher.functors,
            "physics": iloop.physDispatcher.functors,
            "law": iloop.lawDispatcher.functors
        }
        for key, functors in mapping.items():
            for f in functors:
                f_data = f.dict()
                f_data["_type"] = f.__class__.__name__
                data["functors"][key].append(sanitize_value(f_data))
    except IndexError:
        print("Warning: InteractionLoop not found. Functors skipped.")

    # 3. Write to Files
    #
    filename1 = basename + "_psd.json"
    with open(filename1, 'w') as f:
        json.dump(data1, f, indent=4)
    
    filename = basename + ".json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"--- Report exported to: {filename} and {filename1} ---")

def print_material_report():

    print(f"\n{'='*60}")
    print(f"YADE MATERIAL & ASSOCIATION REPORT")
    print(f"{'='*60}\n")

    # 1. Map Material IDs to how many bodies use them
    # We count occurrences of material IDs across all bodies
    mat_id_counts = Counter(b.material.id for b in O.bodies if b.material)
    
    # 2. Iterate through defined materials
    for m in O.materials:
        count = mat_id_counts.get(m.id, 0)
        
        print(f"Material Index [{m.id}]")
        print(f"  ├── Label: {m.label if m.label else 'None'}")
        print(f"  ├── Type:  {m.__class__.__name__}")
        print(f"  ├── Bodies Associated: {count}")
        
        # Print parameters
        params = m.dict()
        for key, val in params.items():
            # Filter out internal/clutter params if desired, 
            # but dict() is usually quite clean
            print(f"  │   ├── {key}: {val}")
        print("  └──")

def print_functor_details():
    # 1. Find the InteractionLoop engine
    try:
        interaction_loop = [e for e in O.engines if isinstance(e, InteractionLoop)][0]
    except IndexError:
        print("InteractionLoop not found in O.engines.")
        return

    # Map the dispatchers to readable names
    dispatchers = {
        "Geometry Functors (IGeom)": interaction_loop.geomDispatcher.functors,
        "Physics Functors (IPhys)": interaction_loop.physDispatcher.functors,
        "Law Functors (Law)": interaction_loop.lawDispatcher.functors
    }

    print(f"\n{'='*60}")
    print(f"YADE FUNCTOR PARAMETERS REPORT")
    print(f"{'='*60}\n")

    for label, functors in dispatchers.items():
        print(f"--- {label} ---")
        if not functors:
            print("  None defined.\n")
            continue

        for f in functors:
            # Print the class name of the functor
            print(f"\n[Functor]: {f.__class__.__name__}")

            # Print parameters (attributes) and their values
            # Using dict() provides a clean key-value pair of current settings
            params = f.dict()
            for key, val in params.items():
                print(f"  |-- {key}: {val}")
        print("\n")
    
