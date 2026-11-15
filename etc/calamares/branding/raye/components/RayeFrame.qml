// One page of Raye Setup, drawn like the Windows 11 setup card: the night
// background, a card in the middle, the picture on the left, and on the
// right a big title, one short line and the page's content. Back and Next
// are in the bar under it (calamares-navigation.qml), lined up with the
// card's right edge.
//
//   RayeFrame {
//       step: "keyboard"            // its name in strings.js (steps)
//       illustration: "keyboard"
//       title: S.t(lang, "keyboardTitle")
//       text: S.t(lang, "keyboardText")
//       onShown: (backward) => { ... }
//       ...content...
//   }
//
// The frame watches the current step itself: some Calamares steps
// (keyboard, summary) never call the page's onActivate().
import QtQuick
import QtQuick.Layouts
import io.calamares.core 1.0
import io.calamares.ui 1.0
import org.raye.setup

import "../strings.js" as S

Item {
    id: frame

    property string step
    property string illustration
    property string title
    property string text
    // "en" or "fr": read again whenever the step moves, since the language
    // page can change it after every page has loaded
    property string lang: { ViewManager.currentStepIndex; ViewManager.nextLabel; return S.current(Qt.locale()) }
    // came here with Back: the page slides in from the left
    property bool backward: false
    readonly property int index: S.steps.indexOf(step)
    // the step on screen before the current one
    property int seen: -1

    signal shown(bool backward)

    // right-to-left languages (Arabic, Hebrew, Persian...) mirror the page
    LayoutMirroring.enabled: { ViewManager.currentStepIndex; ViewManager.nextLabel; return Qt.locale().textDirection === Qt.RightToLeft }
    LayoutMirroring.childrenInherit: true

    default property alias content: body.data
    readonly property alias contentWidth: body.width
    readonly property alias contentHeight: body.height

    // the card's size, also used by the bars to line up with it
    readonly property int cardWidth: Math.min(1100, width - 96)
    readonly property int cardHeight: Math.min(680, height - 48)

    function stepMoved() {
        const now = ViewManager.currentStepIndex
        if (now === index && now !== seen) {
            backward = seen > now
            enter.enter(backward)
            shown(backward)
        }
        seen = now
    }
    Connections {
        target: ViewManager
        function onCurrentStepChanged() { frame.stepMoved() }
    }
    Component.onCompleted: stepMoved()

    SetupBackground {
        anchors.fill: parent
    }

    Rectangle {
        id: card
        width: frame.cardWidth
        height: frame.cardHeight
        anchors.centerIn: parent
        radius: Theme.radiusCard
        color: Theme.surface
        border.width: 1
        border.color: Theme.surfaceStroke

        Rectangle {
            id: leftPane
            readonly property real corner: Theme.radiusCard - 1
            readonly property bool mirrored: frame.LayoutMirroring.enabled
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 1 }
            width: Math.round(card.width * 0.40)
            topLeftRadius: mirrored ? 0 : corner
            bottomLeftRadius: topLeftRadius
            topRightRadius: mirrored ? corner : 0
            bottomRightRadius: topRightRadius
            color: Theme.pictureSide

            Illustration {
                visible: frame.illustration !== ""
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -parent.height * 0.04
                name: frame.illustration
                size: Math.round(Math.min(leftPane.width * 0.62, leftPane.height * 0.55, 360))
            }
        }

        PageEnter {
            id: enter
            autoPlay: false
            anchors {
                left: leftPane.right; right: parent.right; top: parent.top; bottom: parent.bottom
                leftMargin: 48; rightMargin: 48; topMargin: 44; bottomMargin: 32
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: frame.title
                    font: Theme.title
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.Heading
                    Accessible.name: text
                }
                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: 10
                    visible: frame.text !== ""
                    text: frame.text
                    font: Theme.body
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                    lineHeight: 1.15
                }
                Item {
                    id: body
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.topMargin: 24
                }
            }
        }
    }
}
