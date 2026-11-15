// The frame of the two full-screen setup apps (the start app and the
// welcome after the first sign-in): the night background, a card in the
// middle split in two like the Windows setup card (the picture on the
// left, the page on the right), and a strip along the bottom of the
// screen for the small buttons (keyboard, network, power...).
//
//   SetupFrame {
//       anchors.fill: parent
//       illustration: "keyboard"
//       footerLeft: [ KeyboardButton {}, NetworkButton {} ]
//       footerRight: [ PowerButton {} ]
//       // the page: placed in the right half, inside its padding
//       PageEnter { anchors.fill: parent; ... }
//   }
//
// card: false draws the two panes edge to edge instead (the left pane
// 42 % of the width, at most 760 px), the way the Calamares window is laid
// out.
import QtQuick
import org.raye.setup

Item {
    id: frame

    property string illustration
    property bool card: true
    property real leftRatio: card ? 0.45 : 0.42
    property int maxCardWidth: 1100
    property int maxCardHeight: 680
    readonly property real illustrationSize: Math.round(Math.min(leftPane.width * 0.62,
                                                                 leftPane.height * 0.55, 380))

    default property alias content: page.data
    // more things in the left pane, over the picture's pane (a title...)
    property alias leftContent: leftExtra.data
    property alias footerLeft: footerLeftRow.data
    property alias footerRight: footerRightRow.data
    // the two panes, for pages that need their size
    readonly property alias leftPane: leftPane
    readonly property alias pagePane: page

    readonly property int footerHeight: 56
    readonly property int margin: 24

    SetupBackground {
        // named so a page can prove it is drawn on the Raye night
        objectName: "night"
        anchors.fill: parent
    }

    Rectangle {
        id: surface
        objectName: "surface"
        width: frame.card ? Math.min(frame.maxCardWidth, frame.width - 2 * frame.margin * 2) : frame.width
        height: frame.card ? Math.min(frame.maxCardHeight, frame.height - 2 * (frame.footerHeight + frame.margin / 2))
                           : frame.height
        anchors.centerIn: parent
        anchors.verticalCenterOffset: frame.card ? -frame.margin / 4 : 0
        radius: frame.card ? Theme.radiusCard : 0
        color: frame.card ? Theme.surface : "transparent"
        border.width: frame.card ? 1 : 0
        border.color: Theme.surfaceStroke

        // left pane: a shade lighter, the picture in it
        Rectangle {
            id: leftPane
            objectName: "leftPane"
            x: frame.card ? 1 : 0
            y: frame.card ? 1 : 0
            width: frame.card ? Math.round(surface.width * frame.leftRatio)
                              : Math.min(Math.round(frame.width * frame.leftRatio), 760)
            height: surface.height - 2 * y
            topLeftRadius: frame.card ? Theme.radiusCard - 1 : 0
            bottomLeftRadius: topLeftRadius
            color: Theme.pictureSide

            Illustration {
                visible: frame.illustration !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -parent.height * 0.04
                name: frame.illustration
                size: frame.illustrationSize
            }

            Item {
                id: leftExtra
                anchors.fill: parent
                // edge to edge, the bottom strip runs over this pane
                anchors.bottomMargin: frame.card ? 0 : frame.footerHeight
            }
        }

        // right pane: the page
        Item {
            id: page
            objectName: "page"
            anchors {
                left: leftPane.right; right: parent.right; top: parent.top; bottom: parent.bottom
                leftMargin: 48; rightMargin: 48; topMargin: 44
                bottomMargin: frame.card ? 32 : frame.footerHeight + 16
            }
        }
    }

    Row {
        id: footerLeftRow
        anchors { left: parent.left; bottom: parent.bottom; leftMargin: frame.margin; bottomMargin: 12 }
        height: frame.footerHeight - 16
        spacing: 4
    }
    Row {
        id: footerRightRow
        anchors { right: parent.right; bottom: parent.bottom; rightMargin: frame.margin; bottomMargin: 12 }
        height: frame.footerHeight - 16
        spacing: 4
        layoutDirection: Qt.RightToLeft
    }
}
