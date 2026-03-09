#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt

# ------------------------
# Load data from text file
# ------------------------
# Header must be: x net gross res
data = np.genfromtxt('Fig9ref.txt', names=True)
datj = np.genfromtxt('Fig9here.txt', names=True)
dat10mus = np.genfromtxt('Fig9here10us.txt', names=True)

x = data['slip']
y_net  = data['net']
y_gross = data['gross']
y_res = data['res']

xj = datj['slip']
yj_net  = datj['net']
yj_gross = datj['gross']

x10mus = dat10mus['slip']
y10mus_net  = dat10mus['net']
y10mus_gross = dat10mus['gross']

# ------------------------
# Cubic Polynomial Fits
# ------------------------
poly_net   = np.poly1d(np.polyfit(x, y_net  , 3))
poly_gross = np.poly1d(np.polyfit(x, y_gross, 3))
poly_res   = np.poly1d(np.polyfit(x, y_res  , 3))

x_smooth = np.linspace(0, 100, 400)

# ------------------------
# Plot
# ------------------------
plt.figure(figsize=(8, 7))

# Net Traction
plt.plot(x_smooth, poly_net(x_smooth),
         color='blue', linewidth=2.5)
plt.scatter(x, y_net,
            color='blue', s=140, label='Net Traction', zorder=3)
plt.scatter(xj, yj_net, facecolor='None',
            color='deepskyblue', s=140, zorder=4)
plt.scatter(x10mus, y10mus_net, facecolor='None',
            color='yellow', s=140, zorder=4)

# Gross Tractive Effort
plt.plot(x_smooth, poly_gross(x_smooth),
         color='red', linestyle='--', linewidth=2.5)
plt.scatter(x, y_gross,
            color='red', marker='D', s=90,
            label='Gross Tractive Effort', zorder=3)
plt.scatter(xj, yj_gross,
            color='tomato', marker='D', s=90, facecolor='None',
            zorder=4)
plt.scatter(x10mus, y10mus_gross,
            color='yellow', marker='D', s=90, facecolor='None',
            zorder=4)

# Motion Resistance
plt.plot(x_smooth, poly_res(x_smooth),
         color='green', linestyle='-.', linewidth=2.5)
plt.scatter(x, y_res,
            color='green', marker='^', s=140,
            label='Motion Resistance', zorder=3)
plt.scatter(xj, -(yj_gross - yj_net), facecolor='None',
            color='lightgreen', marker='^', s=140,
            zorder=4)
plt.scatter(x10mus, -(y10mus_gross - y10mus_net), facecolor='None',
            color='yellow', marker='^', s=140,
            zorder=4)
plt.axhline(y=0, color='black', linestyle='-', linewidth=1.0)
plt.axvline(x=0, color='black', linestyle='-', linewidth=1.0)

# Axes formatting
plt.xlabel('Slip (%)', fontsize=16)
plt.ylabel('Gross Tractive Effort, Net Traction,\nMotion Resistance (N)', fontsize=16)
plt.xlim(-5, 100)
plt.ylim(-5, 20)
plt.xticks([0, 20, 40, 60, 80, 100], fontsize=16)
plt.yticks([-5, 0, 5, 10, 15, 20], fontsize=16)

plt.title(r"Hollow Markers: present results @ dt = 85 $\mu$s, yellow 10$\mu$s "+ "\n"
          r"Filled Markers: Nakanishi (2020) @ dt = 10 $\mu$s",
          fontsize = 16)
plt.legend(loc='upper left', frameon=False, fontsize=16)
plt.grid(True)

plt.tight_layout()
plt.savefig("Fig9.png")
plt.show()
