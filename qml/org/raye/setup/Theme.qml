// The look of the Raye setup: the start app, the Calamares pages and the
// welcome after the first sign-in. Colours, motion and fonts come from
// the Raye tokens (org.raye.ui); this file only adds what setup draws
// differently: 40 px controls, the bigger type of full-screen pages and
// the surfaces over the night background.
//
// Setup is always drawn at night, whatever the colour scheme says, so the
// first use of Theme pins the tokens to night (unless the app pinned them
// already).
//
//   Text { font: Theme.title; color: Theme.textPrimary; text: ... }
pragma Singleton

import QtQuick
import org.raye.ui

QtObject {
    id: theme

    Component.onCompleted: {
        if (Tokens.forceMode === "")
            Tokens.forceMode = "night"
    }

    // --- switches the apps set --------------------------------------

    // Fades only, no slide. Follows "no animations"; the accessibility
    // menu of setup can turn it on too.
    property bool reducedMotion: Tokens.animationsOff
    // "en" or "fr": the few words the module itself shows or reads out
    property string language: Qt.locale().name.startsWith("fr") ? "fr" : "en"

    // --- pictures -------------------------------------------------------
    readonly property var illustrationNames: ["language", "keyboard", "choose", "network", "disk", "account", "summary", "install", "done", "error", "key", "privacy", "look", "usb", "apps", "desktop"]

    // --- colours (night) -----------------------------------------------
    // One flat grey behind everything, the desktop's own base colour: the
    // violet is kept for the selection and the main button.
    readonly property color background: Tokens.bgBase
    readonly property color backgroundTop: background
    readonly property color backgroundBottom: background

    readonly property color surface: Tokens.bgLayerSolid
    readonly property color surfaceStroke: Qt.rgba(1, 1, 1, 0.07)
    // the picture's side of a card
    readonly property color pictureSide: Qt.rgba(1, 1, 1, 0.025)

    readonly property color controlFill: Qt.rgba(1, 1, 1, 0.06)
    readonly property color controlFillHover: Qt.rgba(1, 1, 1, 0.09)
    readonly property color controlFillPressed: Qt.rgba(1, 1, 1, 0.04)
    readonly property color controlFillDisabled: Qt.rgba(1, 1, 1, 0.03)
    readonly property color controlStroke: Qt.rgba(1, 1, 1, 0.10)
    readonly property color inputActive: Tokens.fillInputActive

    readonly property color accent: Tokens.accent
    readonly property color accentHover: Tokens.accentHover
    readonly property color accentPressed: Tokens.accentPressed
    readonly property color accentDisabled: Tokens.accentDisabled
    readonly property color accentText: Tokens.accentText
    readonly property color textOnAccent: Tokens.textOnAccent
    readonly property color selected: Tokens.fillSubtleSelected

    readonly property color textPrimary: Tokens.textPrimary
    readonly property color textSecondary: Tokens.textSecondary
    readonly property color textTertiary: Tokens.textTertiary
    readonly property color textDisabled: Tokens.textDisabled
    readonly property color error: Tokens.statusCritical
    readonly property color success: Tokens.statusSuccess
    readonly property color caution: Tokens.statusCaution
    readonly property color strokeStrong: Tokens.strokeStrong

    // --- sizes ----------------------------------------------------------
    readonly property int controlHeight: 40         // setup pages
    readonly property int dialogControlHeight: 32   // dialogs on top of them
    readonly property real radiusControl: Tokens.radiusControl
    readonly property real radiusCard: Tokens.radiusOverlay
    readonly property int slide: 40                 // page entrance, px

    // --- type, pixel sizes ---------------------------------------------
    readonly property string displayFamily: Tokens.title.family
    readonly property string textFamily: Tokens.body.family
    readonly property font display: Qt.font({ family: displayFamily, pixelSize: 40, weight: 600 })
    readonly property font title: Qt.font({ family: displayFamily, pixelSize: 28, weight: 600 })
    readonly property font titleLarge: Qt.font({ family: displayFamily, pixelSize: 40, weight: 600 })
    readonly property font subtitle: Qt.font({ family: textFamily, pixelSize: 20, weight: 600 })
    readonly property font bodyLarge: Qt.font({ family: textFamily, pixelSize: 18, weight: 400 })
    readonly property font body: Qt.font({ family: textFamily, pixelSize: 14, weight: 400 })
    readonly property font bodyStrong: Qt.font({ family: textFamily, pixelSize: 14, weight: 600 })
    readonly property font button: Qt.font({ family: textFamily, pixelSize: 14, weight: 500 })
    readonly property font caption: Qt.font({ family: textFamily, pixelSize: 12, weight: 400 })
    // the name over a text box
    readonly property font label: Qt.font({ family: textFamily, pixelSize: 13, weight: 500 })

    // Title 28 on a normal screen, 40 from 1600 px wide
    function titleFor(width) {
        return width >= 1600 ? titleLarge : title
    }

    // --- motion ---------------------------------------------------------
    readonly property int durationEnter: Tokens.durationNormal      // 250
    readonly property int durationExit: Tokens.durationExit         // 167
    readonly property int durationHover: Tokens.durationFaster      // 83
    readonly property int durationMove: Tokens.durationNormal       // pills, dots
    readonly property var bezierEnter: Tokens.bezierDecelerate      // (0,0,0,1)

    // --- the module's own words -----------------------------------------
    readonly property var _words: ({
        en: {
            showPassword: "Show password",
            hidePassword: "Hide password",
            step: "Step %1 of %2",
            busy: "Working"
        },
        fr: {
            showPassword: "Afficher le mot de passe",
            hidePassword: "Masquer le mot de passe",
            step: "Étape %1 sur %2",
            busy: "En cours"
        }
    })

    function text(key) {
        const words = _words[language] || _words.en
        return words[key] !== undefined ? words[key] : _words.en[key]
    }
}
