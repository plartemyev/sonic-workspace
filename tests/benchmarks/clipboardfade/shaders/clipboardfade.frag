// SPDX-FileCopyrightText: 2026 Pavel Artemyev <a@pavel.bz>
// SPDX-License-Identifier: GPL-2.0-or-later

#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(binding = 1) uniform sampler2D source;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float fadeStart;
    float mirror;
};

void main()
{
    // The source texture has premultiplied alpha, so fading the text means
    // scaling the whole vec4. Keeps the fade of the previous gradient mask:
    // fully opaque to the left of (fadeStart - 0.25), a linear ramp to fully
    // transparent at fadeStart, mirrored for right-to-left layouts.
    float x = mix(qt_TexCoord0.x, 1.0 - qt_TexCoord0.x, mirror);
    float a = clamp((fadeStart - x) / 0.25, 0.0, 1.0);
    fragColor = texture(source, qt_TexCoord0) * qt_Opacity * a;
}
