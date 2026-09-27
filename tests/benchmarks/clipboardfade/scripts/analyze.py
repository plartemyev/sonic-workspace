#!/usr/bin/env python3
"""Analyze benchmark logs -> per-phase table + power estimates.

Inputs:  logs/<tag>.err (BENCH PHASE/FPS/T0/END markers)
         logs/<tag>.sampler.csv (ts, charge, volt, current, cpu_busy,
                                 utime, stime, qsg_utime, qsg_stime, engine_gfx)
         logs/<tag>.perf (perf stat -x,)
         cal/*.csv (calibration phases)
Outputs: markdown table to stdout + cal/coefficients.json
"""
import csv
import glob
import json
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "logs")
CAL = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "cal")
USER_HZ = 100.0


def read_sampler(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            def num(key):
                v = r.get(key, "NA")
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
            rows.append({
                "ts": float(r["ts"]),
                "charge": num("charge"),
                "volt": num("volt"),
                "cpu_busy": num("cpu_busy"),
                "utime": num("utime"),
                "stime": num("stime"),
                "qut": num("qsg_utime"),
                "qst": num("qsg_stime"),
                "eng": num("engine_gfx"),
            })
    return rows


def rates(rows, t0, t1, keys):
    """Mean rates over [t0, t1]: dict key -> per-second delta (counters)."""
    seg = [r for r in rows if t0 <= r["ts"] <= t1]
    if len(seg) < 3:
        return {k: None for k in keys}
    out = {}
    dt = seg[-1]["ts"] - seg[0]["ts"]
    for k in keys:
        a, b = seg[0][k], seg[-1][k]
        if a is None or b is None or dt <= 0:
            out[k] = None
        else:
            out[k] = (b - a) / dt
    return out


def phases_from_err(path):
    """Parse BENCH markers -> list of phases with wall start/end + fps."""
    phases = []
    t0 = None
    cur = None
    fps = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"BENCH PHASE (ON|OFF) (\d+) (\d+)", line.strip())
            if m:
                if cur:
                    cur["end"] = int(m.group(3))
                    phases.append(cur)
                cur = {"name": m.group(1), "num": int(m.group(2)),
                       "start": int(m.group(3)), "end": None, "fps": None}
                continue
            m = re.match(r"BENCH FPS (ON|OFF) ([0-9.]+)", line.strip())
            if m:
                fps.setdefault((m.group(1)), []).append(float(m.group(2)))
                if cur:
                    cur["fps"] = float(m.group(2))
    if cur:
        cur["end"] = cur["start"] + 5000
        phases.append(cur)
    return phases, t0


def analyze_run(tag):
    err = os.path.join(LOGS, f"{tag}.err")
    smp = os.path.join(LOGS, f"{tag}.sampler.csv")
    if not (os.path.exists(err) and os.path.exists(smp)):
        return None
    phases, _ = phases_from_err(err)
    rows = read_sampler(smp)
    if not phases or not rows:
        return None
    out = []
    for ph in phases:
        if ph["end"] is None:
            continue
        t0, t1 = ph["start"] / 1000.0, ph["end"] / 1000.0
        r = rates(rows, t0, t1, ["cpu_busy", "utime", "stime", "qut", "qst", "eng"])
        cpu_s = None
        if r["utime"] is not None and r["stime"] is not None:
            cpu_s = (r["utime"] + r["stime"]) / USER_HZ
        qsg_s = None
        if r["qut"] is not None and r["qst"] is not None:
            qsg_s = (r["qut"] + r["qst"]) / USER_HZ
        cores = None
        if r["cpu_busy"] is not None:
            cores = r["cpu_busy"] / USER_HZ
        gpu_s = r["eng"] / 1e9 if r["eng"] is not None else None
        out.append({"name": ph["name"], "num": ph["num"], "fps": ph["fps"],
                    "cpu_s": cpu_s, "qsg_s": qsg_s, "cores": cores, "gpu_s": gpu_s})
    return out


def mean_phase(phases, name, key):
    vals = [p[key] for p in phases if p["name"] == name and p[key] is not None]
    return st.mean(vals) if vals else None


def chunks(rows, max_gap=120.0):
    """Split timestamped rows into contiguous chunks (>max_gap s gap = new chunk)."""
    out = []
    for r in rows:
        if not out or r["ts"] - out[-1][-1]["ts"] > max_gap:
            out.append([r])
        else:
            out[-1].append(r)
    return out


def calibrate():
    bat = os.path.join(CAL, "battery.csv")
    cpu = os.path.join(CAL, "cpu.csv")
    gpu = os.path.join(CAL, "gpu.csv")
    if not os.path.exists(bat):
        return None
    # battery power per sample window: d(charge uAh)/dt(s) * V -> W
    b = []
    with open(bat) as f:
        for r in csv.reader(f):
            if len(r) >= 5 and r[2] not in ("NA", ""):
                b.append({"ts": float(r[0]), "name": r[1],
                          "charge": float(r[2]), "volt": float(r[3])})
    cpus = {}
    with open(cpu) as f:
        for r in csv.reader(f):
            if len(r) >= 4 and r[2] not in ("NA", ""):
                cpus.setdefault(r[1], []).append({"ts": float(r[0]), "busy": float(r[2])})
    gpus = {}
    if os.path.exists(gpu):
        with open(gpu) as f:
            for r in csv.reader(f):
                if len(r) >= 4 and r[3] not in ("NA", ""):
                    gpus.setdefault(r[1], []).append({"ts": float(r[0]), "eng": float(r[3])})
    result = {}
    for phase in ("idle", "cpuburn", "gpuburn"):
        # longest contiguous chunk per phase (re-runs append after gaps)
        seg = max(chunks([x for x in b if x["name"] == phase]), key=len, default=[])
        if len(seg) < 3:
            continue
        dt = seg[-1]["ts"] - seg[0]["ts"]
        dcharge = seg[-1]["charge"] - seg[0]["charge"]  # uAh (negative on discharge)
        volts = [x["volt"] for x in seg if x["volt"]]
        vmean = st.mean(volts) if volts else None
        # current A = d(uAh)/dt(s) * 3600 / 1e6 ; discharge -> positive power
        cur_a = (-dcharge) / dt * 3600.0 / 1e6
        power = cur_a * vmean / 1e6 if vmean else None  # voltage_now is uV
        # cpu cores busy (longest chunk of the same phase)
        cs = max(chunks(cpus.get(phase, [])), key=len, default=[])
        cores = ((cs[-1]["busy"] - cs[0]["busy"]) / USER_HZ / (cs[-1]["ts"] - cs[0]["ts"])
                 if len(cs) >= 2 and cs[-1]["ts"] > cs[0]["ts"] else None)
        # gpu engine s/s (longest chunk)
        gs = max(chunks(gpus.get(phase, [])), key=len, default=[])
        g = ((gs[-1]["eng"] - gs[0]["eng"]) / 1e9 / (gs[-1]["ts"] - gs[0]["ts"])
             if len(gs) >= 2 and gs[-1]["ts"] > gs[0]["ts"] else 0.0)
        result[phase] = {"power_W": power, "cores": cores, "gpu_s_s": g,
                         "cal_s": round(dt)}
    if not all(k in result for k in ("idle", "cpuburn", "gpuburn")):
        return result
    # solve P = P0 + Wc*C + Wg*G with idle baseline and two burn points
    Wc = ((result["cpuburn"]["power_W"] - result["idle"]["power_W"])
          / max(result["cpuburn"]["cores"] - result["idle"]["cores"], 1e-6))
    Wg = ((result["gpuburn"]["power_W"] - result["idle"]["power_W"]
           - Wc * (result["gpuburn"]["cores"] - result["idle"]["cores"]))
          / max(result["gpuburn"]["gpu_s_s"] - result["idle"]["gpu_s_s"], 1e-6))
    result["Wc_per_core_s"] = Wc
    result["Wg_per_gpu_s"] = Wg
    return result


def main():
    cal = calibrate()
    if cal:
        print("## Calibration")
        for k, v in cal.items():
            print(f"- {k}: {v}")
        print()
    tags = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(LOGS, "*.err")))
    print("## Runs")
    print("| run | phase | fps | cpu s/s | qsg s/s | gpu s/s | est. W |")
    print("|---|---|---|---|---|---|---|")
    for tag in tags:
        phases = analyze_run(tag)
        if not phases:
            print(f"| {tag} | (no data) | | | | | |")
            continue
        for p in phases:
            w = ""
            if cal and "Wc_per_core_s" in cal and p["cpu_s"] is not None and p["gpu_s"] is not None:
                est = (cal["Wc_per_core_s"] * p["cpu_s"] + cal["Wg_per_gpu_s"] * p["gpu_s"])
                w = f"{est:.2f}"
            cpu = f"{p['cpu_s']:.3f}" if p["cpu_s"] is not None else ""
            qsg = f"{p['qsg_s']:.3f}" if p["qsg_s"] is not None else ""
            gpu = f"{p['gpu_s']:.3f}" if p["gpu_s"] is not None else ""
            fps = f"{p['fps']:.1f}" if p["fps"] is not None else ""
            print(f"| {tag} | {p['name']}{p['num']} | {fps} | {cpu} | {qsg} | {gpu} | {w} |")
    if cal and "Wc_per_core_s" in cal:
        with open(os.path.join(CAL, "coefficients.json"), "w") as f:
            json.dump(cal, f, indent=2)


if __name__ == "__main__":
    main()
