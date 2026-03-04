#!/usr/bin/env python3
'''
    <DEM Wheel-Soil-Box Simulator.>
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

import matplotlib.pyplot as plt
import numpy as np

# 1. Read the data manually
filename = 'plot.txt'
data_dict = {}
headers = []

with open(filename, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        # Handle the header line
        if line.startswith('#'):
            # Remove '#' and split by tabs/multiple spaces
            headers = [h.strip() for h in line.lstrip('#').split()]
            for h in headers:
                data_dict[h] = []
        else:
            # Parse data rows
            values = line.split()
            if len(values) == len(headers):
                for h, val in zip(headers, values):
                    data_dict[h].append(float(val))

# Convert lists to numpy arrays for easier plotting
for h in data_dict:
    data_dict[h] = np.array(data_dict[h])

t = data_dict['t']

# 2. Create the 2x2 Plot
fig, axs = plt.subplots(2, 2, figsize=(10, 6))
plt.subplots_adjust(hspace=0.3, wspace=0.3)

# --- Top Left: Position (z on left y-axis, x on right y-axis) ---
ax1 = axs[0, 0]
ax1_twin = ax1.twinx()
ax1.plot(t, data_dict['z'], color='tab:blue', label='z')
ax1_twin.plot(t, data_dict['x'], color='m', label='x')

ax1.set_xlabel('t')
ax1.set_ylabel('z')
ax1_twin.set_ylabel('x')
ax1.grid(True)
ax1.legend(loc='upper left')
ax1_twin.legend(loc='upper right')
ax1.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
ax1_twin.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

# --- Top Right: Velocities ---
ax2 = axs[0, 1]
ax2.plot(t, data_dict['Vz'], color='blue', label='Vz')
ax2.plot(t, data_dict['WxR'], color='red', label='WxR')
ax2.plot(t, data_dict['Vx'], color='m', label='Vx')
ax2.set_xlabel('t')
ax2.set_ylabel('Vz, WxR, Vx')
ax2.legend(loc='upper left')
ax2.grid(True)
ax2.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

# --- Bottom Left: Forces ---
ax3 = axs[1, 0]
ax3.plot(t, data_dict['Fz'], color='m', label='Fz')
ax3.plot(t, data_dict['mg'], color='black', label='mg')
ax3.set_xlabel('t')
ax3.set_ylabel('Fz, mg')
ax3.legend(loc='upper right')
ax3.grid(True)
ax3.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

# --- Bottom Right: Traction and Resistance ---
ax4 = axs[1, 1]
ax4.plot(t, data_dict['GrTr'], color='m', label='GrTr')
ax4.plot(t, data_dict['Fx'], color='black', label='Fx')
ax4.plot(t, data_dict['RollRes'], color='green', label='RollRes')
ax4.set_xlabel('t')
ax4.set_ylabel('GrTr, Fx, RollRes')
ax4.legend(loc='upper left')
ax4.grid(True)
ax4.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

plt.savefig("plot.png")
plt.show()
