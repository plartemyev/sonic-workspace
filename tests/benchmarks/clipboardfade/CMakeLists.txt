# SPDX-FileCopyrightText: 2026 Pavel Artemyev <a@pavel.bz>
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Standalone benchmark for the klipper clipboard current-item text fade:
# compares the fade cost of MultiEffect (maskSource), OpacityMask
# (Qt5Compat) and a core-QtQuick ShaderEffect on identical scenes.
# See README.md for the campaign method and results.

cmake_minimum_required(VERSION 3.24)
project(clipboardfade-bench LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)
find_package(Qt6 REQUIRED COMPONENTS Quick ShaderTools)

add_executable(clipfadebench probe_bench.cpp)
target_link_libraries(clipfadebench PRIVATE Qt6::Quick)

qt_add_resources(clipfadebench "bench_qml"
    PREFIX "/bench"
    FILES
        bench_none_real.qml
        bench_none_stress.qml
        bench_multieffect_real.qml
        bench_multieffect_stress.qml
        bench_opacitymask_real.qml
        bench_opacitymask_stress.qml
        bench_shadereffect_real.qml
        bench_shadereffect_stress.qml
        reproduce-bug.qml)

qt_add_shaders(clipfadebench "clipfadebench_shaders"
    PREFIX "/bench"
    FILES shaders/clipboardfade.frag)
