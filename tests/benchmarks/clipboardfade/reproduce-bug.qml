// Reproducer: klipper clipboard current-item text invisible (MultiEffect mask)
//
// Run:  qml clipboard-mask-repro.qml
//
// All effect rows use the same source item (hidden, exactly as
// ClipboardItemDelegate.qml hides the real label while the clipboard item is
// current) and the same hidden rotated white->transparent gradient mask item.
//
// On affected stacks (e.g. Qt 6.11.2 / mesa 26.2.3, radeonsi, EGL/X11):
//   row 1 "control: plain text"                    -> visible
//   row 2 "control: MultiEffect without mask"      -> visible (effect itself works)
//   row 3 "MultiEffect + gradient mask (klipper)"  -> EMPTY  <- the bug
//   row 4 "same, maskInverted"                     -> visible (proves the mask
//                                                     texture was grabbed empty)
// On unaffected stacks row 3 shows the text fading out to the right.
// The fix (PR) restores the OpacityMask implementation used by upstream
// plasma-workspace, which renders row 3's pattern correctly (with fade).

import QtQuick
import QtQuick.Effects

Window {
    id: root
    width: 640
    height: 240
    visible: true
    title: "klipper label-mask reproducer"
    color: "white"

    component ReproRow: Item {
        id: container
        required property string label
        required property bool useEffect
        required property bool useMask
        required property bool inverted
        width: 620
        height: 44

        Text {
            x: 0
            width: 215
            anchors.verticalCenter: parent.verticalCenter
            text: container.label
            color: "#444444"
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }

        // Hidden source label, exactly like the real label is while the item
        // is current: visible: !menuItem.ListView.isCurrentItem -> hidden
        Text {
            id: label
            x: 225
            width: 380
            anchors.verticalCenter: parent.verticalCenter
            text: "CLIPMASK-TEST-CLIPMASK-TEST-CLIPMASK-TEST"
            color: "red"
            font.pixelSize: 18
            visible: false
        }

        // Invisible mask source, same shape as labelMaskSource in
        // ClipboardItemDelegate.qml: hidden Item with a rotated gradient.
        Item {
            id: labelMaskSource
            x: label.x
            width: label.width
            height: label.height
            anchors.verticalCenter: parent.verticalCenter
            visible: false

            Rectangle {
                anchors.centerIn: parent
                rotation: -90
                width: parent.height
                height: parent.width
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "white" }
                    GradientStop { position: 0.6; color: "white" }
                    GradientStop { position: 0.85; color: "transparent" }
                    GradientStop { position: 1; color: "transparent" }
                }
            }
        }

        // Row 1 renders the text directly (no effect), like inactive
        // clipboard items do.
        Text {
            visible: !container.useEffect
            x: label.x
            width: label.width
            anchors.verticalCenter: parent.verticalCenter
            text: label.text
            color: "red"
            font.pixelSize: 18
        }

        MultiEffect {
            visible: container.useEffect
            anchors.fill: label
            source: label
            maskEnabled: container.useMask
            maskInverted: container.inverted
            maskSource: labelMaskSource
        }
    }

    ReproRow { label: "1: control - plain text";                          useEffect: false; useMask: false; inverted: false; x: 10; y: 10  }
    ReproRow { label: "2: control - hidden source + MultiEffect, no mask"; useEffect: true;  useMask: false; inverted: false; x: 10; y: 65  }
    ReproRow { label: "3: hidden source + MultiEffect + gradient mask";    useEffect: true;  useMask: true;  inverted: false; x: 10; y: 120 }
    ReproRow { label: "4: same as 3, maskInverted: true";                  useEffect: true;  useMask: true;  inverted: true;  x: 10; y: 175 }
}
