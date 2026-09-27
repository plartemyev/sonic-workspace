# Clipboard fade benchmark

Measures and compares the per-frame cost of the three implementations of the
klipper clipboard current-item text fade (see `klipper/declarative/qml/`):

| variant | mechanism | status |
|---|---|---|
| `MultiEffect` | `maskSource` gradient mask of the hidden label | shipped in this fork since 6.7.5.1; renders **nothing** on affected stacks (invisible `maskSource` grabbed as an empty texture — reproduces on radeonsi *and* llvmpipe, i.e. Qt 6.11.2-level, not driver-level) |
| `OpacityMask` | Qt5Compat.GraphicalEffects (upstream KDE implementation) | renders correctly, requires Qt5Compat |
| `ShaderEffect` | `ShaderEffectSource` + core-QtQuick fragment shader, alpha ramp | proposed fix (branch `klipper-shader-fade`); renders correctly, no Qt5Compat |

Each `bench_<impl>_<mode>.qml` scene is a 24-row clipboard-like list with
hidden source labels, a 2 s lead-in and a scripted
**4 × (5 s ON, 5 s OFF)** phase pattern (ON = fade visible like a hovered
row, OFF = effects hidden like inactive rows). Labels animate every frame to
force worst-case per-frame texture re-rendering. `reproduce-bug.qml` is the
minimal pixel-verifiable reproducer of the `MultiEffect` failure.

## Metrics (per process, immune to background noise)

- `drm-engine-gfx` ns delta on the process render fd — GPU engine time
- utime/stime, incl. the QSGRenderThread — CPU time
- `frameSwapped` count — FPS (display-paced, 60 Hz here)
- `/proc/stat` busy cores, battery charge/voltage — for power estimation

Power is **estimated** as `CPU_s × Wc + GPU_s × Wg`; the coefficients are
fitted once per machine from multi-minute battery phases (idle / all-core CPU
burn / full GPU burn) — see `cal/` and `analyze.py`. On the reference machine
(HP EliteBook 745 G5, Zen1 APU, pinned lowest clocks): Wc ≈ 1.81 W,
Wg ≈ 2.60 W.

## Layout

- `probe_bench.cpp` — QML runner; stderr reporting (the `qml` tool suppresses
  all output), vsync disabled for uncapped runs (`QT_BENCH_KEEP_VSYNC=1` keeps it)
- `bench_<impl>_<mode>.qml` — scenes; modes: `real` (1 current row, the real
  widget case) and `stress` (24 concurrent fades)
- `reproduce-bug.qml` — 4-row bug reproducer with pixel verdict
- `shaders/clipboardfade.frag` — the fade shader (same as the klipper plugin)
- `scripts/` — `run-container.sh`, `sampler.sh`, `analyze.py`, `summary.py`,
  `check_repro.py`
- `results/` — committed campaign outputs
- `Dockerfile` — reproducible Arch snapshot (pinned via `SNAPSHOT` build arg)

## Usage

Host (matches the running DE, like the original campaign):

```sh
cp cal/coefficients.json ..   # if fitted
bash sampler.sh out.csv 0.5 &
./build/clipfadebench qrc:/bench/bench_shadereffect.qml
```

Reproducible container — **software tier** (llvmpipe, Xvfb, self-contained;
includes the pixel-verified bug reproduction):

```sh
docker build -t clipfade-bench .
docker run --rm -v "$PWD/results:/out" clipfade-bench
```

**GPU-in-container limitation:** a hardware tier inside a displayless
container is not possible with Qt: `QT_QPA_PLATFORM=offscreen` never creates
a hardware GL context (verified — no render-node fd is ever opened and the
scene graph silently falls back to software rendering, even with Mesa's
EGL surfaceless/device platforms available), and a full X server in the
container would need to become KMS master on the physical device, which
cannot be shared with the running host session. Hardware (radeonsi) numbers
therefore come from the host campaign, where the real display server
provides the EGL context.

`run-container.sh` verifies the renderer (glxinfo), pixel-verifies the bug
reproduction, runs the 8-run matrix, and writes `summary.md` + raw CSVs to
`/out`. Analysis: `scripts/summary.py` (compact per-cell table) and
`scripts/analyze.py` (full per-phase table, power estimates when `cal/`
coefficients are present).

## Results snapshot (2026-09-27, radeonsi, pinned lowest clocks)

Effect-activation cost (ON − OFF, see `results/`):

| implementation | realistic (1 row) | stress (24 rows) |
|---|---|---|
| none (floor) | ≈ 0 | ≈ 0 |
| MultiEffect (broken) | +0.005 core-s/s | +0.068 core-s/s (+0.158 W est) |
| OpacityMask (Qt5Compat) | +0.002 core-s/s | +0.032 core-s/s (+0.072 W est) |
| ShaderEffect (this fix) | +0.004 core-s/s | +0.040 core-s/s (+0.088 W est) |

GPU duty ≤ 0.6 % for all variants; vsync 60 fps held everywhere. In the real
widget scenario (one hovered row) all implementations are below measurement
noise. The broken `MultiEffect` pays the most while rendering nothing.

The pinned-snapshot container reproduces the same ordering on llvmpipe
(independent environment, container mesa/qt — see
`results/software/summary.md`): MultiEffect +1.441, ShaderEffect +1.226,
OpacityMask +0.746 core-s/s under stress; realistic ≤ +0.047 for all.
