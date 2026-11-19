// Raye Setup, first page: the language, from every language Calamares is
// translated into, each written in its own name, with a search box like
// Windows. Picking one changes Setup's language at once, and it becomes the
// language of the new system (its language pack comes with the install,
// see modules/packages.conf).
// Under it, only when there is something to say: what keeps this PC from
// running Raye (disk, memory, power), an old processor (raye-cpu-check),
// and what to fix in Windows before installing next to it (raye-preflight).

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
    step: "language"
    illustration: "language"
    title: S.t(lang, "languageTitle")
    text: S.t(lang, "languageText")

    property var findings: []
    property var cpu: ({})
    readonly property var cpuNotice: S.cpuNotice(cpu.verdict)
    // Every language Calamares is translated into, with a search box. Off
    // for the beta (the owner's call): English and French only until the
    // language packs and the rest of Raye's words are ready.
    readonly property bool everyLanguage: false
    Component.onCompleted: {
        Requests.preflight(found => findings = found)
        Requests.cpu(found => { if (found.verdict) cpu = found })
    }
    // Raye's own words exist in English and French; Setup is in English
    // for the rest, apart from what Calamares translates itself
    readonly property bool rayeWords: lang === "fr" || code === "en"
    property string code: S.code(Qt.locale())

    function choose(index) {
        config.localeIndex = index
        code = S.code(Qt.locale())
        lang = S.current(Qt.locale())
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        TextField {
            id: search
            Layout.fillWidth: true
            visible: page.everyLanguage
            placeholderText: S.t(page.lang, "languageSearch")
            Accessible.name: placeholderText
        }

        // every language Calamares is translated into, each in its own name
        ListView {
            id: languages
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            focus: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: page.title
            model: config.languagesModel
            currentIndex: config.localeIndex
            Component.onCompleted: positionViewAtIndex(currentIndex, ListView.Center)

            delegate: ListRow {
                required property int index
                required property string label
                required property string englishLabel
                readonly property bool offered: page.everyLanguage || englishLabel === "English" || englishLabel === "French"
                readonly property bool matches: offered && (search.text === ""
                    || Countries.plain(label).indexOf(Countries.plain(search.text)) >= 0
                    || Countries.plain(englishLabel).indexOf(Countries.plain(search.text)) >= 0)
                width: ListView.view.width
                visible: matches
                height: matches ? implicitHeight : 0
                text: S.languageRow(label, englishLabel)
                detail: englishLabel !== text ? englishLabel : ""
                highlighted: index === config.localeIndex
                onClicked: page.choose(index)
            }
            Keys.onReturnPressed: page.choose(currentIndex)
        }

        Text {
            Layout.fillWidth: true
            visible: !page.rayeWords
            text: "Some of Setup is shown in English."
            font: Theme.caption
            color: Theme.textTertiary
            wrapMode: Text.WordWrap
        }

        // what keeps this PC from running Raye
        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: 8
            visible: !config.requirementsModel.satisfiedRequirements
            implicitHeight: needs.implicitHeight + 24
            radius: Theme.radiusControl
            color: Qt.alpha(config.requirementsModel.satisfiedMandatory ? Theme.caution : Theme.error, 0.12)
            border.color: Qt.alpha(config.requirementsModel.satisfiedMandatory ? Theme.caution : Theme.error, 0.4)
            ColumnLayout {
                id: needs
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 4
                Text {
                    visible: !config.requirementsModel.satisfiedMandatory
                    Layout.fillWidth: true
                    text: S.t(page.lang, "notReadyTitle")
                    font: Theme.bodyStrong
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: config.unsatisfiedRequirements
                    Text {
                        required property string negatedText
                        Layout.fillWidth: true
                        text: "• " + negatedText
                        font: Theme.body
                        color: Theme.textPrimary
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        // an old processor: said, never in the way
        Rectangle {
            readonly property color tone: page.cpuNotice && page.cpuNotice.severe ? Theme.error : Theme.caution
            Layout.fillWidth: true
            Layout.topMargin: 8
            visible: page.cpuNotice !== null
            implicitHeight: processor.implicitHeight + 24
            radius: Theme.radiusControl
            color: Qt.alpha(tone, 0.10)
            border.color: Qt.alpha(tone, 0.35)
            ColumnLayout {
                id: processor
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 4
                Text {
                    Layout.fillWidth: true
                    text: page.cpuNotice ? S.t(page.lang, page.cpuNotice.title) : ""
                    font: Theme.bodyStrong
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true
                    text: page.cpuNotice ? S.t(page.lang, page.cpuNotice.text) : ""
                    font: Theme.body
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
            }
        }

        // what to fix in Windows first
        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: 8
            visible: S.warnings(page.findings).length > 0
            implicitHeight: before.implicitHeight + 24
            radius: Theme.radiusControl
            color: Qt.alpha(Theme.caution, 0.10)
            border.color: Qt.alpha(Theme.caution, 0.35)
            ColumnLayout {
                id: before
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 6
                Text {
                    Layout.fillWidth: true
                    text: S.t(page.lang, S.beforeKey(page.findings))
                    font: Theme.bodyStrong
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: S.warnings(page.findings)
                    Text {
                        required property string modelData
                        Layout.fillWidth: true
                        text: S.t(page.lang, S.findingKey(modelData))
                        font: Theme.body
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: S.t(page.lang, "eraseStillFine")
                    font: Theme.caption
                    color: Theme.textTertiary
                    wrapMode: Text.WordWrap
                }
            }
        }

    }
}
