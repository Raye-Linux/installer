// Raye Setup: "Where do you want to install Raye?". One disk at a time, what
// can be done with it as cards, a picture of what will happen, and encryption
// under it. What may be offered comes from raye-disks, and the rayedisk job
// checks the answer again against the disk before it writes anything.
//
// Nothing is picked for the person unless the disk is empty: a card that
// deletes something is only ever chosen by hand, and only once the box that
// asks "Delete Arch Linux?" (or erase, or make smaller) says yes. Next waits for a choice
// (calamares-navigation.qml reads disk-ready, there is no other way between
// two QML engines).

import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Templates as T
import org.raye.setup

import "../strings.js" as S
import "../components"
import "../components/Requests.js" as Requests
import "../components/DiskLogic.js" as Logic

RayeFrame {
    id: page
    step: "disk"
    illustration: "disk"
    title: S.t(lang, "diskTitle")
    text: S.t(lang, "diskText")

    property var report: null
    property int diskIndex: 0
    property int optionIndex: -1
    property real keep: 0
    property bool scanning: true
    property int waited: 0

    readonly property var disks: report ? report.disks : []
    readonly property var usable: disks.filter(d => !d.blocked)
    readonly property var disk: usable.length > diskIndex ? usable[diskIndex] : null
    readonly property var options: disk ? disk.options : []
    readonly property var option: optionIndex >= 0 && optionIndex < options.length ? options[optionIndex] : null
    readonly property var picture: disk ? Logic.bars(disk, option, keep, lang) : null
    readonly property string passProblem: Logic.passphraseProblem(encrypt.checked, pass.text, again.text, lang)
    readonly property bool complete: option !== null && passProblem === ""
    readonly property string passShown: Logic.passphraseShown(encrypt.checked, pass.text, again.text, lang)

    Component.onCompleted: load()
    onShown: (backward) => { save() }

    function load() {
        Requests.read("disks.json", text => {
            if (report)
                return
            let found = null
            try { found = text ? JSON.parse(text) : null } catch (e) { found = null }
            if (found) {
                report = found
                scanning = false
                choose(0)
            } else {
                // raye-disks takes seconds. After two minutes something is
                // wrong: say so and offer to look again, keep listening
                waited += 1
                if (waited >= 240)
                    scanning = false
                poll.start()
            }
        })
    }
    Timer {
        id: poll
        interval: 500
        onTriggered: page.load()
    }

    function lookAgain() {
        scanning = true
        report = null
        waited = 0
        Requests.write("disks.json", "")
        Requests.send("disks")
        poll.restart()
    }

    function choose(index) {
        diskIndex = index
        picks.checkState = Qt.Unchecked
        optionIndex = -1
        // an empty disk has nothing to lose and one thing to do
        if (disk && disk.empty && disk.options.length === 1)
            optionIndex = 0
        save()
    }

    // a card that deletes or resizes asks first; the others are picked at once
    property int asking: -1
    readonly property var question: asking >= 0 && asking < options.length
                                    ? Logic.confirm(options[asking], disk, lang) : null
    function ask(index) {
        if (index === optionIndex)
            return
        if (Logic.confirm(options[index], disk, lang) === null) {
            pick(index)
            return
        }
        asking = index
        confirmBox.showOver()
        confirmCard.forceActiveFocus()
    }
    function answerQuestion(yes) {
        const index = asking
        asking = -1
        confirmBox.hide()
        if (yes && index >= 0)
            pick(index)
    }

    function pick(index) {
        optionIndex = index
        const picked = options[index]
        if (picked && picked.mode === "shrink")
            keep = picked.keepDefault
        save()
    }

    function save() {
        Requests.write("disk-ready", complete ? "1" : "0")
        Requests.write("answer-disk", complete
                       ? JSON.stringify(Logic.answer(disk, option, keep, encrypt.checked, lang)) : "{}")
        // root's own folder, a 0600 file; the job takes it away as soon as it
        // has read it, and the session empties it whenever Setup ends
        Requests.secret("answer-disk-passphrase", complete && encrypt.checked ? pass.text : "")
    }
    onCompleteChanged: save()

    ButtonGroup { id: picks }

    Flickable {
        id: scroller
        anchors.fill: parent
        clip: true
        contentHeight: column.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {
            policy: scroller.contentHeight > scroller.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
        }

        ColumnLayout {
            id: column
            width: scroller.width - 12
            spacing: 8

            // still reading the disks
            RowLayout {
                visible: page.scanning
                spacing: 12
                ProgressRing { implicitWidth: 24; implicitHeight: 24 }
                Text {
                    text: S.t(page.lang, "diskScanning")
                    font: Theme.body
                    color: Theme.textSecondary
                }
            }

            // no disk Raye can use
            Text {
                Layout.fillWidth: true
                visible: !page.scanning && page.usable.length === 0
                text: S.t(page.lang, "diskNone")
                font: Theme.body
                color: Theme.textPrimary
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: page.disks.filter(d => d.blocked && d.blocked !== "live")
                Text {
                    required property var modelData
                    Layout.fillWidth: true
                    text: S.t(page.lang, "diskShare", [Logic.diskLine(modelData, page.lang), Logic.blockedText(modelData.blocked, page.lang)])
                    font: Theme.caption
                    color: Theme.textTertiary
                    wrapMode: Text.WordWrap
                }
            }

            // which disk, when there is more than one
            Text {
                Layout.fillWidth: true
                visible: page.usable.length === 1
                text: page.disk ? Logic.diskLine(page.disk, page.lang) : ""
                font: Theme.bodyStrong
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
            Flow {
                Layout.fillWidth: true
                visible: page.usable.length > 1
                spacing: 8
                Repeater {
                    model: page.usable
                    SubtleButton {
                        required property var modelData
                        required property int index
                        text: Logic.diskLine(modelData, page.lang)
                        accent: index === page.diskIndex
                        onClicked: page.choose(index)
                    }
                }
            }

            // the choices
            Repeater {
                model: page.options
                ChoiceCard {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    Layout.topMargin: 2
                    padding: 10
                    checkable: true
                    showRadio: true
                    ButtonGroup.group: picks
                    checked: index === page.optionIndex
                    title: Logic.title(modelData, page.disk, page.lang)
                    description: Logic.line(modelData, page.disk, page.lang)
                    danger: Logic.deletes(modelData, page.disk)
                    onClicked: {
                        // the click checked the card; what is picked says if it stays
                        checked = Qt.binding(() => index === page.optionIndex)
                        page.ask(index)
                    }
                }
            }

            // how much each gets, when Windows is made smaller
            ColumnLayout {
                Layout.fillWidth: true
                visible: page.option !== null && page.option.mode === "shrink"
                spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: page.option ? S.t(page.lang, "diskShare", [Logic.systemName(page.option, page.lang), Logic.size(page.keep, page.lang)]) : ""
                        font: Theme.caption
                        color: Theme.textSecondary
                    }
                    Text {
                        text: page.option ? S.t(page.lang, "diskShare", ["Raye", Logic.size(page.option.total - page.keep, page.lang)]) : ""
                        font: Theme.caption
                        color: Theme.textPrimary
                    }
                }
                T.Slider {
                    id: slider
                    Layout.fillWidth: true
                    implicitHeight: 28
                    from: page.option && page.option.mode === "shrink" ? page.option.keepMin : 0
                    to: page.option && page.option.mode === "shrink" ? page.option.keepMax : 1
                    stepSize: Logic.GIB
                    snapMode: T.Slider.NoSnap
                    value: page.keep
                    Accessible.name: S.t(page.lang, "diskSlider")
                    onMoved: {
                        // whole MiB, the unit the install works in
                        page.keep = Math.floor(value / Logic.MIB) * Logic.MIB
                        page.save()
                    }
                    background: Rectangle {
                        x: slider.leftPadding
                        y: slider.topPadding + (slider.availableHeight - height) / 2
                        width: slider.availableWidth
                        height: 4
                        radius: 2
                        color: Theme.accent
                        Rectangle {
                            width: slider.visualPosition * parent.width
                            height: parent.height
                            radius: 2
                            color: Qt.alpha(Theme.textSecondary, 0.55)
                        }
                    }
                    handle: Rectangle {
                        x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                        y: slider.topPadding + (slider.availableHeight - height) / 2
                        width: 20
                        height: 20
                        radius: 10
                        color: Theme.textOnAccent
                        border.color: Theme.accent
                        border.width: slider.visualFocus ? 3 : 2
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: Logic.shrinkNote(page.option, page.lang)
                    font: Theme.caption
                    color: Theme.textTertiary
                    wrapMode: Text.WordWrap
                }
            }

            // why something is not offered
            Repeater {
                model: page.disk ? page.disk.refused : []
                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: why.implicitHeight + 16
                    radius: Theme.radiusControl
                    color: Qt.alpha(Theme.caution, 0.10)
                    border.color: Qt.alpha(Theme.caution, 0.35)
                    Text {
                        id: why
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 10 }
                        text: Logic.refusedText(modelData, page.lang)
                        font: Theme.caption
                        color: Theme.textPrimary
                        wrapMode: Text.WordWrap
                    }
                }
            }

            // what is there now, then, once something is chosen, what will be
            DiskBar {
                Layout.fillWidth: true
                Layout.topMargin: 4
                visible: page.picture !== null && page.picture.before.length > 0 && page.option === null
                title: S.t(page.lang, "diskNow")
                lang: page.lang
                parts: page.picture ? page.picture.before : []
                total: page.picture ? page.picture.total : 1
            }
            DiskBar {
                Layout.fillWidth: true
                visible: page.picture !== null && page.picture.after.length > 0
                title: S.t(page.lang, "diskAfter")
                lang: page.lang
                parts: page.picture ? page.picture.after : []
                total: page.picture ? page.picture.total : 1
            }

            // encryption
            CheckBox {
                id: encrypt
                objectName: "encrypt"
                Layout.topMargin: 4
                visible: page.disk !== null
                text: S.t(page.lang, "diskEncrypt")
                onToggled: { page.save(); if (checked) pass.forceActiveFocus() }
            }
            GridLayout {
                Layout.fillWidth: true
                Layout.topMargin: 4
                visible: encrypt.checked
                columns: 2
                columnSpacing: 12
                rowSpacing: 6
                FieldLabel {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    text: S.t(page.lang, "diskPassLabel")
                    field: pass
                }
                FieldLabel {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    text: S.t(page.lang, "diskPassAgainLabel")
                    field: again
                }
                PasswordField {
                    id: pass
                    objectName: "password"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Accessible.name: S.t(page.lang, "diskPassLabel")
                    error: page.passShown !== "" && text.length < Logic.PASSPHRASE_MINIMUM
                    onTextChanged: page.save()
                }
                PasswordField {
                    id: again
                    objectName: "passwordAgain"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Accessible.name: S.t(page.lang, "diskPassAgainLabel")
                    error: page.passShown !== "" && pass.text.length >= Logic.PASSPHRASE_MINIMUM
                    errorText: page.passShown
                    onTextChanged: page.save()
                }
            }
            Text {
                objectName: "passwordLine"
                Layout.fillWidth: true
                visible: encrypt.checked
                text: page.passShown || S.t(page.lang, "diskEncryptLine")
                font: Theme.caption
                color: page.passShown ? Theme.error : Theme.textTertiary
                wrapMode: Text.WordWrap
            }

            LinkButton {
                visible: !page.scanning
                text: S.t(page.lang, "diskLookAgain")
                onClicked: page.lookAgain()
            }
        }
    }

    // "Delete Arch Linux?": a window of its own over the whole screen, so
    // nothing behind it can be clicked while it asks
    Overlay {
        id: confirmBox
        over: page
        title: page.question ? page.question.title : ""
        onVisibleChanged: if (!visible && page.asking >= 0) page.answerQuestion(false)

        Rectangle {
            id: confirmCard
            anchors.centerIn: parent
            width: Math.min(480, parent.width - 48)
            height: box.implicitHeight + 48
            radius: Theme.radiusCard
            color: Theme.backgroundBottom
            border.color: Theme.surfaceStroke
            focus: true
            Keys.onEscapePressed: page.answerQuestion(false)
            MouseArea { anchors.fill: parent }
            Accessible.role: Accessible.AlertMessage
            Accessible.name: page.question ? page.question.title : ""

            ColumnLayout {
                id: box
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 24 }
                spacing: 12
                Text {
                    objectName: "confirmTitle"
                    Layout.fillWidth: true
                    text: page.question ? page.question.title : ""
                    font: Theme.subtitle
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.Heading
                }
                Text {
                    objectName: "confirmText"
                    Layout.fillWidth: true
                    text: page.question ? page.question.text : ""
                    font: Theme.body
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 12
                    spacing: 8
                    Item { Layout.fillWidth: true }
                    PrimaryButton {
                        objectName: "confirmYes"
                        Layout.minimumWidth: 120
                        text: page.question ? page.question.button : ""
                        onClicked: page.answerQuestion(true)
                    }
                    SubtleButton {
                        objectName: "confirmNo"
                        Layout.minimumWidth: 120
                        text: S.t(page.lang, "confirmCancel")
                        onClicked: page.answerQuestion(false)
                    }
                }
            }
        }
    }
}
