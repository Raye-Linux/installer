// "Save your recovery key": the first page of the welcome after the first
// sign-in, and the first Raye window a person sees on an encrypted install.
//
// What this page replaces, and why it is not a dialog box. Until
// 2026-11-06 the installer's encryption job left a kdialog --msgbox in
// ~/.config/autostart whenever /usr/bin/raye-first-run was not there --
// which was always, because this app had never been written. So the first
// window after installing Raye was a QtWidgets message box carrying the 48
// digits that open the disk: nothing to copy with, nothing to keep it in,
// and no Raye look, because kdialog cannot load org.raye.setup at all.
//
// The page shows the key the way it is written down, offers a way to copy
// it and a way to keep a copy, says in one sentence what it is for, and
// only then lets Done through. Esc leaves it for the next sign-in.
//
// It takes its key as a property and reports what it wants done through
// signals: no file touched here, so tests drive it with a fake key.
import QtQuick
import org.raye.setup

import "words.js" as W

FocusScope {
    id: page

    // The recovery key as the installer writes it: eight groups of six
    // digits joined by "-". Empty until the app hands it over.
    property string key: ""

    // The same key laid out the way a person reads it back, in groups.
    readonly property string grouped: key.split("-").filter(function (g) { return g !== "" }).join(" ")

    // What was last handed to the clipboard. The test reads it; nothing
    // else does. Never the raw key: what is copied is what is shown.
    property string handedToClipboard: ""

    // Asked for by the buttons; the app does the file work.
    signal copyWanted()
    signal saveWanted()
    // the person says the key is written down, and is finished with the page
    signal finished()
    // "not now": the page comes back at the next sign-in
    signal postponed()

    // "en" or "fr". Theme follows the locale; the app can pin it.
    property string lang: Theme.language

    focus: true
    Keys.onEscapePressed: page.postponed()

    SetupFrame {
        id: frame
        anchors.fill: parent
        illustration: "key"

        Column {
            anchors.fill: parent
            spacing: 20

            Text {
                objectName: "title"
                width: parent.width
                font: Theme.titleFor(page.width)
                color: Theme.textPrimary
                wrapMode: Text.WordWrap
                text: W.t(page.lang, "heading")
            }

            Text {
                objectName: "why"
                width: parent.width
                font: Theme.body
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
                lineHeight: 1.35
                text: W.t(page.lang, "why")
            }

            // Selectable, so the key can be read out, picked with the
            // mouse and copied by the Copy button below.
            Rectangle {
                width: parent.width
                height: digits.implicitHeight + 32
                radius: Theme.radiusControl
                color: Theme.controlFill
                border.width: 1
                border.color: Theme.controlStroke

                // four groups to a line, never three and a half
                TextMetrics {
                    id: fourGroups
                    font: digits.font
                    text: "000000 000000 000000 000000 "
                }
                TextEdit {
                    id: digits
                    objectName: "keyText"
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 32, Math.ceil(fourGroups.advanceWidth))
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAtWordBoundaryOrAnywhere
                    horizontalAlignment: TextEdit.AlignHCenter
                    font: Theme.subtitle
                    color: Theme.textPrimary
                    selectionColor: Theme.accent
                    selectedTextColor: Theme.textOnAccent
                    text: page.grouped
                    Accessible.role: Accessible.StaticText
                    Accessible.name: W.t(page.lang, "heading")
                }
            }

            Row {
                spacing: 8
                SubtleButton {
                    objectName: "copyButton"
                    text: copied.running ? W.t(page.lang, "copied") : W.t(page.lang, "copy")
                    onClicked: {
                        digits.selectAll()
                        digits.copy()
                        digits.deselect()
                        page.handedToClipboard = digits.text
                        copied.restart()
                        page.copyWanted()
                    }
                    Timer { id: copied; interval: 1500 }
                }
                SubtleButton {
                    objectName: "saveButton"
                    text: W.t(page.lang, "save")
                    onClicked: page.saveWanted()
                }
            }

            CheckBox {
                id: box
                objectName: "savedCheck"
                text: W.t(page.lang, "savedBox")
            }
        }

        // Done is a binding on the box, not a handler: AbstractButton's
        // toggle() does not emit toggled(), so anything driven by
        // onToggled can be switched on without the button noticing.
        Row {
            anchors { right: frame.pagePane.right; bottom: frame.pagePane.bottom }
            spacing: 8
            SubtleButton {
                objectName: "laterButton"
                text: W.t(page.lang, "later")
                onClicked: page.postponed()
            }
            PrimaryButton {
                objectName: "doneButton"
                text: W.t(page.lang, "done")
                enabled: box.checked
                onClicked: page.finished()
            }
        }
    }
}
