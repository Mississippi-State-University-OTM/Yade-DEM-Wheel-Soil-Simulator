import sys
import argparse
import re
import math
import os

def calculate_stats(file_path, start_time, end_time):
    headers = []
    rows = []
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                if line.startswith('#'):
                    headers = re.split(r'[,\s]+', line.lstrip('#').strip())
                    continue
                
                values = re.split(r'[,\s]+', line)
                try:
                    numeric_row = [float(v) for v in values]
                    t_idx = headers.index('t') if 't' in headers else 0
                    if start_time <= numeric_row[t_idx] <= end_time:
                        rows.append(numeric_row)
                except (ValueError, IndexError):
                    continue

        if not rows:
            return None, None, None

        n = len(rows)
        num_cols = len(headers)
        averages = []
        std_devs = []

        for j in range(num_cols):
            col_data = [row[j] for row in rows]
            avg = sum(col_data) / n
            variance = sum((x - avg) ** 2 for x in col_data) / n
            averages.append(avg)
            std_devs.append(math.sqrt(variance))

        return headers, averages, std_devs
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None, None, None

def parse_comparisons(comp_list):
    comp_map = {}
    if not comp_list:
        return comp_map
    for item in comp_list:
        try:
            col, acc = item.split(':')
            comp_map[col] = float(acc)
        except ValueError:
            print(f"Warning: Ignoring invalid comparison format '{item}'. Use col:accuracy")
    return comp_map

def main():
    parser = argparse.ArgumentParser(description="Average time sequences and compare specific columns.")
    parser.add_argument("file", help="Input data file")
    parser.add_argument("start", type=float, help="Start time")
    parser.add_argument("end", type=float, help="End time")
    parser.add_argument("--ref", help="Reference file to compare against", default=None)
    parser.add_argument("--compare", nargs='+', help="Pairs of col:accuracy (e.g., var1:10.0)", default=[])
    
    args = parser.parse_args()
    comp_map = parse_comparisons(args.compare)
    overall_pass = True

    # 1. Process Main File
    headers, avgs, stds = calculate_stats(args.file, args.start, args.end)
    if not avgs:
        print("No data processed for main file.")
        sys.exit(1)

    # 2. Write New Results to File (Transposed: one variable per row)
    base, ext = os.path.splitext(args.file)
    output_name = f"{base}_avg{ext}"
    try:
        with open(output_name, 'w') as f:
            f.write(f"# Statistics for {args.file} (t={args.start} to {args.end})\n")
            f.write(f"# {'Variable':<15} {'Average':<15} {'Std_Dev':<15}\n")
            for h, a, s in zip(headers, avgs, stds):
                f.write(f"{h:<17} {a:<15.6f} {s:<15.6f}\n")
        print(f"Stats saved to: {output_name}")
    except Exception as e:
        print(f"Could not write to file: {e}")

    # 3. Comparison Logic
    if args.ref and comp_map:
        print(f"\n--- Comparison with {args.ref} ---")
        ref_headers, ref_avgs, ref_stds = calculate_stats(args.ref, args.start, args.end)
        
        if ref_avgs:
            # Updated Table Header with Target % column
            fmt = "{:<8} | {:>10} | {:>10} | {:>10} | {:>8} | {:>8} | {:<8}"
            print(fmt.format("Variable", "New Avg", "Ref Avg", "+/- StDev", "Actual %", "Target %", "Status"))
            print("-" * 79)
            
            for col_name, tol_percent in comp_map.items():
                if col_name in headers and col_name in ref_headers:
                    idx = headers.index(col_name)
                    ridx = ref_headers.index(col_name)
                    
                    new_val = avgs[idx]
                    ref_val = ref_avgs[ridx]
                    ref_std = ref_stds[ridx]
                    
                    diff = abs(new_val - ref_val)
                    tolerance_val = (tol_percent / 100.0) * ref_std
                    
                    # Calculate actual deviation as a percentage of ref StDev
                    actual_pct = (diff / ref_std * 100.0) if ref_std != 0 else (0.0 if diff == 0 else float('inf'))
                    
                    is_pass = diff <= tolerance_val
                    status = "PASS" if is_pass else "FAIL"
                    if not is_pass:
                        overall_pass = False
                    
                    print(fmt.format(
                        col_name, 
                        f"{new_val:.4f}", 
                        f"{ref_val:.4f}", 
                        f"{ref_std:.4f}",
                        f"{actual_pct:.2f}%", 
                        f"{tol_percent:.2f}%", 
                        status
                    ))
                else:
                    print(f"Warning: Column '{col_name}' missing in one or both files.")
        else:
            print("Could not process reference file.")
            sys.exit(1)

    # Final Exit Status
    if not overall_pass:
        print("\nOverall Result: FAILED")
        sys.exit(1)
    else:
        if args.ref and comp_map: print("\nOverall Result: PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
