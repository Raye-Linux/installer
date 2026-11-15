// Shown while Raye installs, like Windows setup: on the left pictures of
// Raye with a tip each, on the right what Setup is doing now in plain words,
// and "Show details" for the live log. Calamares draws the bar with the
// percent under it (stylesheet.qss).
//
// Calamares hands the slideshow no progress -- measured, see the note over
// installStageRules in strings.js. The percentage and the job line under
// this page are Calamares' own widgets, fed by JobQueue::progress; nothing
// here invents a second figure. The stage in plain words and the details
// come from the session log, read every second and a half while the install
// runs.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import org.raye.setup

import "strings.js" as S

Item {
    id: show

    property bool activatedInCalamares: false
    readonly property string lang: { activatedInCalamares; return S.current(Qt.locale()) }
    property int slide: 0
    // "" until a job name in the log says otherwise. It used to start at
    // installDisk, which told anyone whose log could not be read -- wrong
    // path, no XHR permission -- that Raye was partitioning, for the whole
    // install. An unknown stage says "Getting ready" and carries no number.
    property string stage: ""
    readonly property var position: S.installStep(stage)
    property string details: ""
    property bool detailsOpen: false

    // the pictures are Raye's own screens, words included: one set per language
    readonly property var slides: [
        { name: "start", key: "tipStart" },
        { name: "store", key: "tipStore" },
        { name: "files", key: "tipFiles" },
        { name: "update", key: "tipUpdate" }
    ]
    function picture(name) { return "slides/" + show.lang + "/" + name + ".jpg" }

    // slideshow API 2: Calamares calls these when the install starts and ends
    function onActivate() { activatedInCalamares = true; readLog() }
    function onLeave() { activatedInCalamares = false }

    function readLog() {
        const request = new XMLHttpRequest()
        request.onreadystatechange = function() {
            if (request.readyState !== XMLHttpRequest.DONE)
                return
            const tail = String(request.responseText || "").slice(-24000)
            const started = /Starting (?:job|EMERGENCY JOB) "?([^"\n(]+?)"? \(/g
            let last = null
            for (let found = started.exec(tail); found; found = started.exec(tail))
                last = found[1]
            // a job no rule knows leaves the stage where it was: better the
            // last thing we were sure of than a guess
            const reached = last ? S.installStageOf(last) : ""
            if (reached !== "")
                show.stage = reached
            // the log without Calamares' function headers, newest last
            const lines = tail.split("\n")
                .filter(l => l.trim() !== "" && !/^\d\d:\d\d:\d\d \[\d\]: /.test(l))
                .map(l => l.replace(/^\s+(\.\. )?/, ""))
            show.details = lines.slice(-80).join("\n")
        }
        request.open("GET", "file:///root/.cache/calamares/session.log")
        request.send()
    }

    Timer {
        interval: 1500
        repeat: true
        running: show.activatedInCalamares
        onTriggered: show.readLog()
    }

    SetupBackground {
        anchors.fill: parent
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Math.max(48, (parent.width - 1100) / 2)
        anchors.rightMargin: anchors.leftMargin
        anchors.topMargin: 40
        anchors.bottomMargin: 24
        spacing: 48

        // pictures of Raye, a tip under each
        ColumnLayout {
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.55
            spacing: 16

            Item { Layout.fillHeight: true }
            Item {
                id: frame
                Layout.fillWidth: true
                Layout.preferredHeight: width * 9 / 16
                clip: true
                // rounded corners, drawn by a mask the size of the frame
                layer.enabled: true
                layer.effect: MultiEffect {
                    maskEnabled: true
                    maskSource: corners
                }
                Rectangle {
                    id: corners
                    anchors.fill: parent
                    radius: Theme.radiusCard
                    visible: false
                    layer.enabled: true
                }
                Repeater {
                    model: show.slides
                    Image {
                        required property var modelData
                        required property int index
                        anchors.fill: parent
                        source: show.picture(modelData.name)
                        sourceSize.width: frame.width
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        opacity: index === show.slide ? 1 : 0
                        visible: opacity > 0
                        Behavior on opacity { NumberAnimation { duration: 600; easing.type: Easing.InOutQuad } }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    radius: Theme.radiusCard
                    border.width: 1
                    border.color: Theme.surfaceStroke
                }
            }
            Text {
                Layout.fillWidth: true
                text: S.t(show.lang, show.slides[show.slide].key)
                font: Theme.bodyLarge
                color: Theme.textPrimary
                wrapMode: Text.WordWrap
            }
            StepDots {
                count: show.slides.length
                current: show.slide
            }
            Item { Layout.fillHeight: true }
        }

        // what Setup is doing
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Item { Layout.fillHeight: !show.detailsOpen }
            Text {
                Layout.fillWidth: true
                text: S.t(show.lang, "installingTitle")
                font: Theme.title
                color: Theme.textPrimary
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: S.t(show.lang, "installingText")
                font: Theme.body
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.topMargin: 14
                spacing: 12
                ProgressRing {
                    size: 28
                    running: show.activatedInCalamares
                }
                ColumnLayout {
                    spacing: 2
                    Text {
                        text: show.stage === "" ? S.t(show.lang, "installStarting")
                                                : S.t(show.lang, show.stage)
                        font: Theme.bodyStrong
                        color: Theme.textPrimary
                    }
                    // Only a step the order knows gets a number. No
                    // percentage of ours: Calamares draws the real one
                    // under this page (#exec-progress).
                    Text {
                        visible: show.position.step > 0
                        text: S.t(show.lang, "installStepOf",
                                  [show.position.step, show.position.count])
                        font: Theme.caption
                        color: Theme.textTertiary
                    }
                }
            }
            LinkButton {
                Layout.topMargin: 6
                text: S.t(show.lang, show.detailsOpen ? "hideDetails" : "showDetails")
                onClicked: show.detailsOpen = !show.detailsOpen
            }
            // the live log: dark, monospace, follows the end, can be copied
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: show.detailsOpen
                radius: Theme.radiusControl
                color: "#0a0712"
                border.color: Theme.surfaceStroke
                ScrollView {
                    id: logView
                    anchors.fill: parent
                    anchors.margins: 10
                    clip: true
                    TextArea {
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.WrapAnywhere
                        textFormat: TextEdit.PlainText
                        text: show.details
                        font.family: "Cascadia Mono"
                        font.pixelSize: 11
                        color: Theme.textSecondary
                        background: null
                        onTextChanged: Qt.callLater(() => cursorPosition = length)
                    }
                }
            }
            Item { Layout.fillHeight: !show.detailsOpen }
        }
    }

    // a new picture every 8 seconds, only while the install runs
    Timer {
        interval: 8000
        repeat: true
        running: show.activatedInCalamares
        onTriggered: show.slide = (show.slide + 1) % show.slides.length
    }
}
