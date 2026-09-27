// Bench: impl=none mode=stress (currentRows=24)
// Phases: 2s lead-in, then 4 x (5s ON, 5s OFF). Labels wobble continuously.
import QtQuick

Window {
    id: root
    width: 640
    height: 1010
    visible: true
    title: "BENCH none stress"
    color: "#3999e6"

    property int currentRows: 24
    property bool effectOn: false
    property int frames: 0
    property int phaseStartFrames: 0
    property int phaseIdx: -1
    property string phaseName: ""
    property int phaseNum: 0

    onFrameSwapped: frames++

    Component.onCompleted: bench.report("T0 " + Date.now())

    // continuous-frame driver: invisible, negligible cost
    Rectangle {
        width: 2; height: 2; opacity: 0.01; color: "black"
        NumberAnimation on x { from: 0; to: 636; duration: 3000; loops: Animation.Infinite }
    }

    Repeater {
        model: 24

        Item {
            id: container
            required property int index
            x: 10
            y: 10 + index * 41
            width: 600
            height: 40

            Text {
                id: label
                x: 5
                width: 500
                anchors.verticalCenter: parent.verticalCenter
                text: "CLIPMASK-TEST-CLIPMASK-TEST row " + container.index
                color: "red"
                font.pixelSize: 18
                visible: false

                NumberAnimation on x { from: 4.5; to: 5.5; duration: 250; loops: Animation.Infinite }
            }

        }
    }

    Timer {
        id: lead
        interval: 2000
        running: true
        onTriggered: {
            root.phaseIdx = 0
            root.phaseName = "ON"
            root.phaseNum = 1
            root.effectOn = true
            root.phaseStartFrames = root.frames
            bench.report("PHASE ON 1 " + Date.now())
            cycle.running = true
        }
    }

    Timer {
        id: cycle
        interval: 5000
        repeat: true
        running: false
        onTriggered: {
            const df = root.frames - root.phaseStartFrames
            bench.report("FPS " + root.phaseName + " " + (df / 5.0).toFixed(1))
            root.phaseIdx++
            if (root.phaseIdx >= 8) {
                bench.report("END " + Date.now())
                cycle.stop()
                bench.quitApp()
                return
            }
            root.phaseName = root.phaseIdx % 2 === 0 ? "ON" : "OFF"
            root.phaseNum = Math.floor(root.phaseIdx / 2) + 1
            root.effectOn = root.phaseName === "ON"
            root.phaseStartFrames = root.frames
            bench.report("PHASE " + root.phaseName + " " + root.phaseNum + " " + Date.now())
        }
    }
}
