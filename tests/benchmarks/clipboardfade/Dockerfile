# Reproducible environment for the clipboard fade benchmark campaign:
# the SOFTWARE tier (llvmpipe, Xvfb inside the container, fully
# self-contained). The hardware (radeonsi) tier runs on the host with the
# real display server — see README.md ("GPU-in-container limitation").
#
# The Arch repository snapshot is pinned via SNAPSHOT (archive.archlinux.org)
# so package versions (mesa, qt6, llvm) are identical across builds; the exact
# versions are recorded to /out/package-versions.txt at run time.
#
# Build:
#   docker build -t clipfade-bench .
# Run:
#   docker run --rm -v "$PWD/results:/out" clipfade-bench
FROM archlinux:latest
ARG SNAPSHOT=2026/09/26

RUN echo "Server = https://archive.archlinux.org/repos/${SNAPSHOT}/\$repo/os/\$arch" > /etc/pacman.d/mirrorlist \
    && sed -i -e 's/^#\?SigLevel.*/SigLevel = Never/' -e '/\[options\]/a DisableDownloadTimeout\nRetries = 5' /etc/pacman.conf \
    && pacman -Syu --noconfirm --ignore archlinux-keyring

RUN pacman -S --noconfirm --needed --ignore archlinux-keyring \
        mesa \
        qt6-base qt6-declarative qt6-shadertools qt6-5compat \
        gcc cmake make pkgconf \
        xorg-server-xvfb xorg-xauth xorg-xprop \
        imagemagick python python-pillow procps-ng mesa-demos \
        ttf-dejavu fontconfig \
    && pacman -Q > /package-versions.txt

WORKDIR /opt/bench
COPY CMakeLists.txt probe_bench.cpp reproduce-bug.qml ./
COPY bench_none_real.qml bench_none_stress.qml bench_multieffect_real.qml bench_multieffect_stress.qml bench_opacitymask_real.qml bench_opacitymask_stress.qml bench_shadereffect_real.qml bench_shadereffect_stress.qml ./
COPY shaders/ shaders/
COPY scripts/ scripts/

RUN cmake -B build -DCMAKE_BUILD_TYPE=Release . \
    && cmake --build build -j"$(nproc)"

ENTRYPOINT ["./scripts/run-container.sh"]
