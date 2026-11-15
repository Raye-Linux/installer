// Raye Setup: "Is this the right keyboard layout?", then an optional
// second layout. The choice applies to the setup session at once, so the
// field at the bottom and every later field type with it.
//
// Calamares' keyboard job writes the first layout into the new system;
// the second is carried by rayesetupchoices (answer-second-layout).

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.raye.setup

import "../strings.js" as S
import "../components"
import "../components/Countries.js" as Countries
import "../components/Requests.js" as Requests

RayeFrame {
    id: page
    step: "keyboard"
    illustration: "keyboard"
    title: S.t(lang, "keyboardTitle")
    text: S.t(lang, "keyboardText")

    // "layout", "variant" or "second": what the list picks
    property string picking: "layout"
    property string layoutKey: ""
    property string layoutLabel: ""
    property string variantKey: ""
    property string variantLabel: ""
    property string secondKey: ""
    property string secondLabel: ""

    onShown: (backward) => {
        picking = "layout"
        search.text = ""
        Qt.callLater(() => {
            layouts.positionViewAtIndex(Math.max(0, config.keyboardLayoutsModel.currentIndex), ListView.Center)
            // the guess counts too: what is typed later must match the new system
            apply()
        })
    }

    function apply() {
        let names = layoutKey
        let types = variantKey
        if (secondKey !== "" && secondKey !== layoutKey) {
            names += "," + secondKey
            types += ","
        }
        if (names !== "")
            Requests.send("keyboard " + names + (types !== "" ? " " + types : ""))
        Requests.answer("second-layout", secondKey !== layoutKey ? secondKey : "")
        // for the "Ready to install" page, in the words of this list
        Requests.answer("keyboard-label", layoutLabel
                        + (variantKey !== "" && variantLabel !== "" ? " · " + variantLabel : "")
                        + (secondKey !== "" && secondKey !== layoutKey ? ", " + secondLabel : ""))
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Text {
            visible: page.picking !== "layout"
            text: page.picking === "variant" ? S.t(page.lang, "variant") + " · " + page.layoutLabel
                                             : S.t(page.lang, "chooseSecond")
            font: Theme.bodyStrong
            color: Theme.textPrimary
        }

        TextField {
            id: search
            Layout.fillWidth: true
            visible: page.picking !== "variant"
            placeholderText: S.t(page.lang, "keyboardSearch")
            Accessible.name: placeholderText
        }

        ListView {
            id: layouts
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.picking !== "variant"
            clip: true
            focus: visible
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: page.title
            model: config.keyboardLayoutsModel
            currentIndex: page.picking === "layout" ? config.keyboardLayoutsModel.currentIndex : -1

            delegate: ListRow {
                required property int index
                required property string label
                required property string key
                // xkb's "custom" entry is not a layout anyone picks
                readonly property bool matches: key !== "custom"
                                                && (search.text === ""
                                                    || Countries.plain(label).indexOf(Countries.plain(search.text)) >= 0)
                width: ListView.view.width
                visible: matches
                height: matches ? implicitHeight : 0
                text: label
                highlighted: page.picking === "second" ? key === page.secondKey
                                                       : index === config.keyboardLayoutsModel.currentIndex
                // the row Calamares has chosen (its guess, or a click) tells its key
                readonly property bool chosen: index === config.keyboardLayoutsModel.currentIndex
                function report() {
                    if (chosen) {
                        page.layoutKey = key
                        page.layoutLabel = label
                    }
                }
                Component.onCompleted: report()
                onChosenChanged: report()
                onClicked: {
                    if (page.picking === "second") {
                        page.secondKey = key
                        page.secondLabel = label
                        page.picking = "layout"
                        search.text = ""
                        Qt.callLater(() => layouts.positionViewAtIndex(
                            Math.max(0, config.keyboardLayoutsModel.currentIndex), ListView.Contain))
                    } else {
                        config.keyboardLayoutsModel.currentIndex = index
                        page.layoutKey = key
                        page.layoutLabel = label
                        page.variantKey = ""
                        page.variantLabel = ""
                    }
                    page.apply()
                }
            }
        }

        ListView {
            id: variants
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.picking === "variant"
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: S.t(page.lang, "variant")
            model: config.keyboardVariantsModel
            currentIndex: config.keyboardVariantsModel.currentIndex
            delegate: ListRow {
                required property int index
                required property string label
                required property string key
                width: ListView.view.width
                text: label
                highlighted: index === config.keyboardVariantsModel.currentIndex
                function report() {
                    if (highlighted) {
                        page.variantKey = key
                        page.variantLabel = label
                    }
                }
                Component.onCompleted: report()
                onHighlightedChanged: report()
                onClicked: {
                    config.keyboardVariantsModel.currentIndex = index
                    page.variantKey = key
                    page.variantLabel = label
                    page.picking = "layout"
                    page.apply()
                }
            }
        }

        // type and second layout, each with what changes it
        RowLayout {
            Layout.fillWidth: true
            visible: page.picking === "layout"
            spacing: 12
            Text {
                Layout.fillWidth: true
                text: S.t(page.lang, "variant") + (page.lang === "fr" ? "\u00a0: " : ": ")
                      + (page.variantKey === "" || page.variantLabel === "" ? S.t(page.lang, "variantDefault")
                                                                            : page.variantLabel)
                font: Theme.body
                color: Theme.textSecondary
                elide: Text.ElideRight
            }
            LinkButton {
                visible: variants.count > 1
                text: S.t(page.lang, "change")
                onClicked: page.picking = "variant"
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: page.picking === "layout"
            spacing: 12
            LinkButton {
                visible: page.secondKey === ""
                text: S.t(page.lang, "addSecond")
                onClicked: {
                    search.text = ""
                    page.picking = "second"
                    search.forceActiveFocus()
                    layouts.positionViewAtBeginning()
                }
            }
            Text {
                Layout.fillWidth: true
                visible: page.secondKey !== ""
                text: S.t(page.lang, "secondLayout") + (page.lang === "fr" ? "\u00a0: " : ": ") + page.secondLabel
                      + "\n" + S.t(page.lang, "switchHint")
                font: Theme.body
                color: Theme.textSecondary
                elide: Text.ElideRight
            }
            LinkButton {
                visible: page.secondKey !== ""
                text: S.t(page.lang, "remove")
                onClicked: {
                    page.secondKey = ""
                    page.secondLabel = ""
                    page.apply()
                }
            }
        }
        LinkButton {
            visible: page.picking !== "layout"
            text: S.t(page.lang, "back")
            onClicked: page.picking = "layout"
        }

        TextField {
            Layout.fillWidth: true
            visible: page.picking === "layout"
            placeholderText: S.t(page.lang, "tryKeyboard")
            Accessible.name: placeholderText
        }
    }
}
