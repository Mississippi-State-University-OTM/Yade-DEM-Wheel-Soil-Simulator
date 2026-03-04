#!/usr/bin/env python3
'''
    <Column average calculation and comparison utility.>
    Copyright (C) 2026  Mississippi State University

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

For more information, contact Mississippi State University's Office of Technology Management at otm@msstate.edu
'''
import sys, argparse, re, math, os

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
    parser.add_argument("file", help="Input data file") # always
    parser.add_argument("--begt", type=float, help="Start time", default=None)
    parser.add_argument("--endt", type=float, help="End time", default=None)
    parser.add_argument("--pRE", type=float, help="Percentage Relative Error tolerance for all columns", default=4.0)
    parser.add_argument("--param", help="Sim parameter file with postproc.avgInt", default=None)
    parser.add_argument("--ref", help="Reference file to compare against", default=None)
    parser.add_argument("--compare", nargs='+', help="Pairs of col:accuracy (e.g., var1:10.0)", default=['WxR:6', 'Vz:10', 'Fx:40', 'Fz:4', 'Slip:4', 'GrTr:50', 'z:11'])

    args = parser.parse_args()
    args_comp_map = parse_comparisons(args.compare)

    ref_plot = None
    begt = None
    endt = None
    # use parameter file if provided
    if args.param:
        with open(args.param, 'r') as f:
            import json
            data = json.load(f)

        begt = data['postproc']['avgInt'][0]
        endt = data['postproc']['avgInt'][1]

        #gather vars : accur pairs (TODO)
        #par_compare = []
        #for var, val in data['compare']['percStdDev'].items():
        #    par_compare.append(var + ":" + str(val))
        #par_comp_map = parse_comparisons(par_compare)

    # overwrite from cmdln if given
    if args.begt:
        begt = args.begt
    if args.endt:
        endt = args.endt
    if not begt or not endt:
        print("Error: need begt, endt for avgInt from cmdln or params.json",
              file=sys.stderr)
        sys.exit(1)
    if args.ref:
        ref_plot = args.ref
    if args.pRE:
        pctRE = args.pRE

    # merge, second overwrites values for the shared keys
    #comp_map = par_comp_map | args_comp_map (TODO)
    comp_map = args_comp_map

    ##############################
    # only merged vars from now on, except args.file

    overall_pass = True

    # 1. Process Main File
    headers, avgs, stds = calculate_stats(args.file, begt, endt)
    if not avgs:
        print("No data processed for main file.")
        sys.exit(1)

    # 2. Write New Results to File (Transposed: one variable per row)
    print(f"# Statistics for {args.file} (t={begt} to {endt})")
    print(f"# {'Variable':<8} {'Average':>15} {'Std_Dev':15}")
    for h, a, s in zip(headers, avgs, stds):
        if s != 0.0 and h != "At" and h != "t":
            print(f"{h:<10} {a:>15.6f} {s:<15.6f}")

    # 3. Comparison Logic
    if ref_plot and comp_map:
        print(f"\n--- Comparison with {ref_plot} @ {pctRE} % tol ---")
        ref_headers, ref_avgs, ref_stds = calculate_stats(ref_plot, begt, endt)
        
        if ref_avgs:
            # Updated Table Header with Target % column
            fmt = "{:<8} | {:>10} | {:>10} | {:>10} | {:>8} | {:>8} | {:>8} | {:<8}"
            print(fmt.format("Variable", "New Avg", "Ref Avg", "+/- StDev", "RelErr %", "StDev %", "Target %", "Status"))
            print("-" * 101)
            
            for col_name, tol_percent in comp_map.items():
                if col_name in headers and col_name in ref_headers:
                    idx = headers.index(col_name)
                    ridx = ref_headers.index(col_name)
                    
                    new_val = avgs[idx]
                    ref_val = ref_avgs[ridx]
                    ref_std = ref_stds[ridx]
                    diff_posneg = new_val - ref_val

                    status = "FAIL"

                    # Caclculate relative error
                    diff_pct = diff_posneg / abs(ref_val) * 100
                    # E.g. < 5% diff => PASS <5%RelE
                    if abs(diff_pct) <= pctRE:
                        status = "PASS < " + str(pctRE) + " % RelE"

                    # Calculate difference as % of ref StdDev
                    if ref_std != 0:
                        pct_stdev = (diff_posneg / ref_std * 100.0) 
                    else:
                        if abs(diff_posneg) == 0:
                            pct_stdev = 0
                        else:
                            pct_stdev = float('inf')

                    if status == "FAIL": # May change to PASS if ref StDev is high
                        if abs(pct_stdev) <= tol_percent:
                            status = "PASS < " + str(tol_percent)  + " % StDev"

                    # If both failed, overall pass is set to FAIL
                    if status == "FAIL":
                        overall_pass = False
                    
                    print(fmt.format(
                        col_name, 
                        f"{new_val:.4f}", 
                        f"{ref_val:.4f}", 
                        f"{ref_std:.4f}",
                        f"{diff_pct:.2f}%", 
                        f"{pct_stdev:.2f}%", 
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
        if ref_plot and comp_map: print("\nOverall Result: PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
