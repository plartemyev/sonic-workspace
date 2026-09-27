#!/usr/bin/env python3
"""Compact per-cell summary: mean ON/OFF rates per (impl, mode, renderer)."""
import os
import statistics as st
import sys
import analyze as A

LOGS = sys.argv[1] if len(sys.argv) > 1 else A.LOGS
tags = sorted(os.path.basename(p)[:-4] for p in __import__("glob").glob(os.path.join(LOGS, "*.err"))
              if "smoke" not in os.path.basename(p) and "repro" not in os.path.basename(p))

cal = A.calibrate()
Wc = cal.get("Wc_per_core_s") if cal else None
Wg = cal.get("Wg_per_gpu_s") if cal else None

cells = {}
for tag in tags:
    parts = tag.split("_")
    impl, mode = parts[0], parts[1]
    renderer = parts[2] if len(parts) > 2 else "container"
    rnd = parts[3] if len(parts) > 3 else "1"
    phases = A.analyze_run(tag)
    if not phases:
        continue
    key = (impl, mode, renderer)
    for ph in phases:
        c = cells.setdefault(key, {"ON": {"fps": [], "cpu": [], "gpu": [], "w": []},
                                   "OFF": {"fps": [], "cpu": [], "gpu": [], "w": []}})
        if ph["fps"] is not None:
            c[ph["name"]]["fps"].append(ph["fps"])
        if ph["cpu_s"] is not None:
            c[ph["name"]]["cpu"].append(ph["cpu_s"])
        if ph["gpu_s"] is not None:
            c[ph["name"]]["gpu"].append(ph["gpu_s"])
        if ph["cpu_s"] is not None and ph["gpu_s"] is not None and Wc and Wg:
            w = Wc * ph["cpu_s"] + Wg * ph["gpu_s"]
            c[ph["name"]]["w"].append(w)

def m(v):
    return st.mean(v) if v else None


def f3(v, w=6):
    return f"{v:{w}.3f}" if v is not None else " " * w + "n/a"


print(f"Impl/Mode/Renderer       | ON fps | OFF fps |  ON cpu | OFF cpu |    dCPU |  ON gpu | OFF gpu |    dGPU | est W(on) |    dW")
print("-" * 122)
for key in sorted(cells):
    impl, mode, renderer = key
    on, off = cells[key]["ON"], cells[key]["OFF"]
    dcpu = m(on["cpu"]) - m(off["cpu"]) if m(on["cpu"]) and m(off["cpu"]) else None
    dgpu = m(on["gpu"]) - m(off["gpu"]) if m(on["gpu"]) and m(off["gpu"]) else None
    won = m(on["w"])
    dw = (Wc * dcpu + Wg * dgpu) if (dcpu is not None and dgpu is not None and Wc and Wg) else None
    print(f"{impl:<12}{mode:<8}{renderer:<10} | "
          f"{f3(m(on['fps']), 6)} | {f3(m(off['fps']), 7)} | "
          f"{f3(m(on['cpu']))} | {f3(m(off['cpu']), 7)} | {f3(dcpu)} | "
          f"{f3(m(on['gpu']))} | {f3(m(off['gpu']), 7)} | {f3(dgpu)} | "
          f"{f3(won, 9)} | {f3(dw)}")
