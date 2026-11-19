// The pages of Raye Setup that say what will happen to the PC, loaded from
// the branding folder as Calamares loads them, against fakes of Calamares and
// of the network component (tests/ui/fakes).
//
// Three of them showed wrong on the 2026-11-07 image, on a clean run:
//  - the network page was blank on a PC online by cable;
//  - "Ready to install" did not say the disk would be encrypted;
//  - it spoke of Canadian English after "American English" was picked, and
//    of "Set flags on 1024MiB fat32 partition to boot".
import QtQuick
import QtTest
import io.calamares.core 1.0
import org.kde.plasma.networkmanagement as PlasmaNM
import org.raye.setup

import "../../etc/calamares/branding/raye/strings.js" as S
import "../../etc/calamares/branding/raye/components/Summary.js" as Summary

Item {
    id: root
    width: 1280
    height: 800

    // Calamares gives each page this; a Loader's page sees it the same way
    property var config: QtObject {
        property var summaryModel: entries

        // localeq's Config as far as the region page and the formats go:
        // the language follows every location call, the formats only a
        // change of place, and never once they were set by hand
        property var currentLocation: null
        property string currentLanguageCode: ""
        property string currentLCCode: ""
        property bool formatsByHand: false
        property int moves: 0
        property var regionModel: []
        property var regionalZonesModel: zonesOfRegion
        readonly property var countryOf: ({ "America/Toronto": "CA", "America/New_York": "US",
                                            "Europe/London": "GB", "Europe/Paris": "FR" })
        function automatic(tz) {
            const conf = Global.value("localeConf")
            return String(conf.LANG).split(/[_.]/)[0] + "_" + countryOf[tz] + ".UTF-8"
        }
        function where() { return currentLocation ? currentLocation.region + "/" + currentLocation.zone : "" }
        function setCurrentLocation(a, b) {
            const tz = b === undefined ? a : a + "/" + b
            const moved = tz !== where()
            if (moved)
                currentLocation = { region: tz.split("/")[0], zone: tz.split("/")[1] }
            currentLanguageCode = automatic(tz)
            if (moved) {
                moves += 1
                if (!formatsByHand)
                    currentLCCode = automatic(tz)
            }
        }
        // LocaleQmlViewStep::onActivate
        function activate() {
            if (!currentLocation)
                setCurrentLocation("America/Toronto")
            else
                currentLanguageCode = automatic(where())
        }
        function setLCLocaleExplicitly(lc) {
            formatsByHand = true
            currentLCCode = lc
        }
    }
    ListModel {
        id: zonesOfRegion
        property string region
    }
    readonly property string pages: "../../etc/calamares/branding/raye/pages/"

    ListModel { id: entries }

    Loader {
        id: loader
        anchors.fill: parent
    }

    // The raw text of the run on 2026-11-07, encrypted, in English
    readonly property string diskEncrypted:
        "<strong>Erase</strong> disk <strong>/dev/sda</strong> (QEMU HARDDISK) and install Raye 0.1 Beta<br/>"
        + "Create new <strong>1024MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries EFI<br/>"
        + "Set flags on 1024MiB <strong>fat32</strong> partition to <strong>boot</strong><br/>"
        + "Create new <strong>2048MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries raye_boot<br/>"
        + "Create new <strong>62461MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries raye<br/>"
        + "Install Raye on <strong>new</strong> btrfs system partition"
    readonly property string diskPlain:
        "<strong>Erase</strong> disk <strong>/dev/sda</strong> (QEMU HARDDISK) and install Raye 0.1 Beta<br/>"
        + "Create new <strong>63485MiB</strong> partition on <strong>/dev/sda</strong> (QEMU HARDDISK) with entries raye"

    // every word on screen: what a person can read
    function shown(item, out) {
        out = out || []
        if (!item || !item.visible)
            return out
        if (item.text !== undefined && String(item.text) !== "" && item.width > 0 && item.height > 0)
            out.push(String(item.text))
        for (let i = 0; i < item.children.length; ++i)
            shown(item.children[i], out)
        if (item.contentItem && item.contentItem !== item)
            shown(item.contentItem, out)
        return out
    }
    function find(item, text) {
        if (!item)
            return null
        if (item.visible && item.clicked !== undefined && String(item.text) === text)
            return item
        for (let i = 0; i < item.children.length; ++i) {
            const hit = find(item.children[i], text)
            if (hit)
                return hit
        }
        return item.contentItem && item.contentItem !== item ? find(item.contentItem, text) : null
    }

    TestCase {
        name: "SetupPages"
        when: windowShown

        function load(file, step) {
            loader.source = ""
            ViewManager.currentStepIndex = S.steps.indexOf(step)
            loader.source = root.pages + file
            tryVerify(() => loader.status === Loader.Ready, 5000, "the page did not load: " + loader.sourceComponent)
            wait(50)
            return loader.item
        }
        function network(connectivity, wireless, wired, rows) {
            PlasmaNM.World.connectivity = connectivity
            PlasmaNM.World.wireless = wireless
            PlasmaNM.World.wired = wired
            PlasmaNM.World.rows = rows
            return load("Network.qml", "network")
        }
        function wiredRow(state) {
            return { Ssid: "", ConnectionPath: "/c/1", DevicePath: "/d/1", SpecificPath: "",
                     ConnectionState: state, SecurityType: PlasmaNM.Enums.NoneSecurity, Signal: 0 }
        }
        function wifiRow(ssid, state) {
            return { Ssid: ssid, ConnectionPath: state ? "/c/2" : "", DevicePath: "/d/2", SpecificPath: "/ap/1",
                     ConnectionState: state, SecurityType: 2, Signal: 80 }
        }
        function ready(language, encrypted) {
            entries.clear()
            entries.append({ title: "Location", message: "The system language will be set to Canadian English (Canada)." })
            Global.values = ({ locationRegion: "America",
                               locationZone: "Toronto", fullname: "Test Raye", hostname: "raye-test" })
            const page = load("Ready.qml", "ready")
            page.lang = language
            page.keyboard = "English (US)"
            // what the disk page left in answer-disk, read after the file's
            // absence here has been answered
            wait(50)
            page.install = "erase"
            page.diskLabel = "QEMU HARDDISK (/dev/sda)"
            page.diskDetails = "Everything on QEMU HARDDISK (/dev/sda) is deleted."
            page.encrypted = encrypted
            page.hostName = "raye-test"
            wait(50)
            return shown(page)
        }

        // ---- network page: once the network is connected the key box closes
        // (2026-11-15 photo: "Connected" with the key field still open under it)
        function test_a_connected_network_hides_its_key_field() {
            const page = network(4, true, false, [wifiRow("Home", PlasmaNM.Enums.Activated)])
            page.asking = "Home"
            wait(50)
            const words = shown(page)
            verify(words.indexOf(S.t(page.lang, "connect")) < 0, "the key field is still open: " + words)
        }

        // ---- network page: never blank

        function test_online_by_cable_says_so_with_the_cable_in_the_model() {
            const words = shown(network(4, false, true, [wiredRow(PlasmaNM.Enums.Activated)]))
            verify(words.indexOf(S.t("en", "wiredConnected")) >= 0, "nothing says the cable is in: " + words)
            verify(words.indexOf(S.t("en", "online")) >= 0, "nothing says the PC is online: " + words)
        }
        function named(item, name) {
            if (!item)
                return null
            if (item.objectName === name)
                return item
            for (let i = 0; i < item.children.length; ++i) {
                const hit = named(item.children[i], name)
                if (hit)
                    return hit
            }
            return null
        }
        function icons(item, out) {
            out = out || []
            if (!item || !item.visible)
                return out
            if (item.source !== undefined && item.isMask !== undefined)
                out.push(String(item.source))
            for (let i = 0; i < item.children.length; ++i)
                icons(item.children[i], out)
            return out
        }
        // On the 2026-11-08 image the cable card showed a screen: the icon
        // theme draws "network-wired" as a monitor. The cable is drawn here.
        function test_the_cable_card_shows_a_cable() {
            const page = network(4, false, true, [wiredRow(PlasmaNM.Enums.Activated)])
            const plug = named(page, "cablePlug")
            verify(plug !== null && plug.visible, "no cable drawn on the card")
            verify(plug.width > 0 && plug.height > 0)
            verify(icons(page).indexOf("network-wired") < 0, "the theme's screen icon is back")
        }
        function test_online_on_wifi_does_not_claim_a_cable() {
            const page = network(4, true, true, [wiredRow(0), wifiRow("Home", PlasmaNM.Enums.Activated)])
            compare(page.wifiInUse, "Home")
            const words = shown(page)
            verify(words.indexOf(S.t("en", "wiredConnected")) < 0, "a cable was claimed: " + words)
            verify(words.indexOf("Home") >= 0, "the network is not listed: " + words)
        }
        function test_offline_without_a_card_offers_to_go_on() {
            const words = shown(network(1, false, false, []))
            verify(words.indexOf(S.t("en", "noCard")) >= 0, words)
            verify(words.indexOf(S.t("en", "noInternet")) >= 0, words)
        }
        function test_offline_with_a_cable_port_offers_to_go_on() {
            const words = shown(network(0, false, true, [wiredRow(0)]))
            verify(words.indexOf(S.t("en", "noWifi")) >= 0, words)
            verify(words.indexOf(S.t("en", "noInternet")) >= 0, words)
        }
        function test_the_page_is_never_blank_in_any_state() {
            for (const connectivity of [0, 1, 2, 3, 4])
                for (const wireless of [false, true])
                    for (const wired of [false, true]) {
                        const rows = wired ? [wiredRow(connectivity === 4 ? PlasmaNM.Enums.Activated : 0)] : []
                        const page = network(connectivity, wireless, wired, rows)
                        const words = shown(page).filter(w => w !== page.title && w !== page.text)
                        verify(words.length > 0, "blank: connectivity " + connectivity
                               + ", wireless " + wireless + ", wired " + wired)
                    }
        }

        // ---- "Ready to install": says what will happen, in words

        function test_ready_says_the_disk_is_encrypted() {
            const words = ready("en", true)
            verify(words.indexOf(S.t("en", "readyEncryption")) >= 0, words)
            verify(words.indexOf(S.t("en", "readyEncrypted")) >= 0, words)
        }
        function test_ready_says_when_the_disk_is_not_encrypted() {
            const words = ready("en", false)
            verify(words.indexOf(S.t("en", "readyEncryption")) >= 0, words)
            verify(words.indexOf(S.t("en", "readyNotEncrypted")) >= 0, words)
        }
        function test_ready_in_french_too() {
            const words = ready("fr", true)
            verify(words.indexOf("Chiffrement") >= 0, words)
            verify(words.indexOf(S.t("fr", "readyEncrypted")) >= 0, words)
            verify(words.indexOf("Français") >= 0, words)
            verify(words.join(" ").indexOf("Toronto") >= 0, words)
        }
        function test_ready_names_the_language_that_was_picked() {
            const words = ready("en", true)
            verify(words.indexOf("English") >= 0, words)
            verify(words.join(" ").indexOf("Canadian") < 0, "another English than the one picked: " + words)
            verify(words.indexOf("Canada") >= 0, "the country goes with it: " + words)
        }
        function test_ready_speaks_no_jargon_until_asked() {
            const words = ready("en", true).join(" ")
            for (const jargon of ["fat32", "MiB", "Set flags", "partition to", "btrfs", "raye_boot", "ext4", "Set timezone"])
                verify(words.indexOf(jargon) < 0, "jargon on the page: " + jargon + " in " + words)
            verify(words.indexOf("QEMU HARDDISK (/dev/sda)") >= 0, "which disk? " + words)
        }
        function test_ready_keeps_the_details_behind_one_click() {
            ready("en", true)
            const link = root.find(loader.item, S.t("en", "readyDetailsShow"))
            verify(link !== null, "no link to the details")
            link.clicked()
            wait(50)
            verify(shown(loader.item).join(" ").indexOf("is deleted") >= 0, "the details did not open")
        }
        function test_ready_says_who_and_which_pc() {
            const words = ready("en", true)
            verify(words.indexOf("Test Raye") >= 0, words)
            verify(words.indexOf("raye-test") >= 0, words)
            verify(words.indexOf("English (US)") >= 0, words)
        }
        function test_erasing_still_has_its_red_line() {
            verify(ready("en", true).indexOf(S.t("en", "readyErase")) >= 0)
        }

        // ---- "Choose your desktop": KDE Plasma unless Hyprland is picked
        function desktop(lang) {
            const page = load("Desktop.qml", "desktop")
            page.lang = lang
            wait(50)
            return page
        }
        function card(page, name) {
            const hit = findObject(page, name)
            verify(hit !== null, "no card " + name)
            return hit
        }
        function findObject(item, name) {
            if (!item)
                return null
            if (item.objectName === name)
                return item
            for (let i = 0; i < item.children.length; ++i) {
                const hit = findObject(item.children[i], name)
                if (hit)
                    return hit
            }
            return null
        }
        function test_desktop_page_picks_kde_unless_told_otherwise_data() {
            return [{ tag: "en", lang: "en" }, { tag: "fr", lang: "fr" }]
        }
        function test_desktop_page_picks_kde_unless_told_otherwise(data) {
            const page = desktop(data.lang)
            compare(page.choice, "plasma")
            verify(card(page, "plasmaCard").checked)
            verify(!card(page, "hyprlandCard").checked)
            const words = shown(page)
            for (const key of ["desktopTitle", "desktopPlasma", "desktopPlasmaLine",
                               "desktopHyprland", "desktopHyprlandLine"])
                verify(words.indexOf(S.t(data.lang, key)) >= 0, key + " is not on the page")
            verify(words.indexOf(S.t(data.lang, "desktopBoth")) < 0, "KDE picked, but the page talks of switching")
        }
        function test_picking_hyprland_says_kde_stays() {
            const page = desktop("en")
            mouseClick(card(page, "hyprlandCard"))
            compare(page.choice, "hyprland")
            verify(card(page, "hyprlandCard").checked)
            verify(!card(page, "plasmaCard").checked)
            verify(shown(page).indexOf(S.t("en", "desktopBoth")) >= 0)
            mouseClick(card(page, "plasmaCard"))
            compare(page.choice, "plasma")
        }
        function test_hyprland_from_the_network_says_to_stay_online() {
            const page = desktop("fr")
            page.offline = "0"
            mouseClick(card(page, "hyprlandCard"))
            const line = findObject(page, "afterLine").text
            verify(line.indexOf(S.t("fr", "desktopDownload")) >= 0, line)
            page.offline = "1"
            verify(findObject(page, "afterLine").text.indexOf(S.t("fr", "desktopDownload")) < 0)
        }
        function test_the_keyboard_picks_a_desktop_too() {
            const page = desktop("en")
            const hypr = card(page, "hyprlandCard")
            hypr.forceActiveFocus()
            keyClick(Qt.Key_Space)
            compare(page.choice, "hyprland")
        }
        function test_ready_names_the_desktop() {
            const words = ready("en", true)
            verify(words.indexOf("KDE Plasma") >= 0, "no desktop on the summary: " + words)
            loader.item.desktop = "hyprland"
            wait(50)
            verify(shown(loader.item).indexOf("Hyprland") >= 0, "Hyprland picked, not on the summary")
            verify(shown(loader.item).indexOf(S.t("en", "readyDesktop")) >= 0)
        }
        function test_done_says_when_hyprland_could_not_be_added() {
            const page = load("Done.qml", "done")
            page.lang = "en"
            verify(shown(page).indexOf(S.t("en", "doneDesktopFallback")) < 0)
            page.desktopResult = "plasma-fallback"
            wait(50)
            verify(shown(page).indexOf(S.t("en", "doneDesktopFallback")) >= 0)
        }

        // ---- the region page: formats follow the language picked last

        // Setup as Calamares runs it: the language page, then the region page
        // (made once, and kept)
        function region(language) {
            Global.values = ({ localeConf: { LANG: language } })
            root.config.currentLocation = null
            root.config.formatsByHand = false
            root.config.moves = 0
            loader.source = ""
            ViewManager.currentStepIndex = S.steps.indexOf("language")
            loader.source = root.pages + "Region.qml"
            tryVerify(() => loader.status === Loader.Ready, 5000)
            // no time zone from the network here
            loader.item.located = true
            arrive(language)
            return loader.item
        }
        // back to the language page, pick one, then Next
        function arrive(language) {
            if (ViewManager.currentStepIndex !== S.steps.indexOf("language")) {
                ViewManager.currentStepIndex = S.steps.indexOf("language")
                ViewManager.currentStepChanged()
            }
            Global.values = ({ localeConf: { LANG: language } })
            root.config.activate()
            ViewManager.currentStepIndex = S.steps.indexOf("region")
            ViewManager.currentStepChanged()
            wait(20)
        }
        function test_formats_follow_the_language_data() {
            return [
                { tag: "fr-en", path: ["fr", "en"], formats: "en_CA.UTF-8" },
                { tag: "en-fr", path: ["en", "fr"], formats: "fr_CA.UTF-8" },
                { tag: "fr-en-fr", path: ["fr", "en", "fr"], formats: "fr_CA.UTF-8" },
                { tag: "en-fr-en", path: ["en", "fr", "en"], formats: "en_CA.UTF-8" },
            ]
        }
        function test_formats_follow_the_language(data) {
            region(data.path[0])
            for (const language of data.path.slice(1))
                arrive(language)
            compare(root.config.currentLCCode, data.formats)
            compare(root.config.currentLanguageCode, data.formats)
            compare(root.config.where(), "America/Toronto")
        }
        function test_formats_follow_the_language_in_another_country() {
            region("fr")
            root.config.setCurrentLocation("America/New_York")
            compare(root.config.currentLCCode, "fr_US.UTF-8")
            arrive("en")
            compare(root.config.currentLCCode, "en_US.UTF-8")
            compare(root.config.where(), "America/New_York")
        }
        function test_formats_set_by_hand_stay() {
            region("en")
            root.config.setLCLocaleExplicitly("en_GB.UTF-8")
            arrive("fr")
            compare(root.config.currentLCCode, "en_GB.UTF-8")
            compare(root.config.currentLanguageCode, "fr_CA.UTF-8")
            arrive("en")
            compare(root.config.currentLCCode, "en_GB.UTF-8")
        }
        function test_same_language_moves_nothing() {
            region("fr")
            const moves = root.config.moves
            arrive("fr")
            arrive("fr")
            compare(root.config.moves, moves, "the time zone moved for nothing")
            compare(root.config.currentLCCode, "fr_CA.UTF-8")
        }

        // ---- the Done page's button, in French

        Component {
            id: buttonMaker
            PrimaryButton {}
        }
        function test_a_button_grows_when_its_label_gets_longer() {
            const button = createTemporaryObject(buttonMaker, root, { text: "Restart now" })
            wait(50)
            button.text = "Redémarrer maintenant et encore un peu plus"
            wait(50)
            verify(button.implicitWidth > 240, "the button kept the width of its old label: " + button.implicitWidth)
        }

        // ---- the words behind it

        function test_the_language_list_says_english_not_american() {
            compare(S.languageRow("American English", "English"), "English")
            compare(S.languageRow("français", "French"), "Français")
        }
        function test_every_install_choice_has_words() {
            for (const c of ["erase", "alongside", "replace", "manual", ""])
                for (const lang of ["en", "fr"])
                    verify(S.t(lang, Summary.whatHappens(c)).indexOf("ready") !== 0, c)
        }
    }
}
