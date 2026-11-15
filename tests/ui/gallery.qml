// Everything org.raye.setup has, on one screen, to look at:
//
//   tests/ui/run-gallery.sh [--fr] [--page controls|pictures|frame|edge] [--reduced]
//
// run-gallery.sh lays the module out the way the package installs it
// (the pictures inside the module folder) and starts this file with qml6.
import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Layouts
import QtQuick.Window
import org.raye.ui as Ui
import org.raye.setup

Window {
    id: win

    readonly property var args: Qt.application.arguments
    function arg(name, fallback) {
        const i = args.indexOf(name)
        return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback
    }
    readonly property bool fr: args.indexOf("--fr") >= 0
    readonly property string page: arg("--page", "controls")

    width: Screen.width > 0 ? Screen.width : 1280
    height: Screen.height > 0 ? Screen.height : 800
    visible: true
    color: Theme.backgroundTop
    title: "org.raye.setup"

    Component.onCompleted: {
        Theme.language = fr ? "fr" : "en"
        if (args.indexOf("--reduced") >= 0)
            Theme.reducedMotion = true
    }

    readonly property var words: fr ? ({
        buttons: "Boutons", fields: "Champs", choices: "Choix", lists: "Listes", busy: "Patience",
        next: "Suivant", back: "Retour", install: "Installer", disabled: "Désactivé", change: "Modifier",
        name: "Nom complet", password: "Mot de passe", wrong: "Ce nom est déjà pris", saved: "J'ai enregistré ma clé de récupération",
        english: "English", french: "Français", canada: "Canada", installRaye: "Installer Raye",
        installLine: "Raye remplace ou côtoie ce qui est sur ce PC", tryRaye: "Essayer Raye d'abord",
        tryLine: "Rien ne change sur cet ordinateur", erase: "Effacer le disque et installer Raye",
        eraseLine: "Tout ce qui est sur le disque 1 sera effacé", along: "Installer à côté de Windows",
        alongLine: "Vous choisissez au démarrage",
        layouts: ["Français (Canada)", "Anglais (États-Unis)", "Français (France)", "Anglais (Canada, multilingue)"],
        recommended: "Recommandé", keyboardTitle: "Est-ce la bonne disposition de clavier ?",
        keyboardLine: "Essayez-la ici. Vous pourrez en ajouter une autre plus tard.", tryHere: "Tapez ici pour essayer votre clavier",
        showAll: "Afficher toutes les dispositions", steps: "Étapes", countdown: "Redémarrage", pictures: "Images",
        networkTitle: "Connectons-vous à un réseau", networkLine: "Raye règle l'heure tout seul une fois connecté."
    }) : ({
        buttons: "Buttons", fields: "Fields", choices: "Choices", lists: "Lists", busy: "Busy",
        next: "Next", back: "Back", install: "Install", disabled: "Disabled", change: "Change",
        name: "Full name", password: "Password", wrong: "That name is already taken", saved: "I saved my recovery key",
        english: "English", french: "Français", canada: "Canada", installRaye: "Install Raye",
        installLine: "Raye replaces or sits next to what is on this PC", tryRaye: "Try Raye first",
        tryLine: "Nothing changes on this computer", erase: "Erase the disk and install Raye",
        eraseLine: "Everything on Disk 1 will be erased", along: "Install next to Windows",
        alongLine: "You pick one each time the PC starts",
        layouts: ["French (Canada)", "English (US)", "French (France)", "English (Canada, multilingual)"],
        recommended: "Recommended", keyboardTitle: "Is this the right keyboard layout?",
        keyboardLine: "Try it here. You can add another one later.", tryHere: "Type here to try your keyboard",
        showAll: "Show all layouts", steps: "Steps", countdown: "Restarting", pictures: "Pictures",
        networkTitle: "Let's connect you to a network", networkLine: "Raye sets the clock by itself once you're online."
    })

    component Heading: Text {
        font: Theme.subtitle
        color: Theme.textPrimary
        Layout.topMargin: 8
    }

    SetupBackground {
        anchors.fill: parent
        visible: win.page === "controls" || win.page === "pictures"
    }

    // --- every control ----------------------------------------------------
    Flickable {
        visible: win.page === "controls"
        anchors.fill: parent
        contentHeight: grid.implicitHeight + 64
        clip: true

        GridLayout {
            id: grid
            x: 40
            y: 32
            width: win.width - 80
            columns: 2
            columnSpacing: 56
            rowSpacing: 12

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: 12

                Text { text: "org.raye.setup"; font: Theme.display; color: Theme.textPrimary }

                Heading { text: win.words.buttons }
                RowLayout {
                    spacing: 8
                    SubtleButton { text: win.words.back }
                    PrimaryButton { id: firstButton; text: win.words.next }
                    PrimaryButton { text: win.words.disabled; enabled: false }
                    SubtleButton { text: win.words.disabled; enabled: false }
                    LinkButton { text: win.words.change }
                }
                RowLayout {
                    spacing: 8
                    SubtleButton { text: win.words.back; compact: true }
                    PrimaryButton { text: win.words.install; compact: true }
                }

                Heading { text: win.words.fields }
                TextField { Layout.fillWidth: true; placeholderText: win.words.name }
                TextField { Layout.fillWidth: true; text: "Raye"; error: true; errorText: win.words.wrong }
                Text { text: win.words.wrong; font: Theme.caption; color: Theme.error }
                PasswordField { id: pw; Layout.fillWidth: true; placeholderText: win.words.password; text: "night-sky-42" }
                PasswordField { Layout.fillWidth: true; placeholderText: win.words.password; text: "night-sky-42"; revealed: true }
                TextField { Layout.fillWidth: true; placeholderText: win.words.disabled; enabled: false }
                RowLayout {
                    spacing: 24
                    CheckBox { text: win.words.saved; checked: true }
                    CheckBox { text: win.words.saved }
                }
                CheckBox { text: win.words.disabled; enabled: false }

                Heading { text: win.words.busy }
                RowLayout {
                    spacing: 32
                    ProgressRing { }
                    ProgressRing { size: 64 }
                    ProgressRing { size: 64; value: 0.65 }
                    StepDots { count: 5; current: 2 }
                    Ui.Switch { text: "Wi-Fi"; checked: true }
                }
            }

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: 12

                Heading { text: win.words.choices }
                RowLayout {
                    spacing: 12
                    QQC.ButtonGroup { id: langs }
                    ChoiceCard { Layout.fillWidth: true; title: win.words.english; description: win.words.canada; checkable: true; checked: !win.fr; QQC.ButtonGroup.group: langs }
                    ChoiceCard { Layout.fillWidth: true; title: win.words.french; description: win.words.canada; checkable: true; checked: win.fr; QQC.ButtonGroup.group: langs }
                }
                ChoiceCard {
                    Layout.fillWidth: true
                    accent: true
                    illustration: "install"
                    illustrationSize: 72
                    title: win.words.installRaye
                    description: win.words.installLine
                }
                ChoiceCard {
                    Layout.fillWidth: true
                    illustration: "choose"
                    illustrationSize: 72
                    title: win.words.tryRaye
                    description: win.words.tryLine
                }
                QQC.ButtonGroup { id: disk }
                ChoiceCard { Layout.fillWidth: true; showRadio: true; checkable: true; checked: true; title: win.words.erase; description: win.words.eraseLine; QQC.ButtonGroup.group: disk }
                ChoiceCard { Layout.fillWidth: true; showRadio: true; checkable: true; title: win.words.along; description: win.words.alongLine; QQC.ButtonGroup.group: disk }
                ChoiceCard { Layout.fillWidth: true; showRadio: true; checkable: true; enabled: false; title: win.words.disabled; QQC.ButtonGroup.group: disk }

                Heading { text: win.words.lists }
                ListView {
                    id: list
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4 * 40
                    model: win.words.layouts
                    currentIndex: 0
                    interactive: false
                    delegate: ListRow {
                        required property int index
                        required property string modelData
                        width: ListView.view.width
                        text: modelData
                        detail: index === 0 ? win.words.recommended : ""
                        highlighted: ListView.isCurrentItem
                        onClicked: ListView.view.currentIndex = index
                    }
                }
            }
        }
    }

    // --- all the pictures --------------------------------------------------
    GridLayout {
        visible: win.page === "pictures"
        anchors.centerIn: parent
        columns: 5
        columnSpacing: 16
        rowSpacing: 4
        Repeater {
            model: Theme.illustrationNames
            ColumnLayout {
                required property string modelData
                spacing: 0
                Illustration {
                    Layout.alignment: Qt.AlignHCenter
                    name: modelData
                    size: Math.min((win.width - 160) / 5, (win.height - 140) / 3 - 24)
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: modelData
                    font: Theme.caption
                    color: Theme.textSecondary
                }
            }
        }
    }

    // --- a page in the frame ------------------------------------------------
    SetupFrame {
        visible: win.page === "frame" || win.page === "edge"
        anchors.fill: parent
        card: win.page === "frame"
        illustration: win.page === "frame" ? "keyboard" : "network"

        footerLeft: [
            SubtleButton { compact: true; text: win.fr ? "FR" : "EN" },
            SubtleButton { compact: true; text: "Wi-Fi" }
        ]
        footerRight: [
            SubtleButton { compact: true; text: win.fr ? "Arrêter" : "Power" }
        ]

        leftContent: [
            ColumnLayout {
                visible: win.page === "edge"
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 48 }
                spacing: 8
                Text { Layout.fillWidth: true; text: win.words.networkTitle; font: Theme.titleFor(win.width); color: Theme.textPrimary; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: win.words.networkLine; font: Theme.bodyLarge; color: Theme.textSecondary; wrapMode: Text.WordWrap }
            }
        ]

        PageEnter {
            anchors.fill: parent

            ColumnLayout {
                anchors.fill: parent
                spacing: 12
                Text {
                    visible: win.page === "frame"
                    Layout.fillWidth: true
                    text: win.words.keyboardTitle
                    font: Theme.titleFor(win.width)
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                }
                Text {
                    visible: win.page === "frame"
                    Layout.fillWidth: true
                    text: win.words.keyboardLine
                    font: Theme.body
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4 * 40
                    Layout.topMargin: 8
                    model: win.words.layouts
                    currentIndex: 0
                    interactive: false
                    delegate: ListRow {
                        required property int index
                        required property string modelData
                        width: ListView.view.width
                        text: modelData
                        detail: index === 0 ? win.words.recommended : ""
                        highlighted: ListView.isCurrentItem
                        onClicked: ListView.view.currentIndex = index
                    }
                }
                LinkButton { text: win.words.showAll }
                TextField { Layout.fillWidth: true; placeholderText: win.words.tryHere }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true
                    StepDots { count: 5; current: 1 }
                    Item { Layout.fillWidth: true }
                    SubtleButton { text: win.words.back }
                    PrimaryButton { text: win.words.next }
                }
            }
        }
    }
}
