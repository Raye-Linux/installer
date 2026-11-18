// org.raye.setup: focus order, the states of each control, the pictures,
// the page entrance and reduced motion. Run by ctest (tests/ui).
//
// The second TestCase, "Words", runs the pure functions of the branding's
// strings.js. They live here because this is the only QML runner the
// repository has, and a second one would mean a new suite in iso/tools,
// which is another repository. A Python test cannot run them: they are
// JavaScript, and what matters is what they RETURN, not how they read.
import QtQuick
import QtQuick.Controls as QQC
import QtTest
import org.raye.ui as Ui
import org.raye.setup

import "../../etc/calamares/branding/raye/strings.js" as S

Item {
    id: root
    width: 1280
    height: 800

    function findByName(item, name) {
        if (!item)
            return null
        if (item.objectName === name)
            return item
        for (let i = 0; i < item.children.length; ++i) {
            const found = findByName(item.children[i], name)
            if (found)
                return found
        }
        return null
    }

    Column {
        id: page
        x: 20
        y: 20
        spacing: 8
        width: 600

        TextField { id: field; width: 400; placeholderText: "Full name" }
        PasswordField { id: password; width: 400; placeholderText: "Password" }
        CheckBox { id: check; text: "I saved my recovery key" }
        QQC.ButtonGroup { id: group }
        ChoiceCard { id: cardA; width: 400; title: "English"; checkable: true; QQC.ButtonGroup.group: group }
        ChoiceCard { id: cardB; width: 400; title: "Français"; checkable: true; QQC.ButtonGroup.group: group }
        ListView {
            id: list
            width: 400
            height: 120
            model: 3
            activeFocusOnTab: true
            currentIndex: 0
            delegate: ListRow {
                required property int index
                width: ListView.view.width
                text: "Layout " + index
                highlighted: ListView.isCurrentItem
            }
        }
        Row {
            spacing: 8
            SubtleButton { id: back; text: "Back" }
            PrimaryButton { id: next; text: "Next" }
            LinkButton { id: link; text: "Change" }
        }
        PrimaryButton { id: off; text: "Off"; enabled: false }
        ChoiceCard { id: action; width: 400; accent: true; title: "Install Raye"; illustration: "install" }
    }

    Column {
        x: 680
        y: 20
        spacing: 8
        ProgressRing { id: ring }
        ProgressRing { id: countdown; value: 0.5 }
        StepDots { id: dots; count: 5; current: 1 }
        Illustration { id: picture; name: "network"; size: 160 }
        Illustration { id: bigPicture; name: "done"; size: 480; visible: false }
        Item {
            width: 300
            height: 100
            PageEnter { id: enter; anchors.fill: parent; autoPlay: false; Rectangle { width: 10; height: 10 } }
        }
    }

    Component {
        id: lateIllustration
        Illustration { size: 64 }
    }
    Component {
        id: flatBackground
        SetupBackground { width: 200; height: 100 }
    }

    TestCase {
        name: "Setup"
        when: windowShown

        function init() {
            Theme.reducedMotion = false
            field.forceActiveFocus(Qt.TabFocusReason)
        }

        // --- the theme -------------------------------------------------

        function test_theme_is_night_and_setup_sized() {
            verify(Ui.Tokens.night, "setup pins the tokens to night")
            compare(Theme.controlHeight, 40)
            compare(field.height, 40)
            compare(next.height, 40)
            compare(Theme.title.pixelSize, 28)
            compare(Theme.titleFor(1920).pixelSize, 40)
            compare(Theme.titleFor(1280).pixelSize, 28)
            verify(Theme.caption.pixelSize >= 12, "no text smaller than 12 px")
        }

        function test_words_follow_the_language() {
            Theme.language = "fr"
            compare(Theme.text("showPassword"), "Afficher le mot de passe")
            compare(dots.Accessible.name, "Étape 2 sur 5")
            Theme.language = "en"
            compare(Theme.text("showPassword"), "Show password")
            compare(dots.Accessible.name, "Step 2 of 5")
            Theme.language = "de"
            compare(Theme.text("busy"), "Working", "an unknown language falls back to English")
            Theme.language = "en"
        }

        // --- focus order -------------------------------------------------

        function test_tab_order() {
            const order = [field, password, check, cardA, cardB, list, back, next, link, action]
            verify(field.activeFocus)
            for (let i = 1; i < order.length; ++i) {
                keyClick(Qt.Key_Tab)
                verify(order[i].activeFocus, "Tab " + i + " should reach " + order[i])
            }
            // the disabled button is skipped and Shift+Tab walks back
            keyClick(Qt.Key_Tab, Qt.ShiftModifier)
            verify(link.activeFocus)
        }

        function test_focus_ring_only_from_the_keyboard() {
            keyClick(Qt.Key_Tab)       // password
            keyClick(Qt.Key_Tab)       // check box
            verify(check.visualFocus)
            verify(findByName(check, "focusRing").visible)
            keyClick(Qt.Key_Tab)
            keyClick(Qt.Key_Tab)
            keyClick(Qt.Key_Tab)       // the list
            verify(list.activeFocus)
            verify(findByName(list.itemAtIndex(0), "focusRing").visible, "the current row shows the ring")
            verify(!findByName(list.itemAtIndex(1), "focusRing").visible)
            mouseClick(next)
            verify(!next.visualFocus)
            verify(!findByName(next, "focusRing").visible, "no ring after a click")
        }

        // --- states ------------------------------------------------------

        function test_primary_button_states() {
            compare(next.fillColor, Theme.accent)
            mouseMove(next, next.width / 2, next.height / 2)
            tryCompare(next, "hovered", true)
            compare(next.fillColor, Theme.accentHover)
            mousePress(next)
            compare(next.fillColor, Theme.accentPressed)
            mouseRelease(next)
            compare(off.fillColor, Theme.accentDisabled)
            mouseMove(root, 1270, 790)
        }

        function test_subtle_button_states() {
            compare(back.fillColor, Theme.controlFill)
            mouseMove(back, back.width / 2, back.height / 2)
            tryCompare(back, "hovered", true)
            compare(back.fillColor, Theme.controlFillHover)
            mousePress(back)
            compare(back.fillColor, Theme.controlFillPressed)
            mouseRelease(back)
            mouseMove(root, 1270, 790)
        }

        function test_enter_presses_a_button() {
            let clicks = 0
            const count = () => ++clicks
            next.clicked.connect(count)
            next.forceActiveFocus(Qt.TabFocusReason)
            keyClick(Qt.Key_Return)
            keyClick(Qt.Key_Space)
            next.clicked.disconnect(count)
            compare(clicks, 2)
        }

        function test_text_field_line() {
            field.forceActiveFocus()
            compare(field.lineWidth, 2)
            compare(field.lineColor, Theme.accent)
            compare(field.fillColor, Theme.inputActive)
            next.forceActiveFocus()
            compare(field.lineWidth, 1)
            field.error = true
            compare(field.lineWidth, 2)
            compare(field.lineColor, Theme.error)
            field.error = false
        }

        function test_password_reveal() {
            const eye = findByName(password, "reveal")
            password.text = ""
            verify(!eye.visible, "nothing typed, no eye")
            password.forceActiveFocus()
            keyClick(Qt.Key_A)
            verify(eye.visible)
            compare(password.echoMode, TextInput.Password)
            mouseClick(eye)
            verify(password.revealed)
            compare(password.echoMode, TextInput.Normal)
            verify(password.activeFocus, "the eye leaves the focus in the box")
            keyClick(Qt.Key_F8, Qt.AltModifier)
            verify(!password.revealed, "Alt+F8 hides it again")
            keyClick(Qt.Key_F8, Qt.AltModifier)
            verify(password.revealed)
            next.forceActiveFocus()
            verify(!password.revealed, "leaving the box hides the password")
            password.revealable = false
            password.forceActiveFocus()
            keyClick(Qt.Key_F8, Qt.AltModifier)
            verify(!password.revealed, "never shown when not revealable")
            verify(!eye.visible)
            password.revealable = true
            password.text = ""
        }

        function test_check_box() {
            verify(!check.checked)
            mouseClick(check)
            verify(check.checked)
            compare(check.boxColor, check.hovered ? Theme.accentHover : Theme.accent)
            mouseMove(check, 10, check.height / 2)
            tryCompare(check, "hovered", true)
            compare(check.boxColor, Theme.accentHover)
            mouseMove(root, 1270, 790)
            check.forceActiveFocus(Qt.TabFocusReason)
            keyClick(Qt.Key_Space)
            verify(!check.checked)
        }

        function test_choice_cards_pick_one() {
            mouseClick(cardA)
            verify(cardA.checked)
            verify(!cardB.checked)
            cardB.forceActiveFocus(Qt.TabFocusReason)
            keyClick(Qt.Key_Space)
            verify(cardB.checked)
            verify(!cardA.checked, "one card of a group at a time")
            cardA.forceActiveFocus(Qt.TabFocusReason)
            keyClick(Qt.Key_Return)
            verify(cardA.checked, "Enter picks the card too")
            keyClick(Qt.Key_Return)
            verify(cardA.checked, "a second Enter keeps the pick")
            verify(!cardB.checked)
            compare(cardA.fillColor, Theme.selected)
            compare(cardA.Accessible.role, Accessible.RadioButton)
            compare(action.Accessible.role, Accessible.Button)
        }

        function test_list_rows() {
            list.forceActiveFocus(Qt.TabFocusReason)
            compare(list.currentIndex, 0)
            keyClick(Qt.Key_Down)
            compare(list.currentIndex, 1)
            const row = list.itemAtIndex(1)
            verify(row.highlighted)
            compare(row.fillColor, Theme.selected)
            tryCompare(findByName(row, "pill"), "height", 16)
            tryCompare(findByName(list.itemAtIndex(0), "pill"), "height", 0)
            compare(row.height, 40)
        }

        // --- busy, steps, pictures ------------------------------------

        function test_progress_ring() {
            compare(ring.width, 40)
            verify(ring.busy)
            verify(ring.orbiting)
            ring.visible = false
            verify(!ring.orbiting, "a hidden ring stops")
            ring.visible = true
            Theme.reducedMotion = true
            verify(!ring.orbiting)
            verify(ring.pulsing, "reduced motion: the dots stay, a light runs round")
            Theme.reducedMotion = false
            verify(!countdown.busy)
            verify(!countdown.orbiting)
        }

        function test_step_dots() {
            const current = findByName(dots, "dot1")
            tryCompare(current, "width", 16)
            compare(findByName(dots, "dot0").width, 6)
            dots.current = 3
            tryCompare(findByName(dots, "dot3"), "width", 16)
            tryCompare(current, "width", 6)
            dots.current = 1
        }

        function test_every_picture_loads() {
            const names = Theme.illustrationNames
            compare(names.length, 15)
            for (let i = 0; i < names.length; ++i) {
                const item = createTemporaryObject(lateIllustration, root, { name: names[i] })
                verify(item.known, names[i])
                tryCompare(item, "status", Image.Ready, 5000, names[i] + " did not load")
            }
        }

        function test_unknown_picture_shows_nothing() {
            ignoreWarning(/no picture named/)
            const item = createTemporaryObject(lateIllustration, root, { name: "nothing" })
            verify(!item.known)
            compare(findByName(item, "lines").source.toString(), "")
        }

        function test_picture_scale() {
            verify(!picture.hidpi)
            verify(findByName(picture, "lines").source.toString().endsWith("network.png"))
            verify(bigPicture.hidpi)
            verify(findByName(bigPicture, "lines").source.toString().endsWith("done@2x.png"))
        }

        function test_a_picture_is_flat_and_still() {
            compare(findByName(picture, "glow"), null, "a glow is drawn behind the picture")
            const lines = findByName(picture, "lines")
            const y = lines.mapToItem(root, 0, 0).y
            wait(400)
            compare(lines.mapToItem(root, 0, 0).y, y, "the picture floats")
        }

        function test_the_background_is_one_flat_colour() {
            const bg = createTemporaryObject(flatBackground, root)
            verify(!bg.gradient, "the background is a gradient")
            compare(bg.children.length, 0, "lights are drawn over the background")
            compare(String(bg.color), String(Ui.Tokens.bgBase))
        }

        // --- page entrance -------------------------------------------

        function test_page_enters_from_the_right() {
            enter.enter(false)
            verify(enter.offset > 0, "starts on the right")
            tryCompare(enter, "running", false, 2000)
            compare(enter.offset, 0)
        }

        function test_page_enters_from_the_left_on_back() {
            enter.enter(true)
            verify(enter.offset < 0, "starts on the left")
            tryCompare(enter, "running", false, 2000)
            compare(enter.offset, 0)
        }

        function test_page_reduced_motion_only_fades() {
            Theme.reducedMotion = true
            enter.enter(false)
            compare(enter.offset, 0)
            tryCompare(enter, "running", false, 2000)
            enter.leave()
            tryCompare(enter, "running", false, 2000)
            Theme.reducedMotion = false
        }
    }

    // --- the words of the branding (etc/calamares/branding/raye) --------

    TestCase {
        name: "Words"

        // The premise, measured rather than assumed: Qt hands a language
        // its own name, and in French that name is lower case. The row the
        // owner saw on 2026-11-02 -- "français" between capitals -- was Qt
        // being right about French and the list being inconsistent. If Qt
        // ever changes its mind, this is the check that says so.
        function test_qt_gives_french_its_name_in_lower_case() {
            compare(Qt.locale("fr_FR").nativeLanguageName.charAt(0), "f")
            compare(Qt.locale("en_US").nativeLanguageName.charAt(0), "A")
            compare(Qt.locale("de_DE").nativeLanguageName.charAt(0), "D")
        }

        function test_every_row_of_the_language_list_starts_with_a_capital() {
            compare(S.listName(Qt.locale("fr_FR").nativeLanguageName), "Français")
            compare(S.listName("français"), "Français")
            compare(S.listName("español"), "Español")
            compare(S.listName("English"), "English")
            compare(S.listName("Deutsch"), "Deutsch")
            // not a letter, and nothing at all: neither may throw, and
            // neither may lose a character
            compare(S.listName("日本語"), "日本語")
            compare(S.listName(""), "")
        }

        // The card headed "Before you install next to Windows" over a
        // single line reading "Another Linux system is on this disk" --
        // the 2026-11-02 image. The title names Windows only for what
        // Windows has to fix.
        function test_the_warning_title_names_windows_only_for_windows() {
            compare(S.beforeKey(["bitlocker"]), "beforeTitle")
            compare(S.beforeKey(["hibernated"]), "beforeTitle")
            compare(S.beforeKey(["shared-efi"]), "beforeTitleDisk")
            compare(S.beforeKey([]), "beforeTitleDisk")
            // one of each: Windows is in there, so the title may say so
            compare(S.beforeKey(["shared-efi", "hibernated"]), "beforeTitle")
            // a word raye-preflight might grow and nobody listed: the
            // neutral title, never a claim about Windows
            compare(S.beforeKey(["something-new"]), "beforeTitleDisk")
        }

        function test_the_neutral_title_says_nothing_about_windows() {
            verify(S.t("en", "beforeTitleDisk").toLowerCase().indexOf("windows") < 0)
            verify(S.t("fr", "beforeTitleDisk").toLowerCase().indexOf("windows") < 0)
            verify(S.t("en", "beforeTitle").toLowerCase().indexOf("windows") >= 0,
                   "the Windows title is the one that may name it")
        }

        // --- while Raye installs ---------------------------------------
        //
        // The job names below were read off the installed Calamares 3.3.14
        // on 2026-11-06: the English from each module's pretty_name(), the
        // French from /usr/share/locale/fr/LC_MESSAGES/calamares-python.mo.
        // They are what the session log really carries, not invented names.

        readonly property var realJobs: [
            { job: "Mounting partitions.", stage: "installDisk" },
            { job: "Montage des partitions.", stage: "installDisk" },
            { job: "Filling up filesystems.", stage: "installCopy" },
            { job: "Remplir les systèmes de fichiers.", stage: "installCopy" },
            { job: "Install packages.", stage: "installDownload" },
            { job: "Installer les paquets.", stage: "installDownload" },
            { job: "Writing fstab.", stage: "installSetup" },
            { job: "Écriture du fstab.", stage: "installSetup" },
            { job: "Configuring locales.", stage: "installSetup" },
            { job: "Configuration des locales.", stage: "installSetup" },
            { job: "Saving network configuration.", stage: "installSetup" },
            { job: "Sauvegarde de la configuration du réseau en cours.", stage: "installSetup" },
            { job: "Setting hardware clock.", stage: "installSetup" },
            { job: "Configuration de l'horloge matériel.", stage: "installSetup" },
            { job: "Configuring initramfs.", stage: "installFinish" },
            { job: "Configuration du initramfs.", stage: "installFinish" },
            { job: "Configure GRUB.", stage: "installFinish" },
            { job: "Configuration du GRUB.", stage: "installFinish" },
            { job: "Install bootloader.", stage: "installFinish" },
            { job: "Installation du bootloader.", stage: "installFinish" },
            { job: "Unmount file systems.", stage: "installFinish" }
        ]

        function test_every_real_job_name_lands_on_its_stage() {
            for (var i = 0; i < realJobs.length; ++i) {
                var one = realJobs[i]
                compare(S.installStageOf(one.job), one.stage, one.job + " landed on " + S.installStageOf(one.job))
            }
        }

        // Two names hold a word of an earlier stage, so the rules are
        // tried in an order that is NOT the display order. Sorting them by
        // installStageOrder sends the end of the install back to its
        // beginning, and nothing else would say so.
        function test_the_end_of_the_install_is_not_read_as_its_beginning() {
            compare(S.installStageOf("Unmount file systems."), "installFinish",
                    "holds \"mount\", which is the disk stage")
            compare(S.installStageOf("Configure GRUB."), "installFinish",
                    "holds \"configur\", which is the setup stage")
        }

        // A rule word swallowed by a longer word of another language.
        // "log" (meant for the log-collecting job, which never matched it)
        // sits inside "horloge", so the French clock job -- a setup job,
        // run in the middle -- announced the last stage of the install.
        function test_a_short_rule_word_is_not_swallowed_by_a_longer_one() {
            compare(S.installStageOf("Configuration de l'horloge matériel."),
                    "installSetup")
            for (var i = 0; i < S.installStageRules.length; ++i)
                for (var w = 0; w < S.installStageRules[i].words.length; ++w)
                    verify(S.installStageRules[i].words[w].length >= 4,
                           "a rule word of three letters or fewer is a trap: "
                           + S.installStageRules[i].words[w])
        }

        function test_an_unknown_job_name_claims_no_stage() {
            compare(S.installStageOf("Shell Processes Job"), "")
            compare(S.installStageOf(""), "")
            // and an unknown stage carries no step number rather than a
            // wrong one
            compare(S.installStep("").step, 0)
            compare(S.installStep("installNowhere").step, 0)
        }

        function test_the_step_number_counts_the_stages_in_order() {
            compare(S.installStep("installDisk").step, 1)
            compare(S.installStep("installFinish").step, S.installStageOrder.length)
            compare(S.installStep("installDisk").count, S.installStageOrder.length)
            verify(S.installStep("installCopy").step < S.installStep("installDownload").step)
            verify(S.installStep("installDownload").step < S.installStep("installSetup").step)
            verify(S.installStep("installSetup").step < S.installStep("installFinish").step)
        }

        function test_the_two_stage_orders_name_the_same_stages() {
            var ruled = []
            for (var i = 0; i < S.installStageRules.length; ++i)
                ruled.push(S.installStageRules[i].key)
            compare(ruled.slice().sort().join(","),
                    S.installStageOrder.slice().sort().join(","),
                    "a stage with rules and no place, or a place and no rules")
            for (var j = 0; j < S.installStageOrder.length; ++j) {
                var key = S.installStageOrder[j]
                verify(S.t("en", key) !== key, "no English words for " + key)
                verify(S.t("fr", key) !== key, "no French words for " + key)
            }
        }

        function test_a_finding_reaches_its_own_words() {
            compare(S.findingKey("shared-efi"), "sharedEfi")
            compare(S.findingKey("bitlocker"), "bitlocker")
            compare(S.findingKey("a-b-c"), "aBC")
            for (var i = 0; i < S.diskFindings.length; ++i) {
                var key = S.findingKey(S.diskFindings[i])
                verify(S.t("en", key) !== key, "no English words for " + S.diskFindings[i])
                verify(S.t("fr", key) !== key, "no French words for " + S.diskFindings[i])
            }
        }
    
        // a stick that can't be read fails the copy; the person has to hear
        // "write the stick again", not "restart and try again"
        function test_a_failed_read_of_the_stick_says_to_write_it_again() {
            for (const message of ["Failed to unpack image \"/cdrom/casper/filesystem.squashfs\"",
                                   "rsync failed with error code 23.\nrsync: read errors mapping \"/x\": Input/output error (5)"])
                compare(S.failureKey(message, ""), "failedMedium", message)
            compare(S.failureKey("Bootloader installation error", "grub-install: error"), "failedRestart")
            compare(S.failureKey("", "SQUASHFS error: zlib decompression failed"), "failedMedium")
            for (const lang of ["en", "fr"])
                verify(S.t(lang, "failedMedium") !== "failedMedium" && S.t(lang, "failedMedium").indexOf("Rufus") < 0)
        }

        // another Linux owning EFI/ubuntu is no longer a reason to worry:
        // Raye makes its own EFI partition next to it
        function test_the_welcome_card_warns_only_about_real_trouble() {
            compare(S.warnings(["shared-efi"]).length, 0)
            compare(S.warnings(["linux-hibernated", "shared-efi", "bitlocker", "something-new"]),
                    ["linux-hibernated", "bitlocker"])
            compare(S.beforeKey(["linux-hibernated"]), "beforeTitleDisk")
        }
}
}
