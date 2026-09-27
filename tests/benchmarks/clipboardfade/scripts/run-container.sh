#!/bin/bash
# Container entrypoint: reproducible software tier (Xvfb + llvmpipe inside the
# container). Results are written to /out.
#
# NOTE: a "GPU tier" inside a displayless container is not possible with Qt:
# QT_QPA_PLATFORM=offscreen never creates a hardware GL context (verified: no
# render-node fd is ever opened, the scene graph silently falls back to
# software rendering even with EGL surfaceless/device platforms available).
# Hardware (radeonsi) numbers therefore come from the host campaign, where the
# real display server provides the EGL context.
set -u
OUT=/out
mkdir -p "$OUT"
# writable HOME for Qt/fontconfig caches when running with --user
export HOME=/tmp/benchhome
mkdir -p "$HOME"
cp /package-versions.txt "$OUT/package-versions.txt"

Xvfb :99 -screen 0 1280x1024x24 &
XPID=$!
export DISPLAY=:99
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=xcb_egl
export LIBGL_ALWAYS_SOFTWARE=1
echo "mode: software (Xvfb + llvmpipe)"
sleep 2
cleanup() { kill "$XPID" 2>/dev/null || true; }
trap cleanup EXIT

RENDERER=$(glxinfo -B 2>/dev/null | grep -i 'renderer string' || echo "glxinfo failed")
echo "renderer: $RENDERER" | tee "$OUT/renderer-software.txt"

# --- 1) verify the environment reproduces the MultiEffect mask bug ---------
# Run in the background and capture while the window is still mapped.
./build/clipfadebench qrc:/bench/reproduce-bug.qml > "$OUT/repro.err" 2>&1 &
REPROPID=$!
sleep 4
import -window root "$OUT/repro.png" 2>/dev/null || true
kill "$REPROPID" 2>/dev/null
wait "$REPROPID" 2>/dev/null || true
python3 scripts/check_repro.py "$OUT/repro.png" 2>&1 | tee "$OUT/repro.verdict"

# --- 2) benchmark matrix ---------------------------------------------------
for impl in none multieffect opacitymask shadereffect; do
    for mode in real stress; do
        tag="${impl}_${mode}"
        bash scripts/sampler.sh "$OUT/$tag.sampler.csv" 0.5 &
        SPID=$!
        sleep 0.3
        timeout 60 ./build/clipfadebench "qrc:/bench/bench_${impl}_${mode}.qml" \
            > "$OUT/$tag.err" 2>&1 || true
        kill "$SPID" 2>/dev/null || true
        wait "$SPID" 2>/dev/null || true
        echo "RUN done $tag"
    done
done

# --- 3) analysis -----------------------------------------------------------
python3 scripts/summary.py > "$OUT/summary.md" 2>&1 || true
echo "CAMPAIGN DONE"
