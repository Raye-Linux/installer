// Words of Raye Setup, English and French. Every page and both bars read
// them through t(); tests/test_branding.py checks both languages have the
// same keys.
//
//   import "strings.js" as S
//   Text { text: S.t(page.lang, "regionTitle") }
//   Text { text: S.t(page.lang, "joining", [name]) }    // %1, %2...
.pragma library

var words = {
    en: {
        setupName: "Raye Setup",
        quit: "Close Setup",
        back: "Back",
        next: "Next",
        accept: "Accept",
        install: "Install",
        restartNow: "Restart now",
        skip: "Skip for now",
        change: "Change",
        done: "Done",
        search: "Search",

        stageRegion: "Region",
        stageNetwork: "Network",
        stageDisk: "Disk",
        stageAccount: "Account",
        stagePrivacy: "Privacy",
        stageDesktop: "Desktop",
        stageInstall: "Install",
        stageOf: "Step %1 of %2: %3",

        quitTitle: "Quit Setup?",
        quitText: "Raye isn't installed yet. Your PC will restart, and nothing on it has been changed.",
        quitRestart: "Restart",
        quitShutDown: "Shut down",
        quitTextDesktop: "Raye isn't installed yet, and nothing on your PC has been changed. You'll go back to the desktop.",
        quitClose: "Quit Setup",

        accessibility: "Accessibility",
        onScreenKeyboard: "On-screen keyboard",
        screenReader: "Screen reader",
        screenReaderHint: "Windows key + Alt + S",

        languageTitle: "Choose your language",
        languageText: "You can add more languages later in Settings.",
        languageSearch: "Search for a language",
        notReadyTitle: "This PC can't run Raye",
        notReadyLine: "Fix this, then start Setup again:",
        beforeTitle: "Before you install next to Windows",
        beforeTitleDisk: "Before you install",
        bitlocker: "Windows is encrypted with BitLocker. To install Raye next to it, start Windows, open Manage BitLocker and choose Suspend protection, then come back. Keep your BitLocker recovery key at hand.",
        hibernated: "Windows isn't fully shut down (Fast Startup or hibernation). In Windows, open Control Panel > Power Options > Choose what the power buttons do, untick Turn on fast startup, then shut down.",
        ntfsDirty: "Windows wasn't shut down properly, so Raye can't make room next to it. Start Windows, then shut it down from the Start menu -- not Sleep, not Restart -- and come back.",
        ntfsCheck: "Windows wants to check this disk before anything else touches it. Start Windows, open a command prompt as administrator, run chkdsk /f, and restart Windows twice so it finishes.",
        ntfsBusy: "Something else is holding this Windows volume -- another system that is still running, or a RAID set the firmware set up. Raye can't make room next to it.",
        ntfsUnknown: "Raye couldn't make sense of the Windows volume on this disk, so it won't try to resize it. Erase the disk or pick another one.",
        sharedEfi: "Another Linux system starts from this disk. Raye gets a boot partition of its own next to it, so that system keeps starting the way it does now.",
        linuxHibernated: "A Linux system on this disk is hibernated. Start it, shut it down normally, then come back.",
        linuxCheck: "%1 wasn't shut down properly, so Raye won't resize it. Start it, shut it down normally, then come back.",
        linuxUnknown: "Raye couldn't read %1 well enough to resize it safely.",
        btrfsMulti: "%1 spans more than one disk, so Raye can't make it smaller.",
        xfs: "%1 uses XFS, which can't be made smaller. You can still replace it or use free space.",
        encrypted: "%1 is encrypted, so Raye can't make it smaller. You can still replace it or use free space.",
        lvm: "%1 uses LVM, so Raye can't make it smaller. You can still replace it or use free space.",
        fullTable: "This disk's older layout already holds as many partitions as it can, so Raye can only be installed on it by erasing it.",
        eraseStillFine: "You can still go on if you mean to erase the disk.",

        regionTitle: "Is this the right country or region?",
        regionText: "This sets your time zone and the way dates and numbers look.",
        regionSearch: "Search for a country or region",
        timeZone: "Time zone",
        notListed: "My country isn't listed",
        pickZone: "Pick your time zone",
        zoneArea: "Area",
        zoneCity: "City",
        backToList: "Back to the list",

        keyboardTitle: "Is this the right keyboard layout?",
        keyboardText: "If you also use another layout, you can add it below.",
        keyboardSearch: "Search for a layout",
        variant: "Type",
        variantDefault: "Default",
        addSecond: "Add a second layout",
        secondLayout: "Second layout",
        remove: "Remove",
        switchHint: "Switch layouts with Windows key + Space.",
        tryKeyboard: "Type here to try your keyboard",
        chooseSecond: "Choose the second layout",

        networkTitle: "Let's connect you to a network",
        networkText: "Raye uses the internet to set the clock and get the latest fixes after setup.",
        connectedTo: "Connected to %1",
        wiredConnected: "Connected with a cable",
        online: "You're online.",
        wifiPassword: "Network security key",
        connect: "Connect",
        connecting: "Connecting…",
        connected: "Connected",
        secured: "Secured",
        open: "Open",
        couldNotConnect: "Couldn't connect to %1. Check the key and try again.",
        noInternet: "I don't have internet",
        signInPage: "This network wants you to sign in on a web page. Use another network, or continue without the internet.",
        limited: "Connected to the network, but the internet can't be reached.",
        noCard: "No network card was found on this PC. You can continue without the internet.",
        noWifi: "No Wi-Fi card was found. Plug in a network cable, or continue without the internet.",
        scanning: "Looking for networks…",

        diskTitle: "Where do you want to install Raye?",
        diskText: "Choose how Raye uses this disk.",
        diskScanning: "Checking your disks…",
        diskNone: "Raye can't find a disk to install on.",
        diskBlockedLive: "this is the USB stick Raye started from.",
        diskBlockedSmall: "too small. Raye needs at least 28 GB.",
        diskBlockedInUse: "something on it is in use, so Raye won't touch it.",
        diskBlockedUnreadable: "Raye couldn't read it, so it won't touch it. Check the cable, or restart the PC and try again.",
        diskSize: "%1 GB",
        diskShare: "%1: %2",
        diskThisPartition: "this partition",
        diskShrinkTitle: "Install next to %1",
        diskShrinkLine: "%1 and your files stay. Raye takes room from its volume.",
        diskShrinkNote: "Windows may check its disk the first time it starts afterwards. Let it finish.",
        diskShrinkNoteLinux: "Raye checks the volume first and stops if anything looks wrong. Back up anything you can't lose before you go on.",
        diskReplacePartition: "partition %1 (%2)",
        confirmCancel: "Cancel",
        confirmEraseTitle: "Erase this disk?",
        confirmEraseText: "Everything on %1 will be deleted: files, apps, settings and any other system on it. This can't be undone.",
        confirmErase: "Erase",
        confirmReplaceTitle: "Delete %1?",
        confirmReplaceText: "Everything on %1 (%2) will be deleted, including the files on it. The rest of the disk stays as it is. This can't be undone.",
        confirmReplace: "Delete",
        confirmShrinkTitle: "Make %1 smaller?",
        confirmShrinkText: "Raye checks %1, then makes it smaller to make room. Its files stay, but a power cut in the middle can damage them, so back up anything important first.",
        confirmShrink: "Continue",
        diskSlider: "How much room each system gets",
        diskFreeTitle: "Use the free space",
        diskFreeLine: "%1 not used by anything. Nothing else on the disk changes.",
        diskReplaceTitle: "Replace %1",
        diskReplaceLine: "Everything on %1 (%2) will be deleted.",
        diskEraseTitle: "Erase this disk",
        diskEraseLine: "Everything on this disk will be deleted.",
        diskEmptyTitle: "Use this disk",
        diskEmptyLine: "This disk is empty. Raye will use all of it.",
        diskOldTable: "This disk uses an older layout, so Raye can only be installed on it by erasing it.",
        diskNow: "Now",
        diskAfter: "After the install",
        diskFreeWord: "Free space",
        diskEncrypt: "Encrypt Raye with a password",
        diskEncryptLine: "If this PC is lost or stolen, nobody can read your files without this password.",
        diskPassLabel: "Disk password",
        diskPassAgainLabel: "Confirm disk password",
        diskPassShort: "Use at least %1 characters.",
        diskPassMismatch: "The passwords don't match.",
        diskLookAgain: "Refresh",
        diskDetailErase: "Everything on %1 is deleted.",
        diskDetailShrink: "%1 keeps %2.",
        diskDetailRaye: "Raye gets %1.",
        diskDetailReplace: "%1 (%2) is deleted. Everything else stays.",
        diskDetailEncrypted: "Raye is encrypted.",
        folderDesktop: "Desktop",
        folderDocuments: "Documents",
        folderDownloads: "Downloads",
        folderMusic: "Music",
        folderPictures: "Pictures",
        folderVideos: "Videos",
        diskKeepTitle: "Replace %1 and keep my files",
        diskKeepLine: "Your Desktop, Documents, Downloads, Music, Pictures and Videos come with you (%2). Everything else on %1 is deleted.",
        diskKeepRoom: "Raye can't keep your files from %1 here: copying them safely takes %2 on this disk, and there's %3. Copy them to a USB drive first, or free up some space in it.",
        diskKeepUnreadable: "Some of your files on %1 can't be read, so Raye can't promise to keep them. Copy them to a USB drive first.",
        confirmKeepTitle: "Replace %1 and keep your files?",
        confirmKeepStage: "Raye copies these folders into your new account and checks every file. Then %1 is deleted, with its apps, settings and every other file.",
        confirmKeepHome: "These folders move into your new account. The partition they're on stays as it is. %1 is deleted, with its apps and settings.",
        confirmKeepSafe: "If a single file can't be copied, %1 isn't deleted.",
        confirmKeepFolder: "%1 (%2)",
        confirmKeepFiles: "%1 · %2 files",
        confirmKeep: "Replace and keep",
        diskDetailKeep: "%1 is replaced by Raye. Your folders (%2) come to your new account first.",
        keepDone: "Your files from %1 are in your folders.",
        keepLeft: "Some of your files couldn't be copied. Nothing was lost: all of them are still on this PC, in the partition named raye_files.",
        keepNotMoved: "Some of your folders couldn't be moved. Nothing was deleted: they're still in your Home folder.",
        doneDesktopFallback: "Hyprland couldn't be installed, so Raye starts with KDE Plasma.",

        deviceTitle: "Let's name your device",
        deviceText: "A name makes it easier to recognize this PC on your network and when you share files.",
        deviceName: "Device name",
        deviceRules: "Letters, numbers and hyphens, up to 63 characters. No spaces.",
        deviceSkip: "Leave it empty and Raye picks one from your name.",

        accountTitle: "Sign in with your Raye account",
        accountText: "Bring your settings, wallpaper and Store apps with you. You'll finish signing in on the account website after Raye starts.",
        accountSignIn: "Sign in with my Raye account",
        accountLocal: "Use a local account instead",
        accountLater: "Sign in later",
        accountChosen: "After setup, Raye opens the account website so you can sign in.",

        userTitle: "Who's going to use this PC?",
        userText: "You'll use this name and password to sign in to this PC.",
        fullName: "Name",
        userName: "Account name",
        userNameLine: "Account name: %1",
        password: "Password",
        confirmPassword: "Confirm password",
        passwordsDiffer: "The passwords don't match.",
        hint: "Password hint (optional)",
        hintLine: "Shown on the sign-in screen if you forget your password.",
        hintHasPassword: "The hint can't contain your password.",

        privacyTitle: "Choose privacy settings for your device",
        privacyText: "Raye sends nothing about you: no ads, no tracking. You can change these at any time in Settings > Privacy & security.",
        location: "Location",
        locationOn: "Apps can ask to know where you are, for weather or maps. Raye asks you before each app gets it.",
        locationOff: "No app can know where you are.",
        diagnostics: "Usage statistics",
        diagnosticsOn: "Send anonymous statistics to KDE, who make the desktop Raye is built on. Nothing that identifies you.",
        diagnosticsOff: "Nothing is sent.",
        history: "Activity history",
        historyOn: "Raye remembers the files and apps you use, so you can find them again quickly.",
        historyOff: "Raye doesn't remember the files and apps you use.",
        on: "On",
        off: "Off",

        desktopTitle: "Choose your desktop",
        desktopText: "This is what you'll see after you sign in. If you're not sure, keep the one we recommend.",
        desktopPlasma: "KDE Plasma (recommended)",
        desktopPlasmaLine: "The full Raye desktop, made to work like Windows: taskbar, Start menu, windows you drag and snap.",
        desktopHyprland: "Hyprland",
        desktopHyprlandLine: "A tiling desktop: windows line up side by side on their own, and you do most things with the keyboard. For people who already know Hyprland.",
        desktopBoth: "KDE Plasma stays installed too. You can switch between the two on the sign-in screen.",
        desktopDownload: "Raye downloads Hyprland while it installs, so stay connected to the internet.",

        readyTitle: "Ready to install",
        readyText: "Check these choices. Raye starts installing when you select Install.",
        readyErase: "Everything on this disk will be deleted, including your files, apps and settings.",
        readyRegionCard: "Language and region",
        readyLanguage: "Language",
        readyCountry: "Country or region",
        readyKeyboard: "Keyboard",
        readyDiskCard: "Disk",
        readyDisk: "Drive",
        readyWhat: "What happens",
        readyWhatErase: "Erase the whole disk and install Raye",
        readyWhatAlongside: "Install Raye next to what's already on the disk",
        readyWhatReplace: "Replace one partition with Raye",
        readyWhatOther: "Install Raye on this disk",
        readyEncryption: "Encryption",
        readyEncrypted: "On. You'll get a recovery key after setup.",
        readyNotEncrypted: "Off",
        readyAccountCard: "Account",
        readyName: "Name",
        readyPcName: "PC name",
        readyDesktop: "Desktop",
        readyDetailsShow: "Show disk details",
        readyDetailsHide: "Hide disk details",

        installingTitle: "Installing Raye",
        installingText: "This takes a few minutes. You can leave your PC alone.",
        installStarting: "Getting ready",
        installStepOf: "Step %1 of %2",
        installDisk: "Getting the disk ready",
        installCopy: "Copying Raye",
        installDownload: "Downloading updates and language packs",
        installDrivers: "Installing drivers",
        installSetup: "Setting things up",
        installFinish: "Finishing up",
        showDetails: "Show details",
        hideDetails: "Hide details",
        tipStart: "Press the Windows key to open Start: your apps, files and settings in one place.",
        tipStore: "Get apps and games in one click from Raye Store.",
        tipFiles: "Your files have a home in Files, with Documents, Pictures and Downloads ready.",
        tipUpdate: "Updates install while you work. Only the few that need a restart wait for one.",

        doneTitle: "Raye is installed",
        doneText: "Your PC restarts to finish. Take out the USB stick when the screen goes dark.",
        restartIn: "Restarting in %1 s",
        failedTitle: "Something went wrong",
        failedText: "Raye couldn't be installed.",
        failedDetails: "What happened",
        failedRestart: "Restart your PC and try again. If it happens again, the details below help find out why.",
        failedMedium: "Raye couldn't read the USB stick it started from: it may have been written badly or be worn out. Write the stick again, on another one if you can, and start over.",
        licences: "Licenses",
        licenceText: "Raye Setup uses Calamares, free software under the GNU GPL 3.0 or later. © 2014-2017 Teo Mrnjavac, © 2017-2024 Adriaan de Groot and the Calamares team."
    },
    fr: {
        setupName: "Installation de Raye",
        quit: "Fermer l'installation",
        back: "Retour",
        next: "Suivant",
        accept: "Accepter",
        install: "Installer",
        restartNow: "Redémarrer maintenant",
        skip: "Ignorer pour l'instant",
        change: "Changer",
        done: "Terminé",
        search: "Rechercher",

        stageRegion: "Région",
        stageNetwork: "Réseau",
        stageDisk: "Disque",
        stageAccount: "Compte",
        stagePrivacy: "Confidentialité",
        stageDesktop: "Bureau",
        stageInstall: "Installation",
        stageOf: "Étape %1 sur %2 : %3",

        quitTitle: "Quitter l'installation ?",
        quitText: "Raye n'est pas encore installé. Votre PC va redémarrer, et rien n'y a été modifié.",
        quitRestart: "Redémarrer",
        quitShutDown: "Arrêter",
        quitTextDesktop: "Raye n'est pas encore installé, et rien n'a été modifié sur votre PC. Vous retrouverez le bureau.",
        quitClose: "Quitter l'installation",

        accessibility: "Accessibilité",
        onScreenKeyboard: "Clavier visuel",
        screenReader: "Lecteur d'écran",
        screenReaderHint: "Touche Windows + Alt + S",

        languageTitle: "Choisissez votre langue",
        languageText: "Vous pourrez ajouter d'autres langues plus tard dans les Paramètres.",
        languageSearch: "Rechercher une langue",
        notReadyTitle: "Ce PC ne peut pas faire fonctionner Raye",
        notReadyLine: "Réglez ceci, puis relancez l'installation :",
        beforeTitle: "Avant d'installer à côté de Windows",
        beforeTitleDisk: "Avant d'installer",
        bitlocker: "Windows est chiffré avec BitLocker. Pour installer Raye à côté, démarrez Windows, ouvrez Gérer BitLocker et choisissez Suspendre la protection, puis revenez ici. Gardez votre clé de récupération BitLocker sous la main.",
        hibernated: "Windows n'est pas complètement éteint (démarrage rapide ou veille prolongée). Dans Windows, ouvrez Panneau de configuration > Options d'alimentation > Choisir l'action des boutons d'alimentation, décochez Activer le démarrage rapide, puis arrêtez le PC.",
        ntfsDirty: "Windows n'a pas été arrêté correctement, Raye ne peut donc pas faire de place à côté. Démarrez Windows, puis arrêtez-le depuis le menu Démarrer\u00a0: ni Veille, ni Redémarrer. Revenez ensuite ici.",
        ntfsCheck: "Windows veut vérifier ce disque avant que quoi que ce soit d'autre y touche. Démarrez Windows, ouvrez une invite de commandes en administrateur, lancez chkdsk /f, puis redémarrez Windows deux fois pour qu'il termine.",
        ntfsBusy: "Quelque chose retient ce volume Windows\u00a0: un autre système encore en marche, ou un ensemble RAID monté par le firmware. Raye ne peut pas faire de place à côté.",
        ntfsUnknown: "Raye n'a pas réussi à lire le volume Windows de ce disque, il n'essaiera donc pas de le redimensionner. Effacez le disque ou choisissez-en un autre.",
        sharedEfi: "Un autre système Linux démarre depuis ce disque. Raye y crée sa propre partition de démarrage, et cet autre système continue de démarrer comme avant.",
        linuxHibernated: "Un système Linux de ce disque est en veille prolongée. Démarrez-le, éteignez-le normalement, puis revenez ici.",
        linuxCheck: "%1 n'a pas été arrêté correctement, Raye ne le redimensionne donc pas. Démarrez-le, éteignez-le normalement, puis revenez ici.",
        linuxUnknown: "Raye n'a pas pu lire %1 assez bien pour le redimensionner sans risque.",
        btrfsMulti: "%1 s'étend sur plusieurs disques\u00a0: Raye ne peut pas le réduire.",
        xfs: "%1 utilise XFS, qui ne peut pas être réduit. Vous pouvez quand même le remplacer ou utiliser l'espace libre.",
        encrypted: "%1 est chiffré\u00a0: Raye ne peut pas le réduire. Vous pouvez quand même le remplacer ou utiliser l'espace libre.",
        lvm: "%1 utilise LVM\u00a0: Raye ne peut pas le réduire. Vous pouvez quand même le remplacer ou utiliser l'espace libre.",
        fullTable: "L'ancienne disposition de ce disque contient déjà autant de partitions que possible\u00a0: Raye ne peut s'y installer qu'en l'effaçant.",
        eraseStillFine: "Vous pouvez quand même continuer si vous comptez effacer le disque.",

        regionTitle: "Est-ce le bon pays ou la bonne région ?",
        regionText: "Cela règle le fuseau horaire et l'affichage des dates et des nombres.",
        regionSearch: "Rechercher un pays ou une région",
        timeZone: "Fuseau horaire",
        notListed: "Mon pays n'est pas dans la liste",
        pickZone: "Choisissez votre fuseau horaire",
        zoneArea: "Zone",
        zoneCity: "Ville",
        backToList: "Revenir à la liste",

        keyboardTitle: "Est-ce la bonne disposition de clavier ?",
        keyboardText: "Si vous utilisez aussi une autre disposition, vous pouvez l'ajouter ci-dessous.",
        keyboardSearch: "Rechercher une disposition",
        variant: "Type",
        variantDefault: "Par défaut",
        addSecond: "Ajouter une deuxième disposition",
        secondLayout: "Deuxième disposition",
        remove: "Retirer",
        switchHint: "Passez de l'une à l'autre avec touche Windows + Espace.",
        tryKeyboard: "Tapez ici pour essayer votre clavier",
        chooseSecond: "Choisissez la deuxième disposition",

        networkTitle: "Connectons-vous à un réseau",
        networkText: "Raye utilise Internet pour régler l'heure et obtenir les derniers correctifs après l'installation.",
        connectedTo: "Connecté à %1",
        wiredConnected: "Connecté par câble",
        online: "Vous êtes en ligne.",
        wifiPassword: "Clé de sécurité réseau",
        connect: "Se connecter",
        connecting: "Connexion…",
        connected: "Connecté",
        secured: "Sécurisé",
        open: "Ouvert",
        couldNotConnect: "Impossible de se connecter à %1. Vérifiez la clé et réessayez.",
        noInternet: "Je n'ai pas Internet",
        signInPage: "Ce réseau demande de vous connecter sur une page web. Utilisez un autre réseau, ou continuez sans Internet.",
        limited: "Connecté au réseau, mais Internet est injoignable.",
        noCard: "Aucune carte réseau n'a été trouvée sur ce PC. Vous pouvez continuer sans Internet.",
        noWifi: "Aucune carte Wi-Fi n'a été trouvée. Branchez un câble réseau, ou continuez sans Internet.",
        scanning: "Recherche des réseaux…",

        diskTitle: "Où voulez-vous installer Raye ?",
        diskText: "Choisissez comment Raye utilise ce disque.",
        diskScanning: "Vérification de vos disques…",
        diskNone: "Raye ne trouve aucun disque où s'installer.",
        diskBlockedLive: "c'est la clé USB depuis laquelle Raye a démarré.",
        diskBlockedSmall: "trop petit. Raye a besoin d'au moins 28 Go.",
        diskBlockedInUse: "une partie est utilisée, Raye n'y touche donc pas.",
        diskBlockedUnreadable: "Raye n'a pas pu le lire, il n'y touche donc pas. Vérifiez le câble, ou redémarrez le PC et réessayez.",
        diskSize: "%1 Go",
        diskShare: "%1 : %2",
        diskThisPartition: "cette partition",
        diskShrinkTitle: "Installer à côté de %1",
        diskShrinkLine: "%1 et vos fichiers restent. Raye prend de la place sur son volume.",
        diskShrinkNote: "Windows peut vérifier son disque la première fois qu'il démarre ensuite. Laissez-le terminer.",
        diskShrinkNoteLinux: "Raye vérifie d'abord le volume et s'arrête si quelque chose cloche. Sauvegardez ce que vous ne voulez pas perdre avant de continuer.",
        diskReplacePartition: "la partition %1 (%2)",
        confirmCancel: "Annuler",
        confirmEraseTitle: "Effacer ce disque\u00a0?",
        confirmEraseText: "Tout ce qui se trouve sur %1 sera supprimé\u00a0: fichiers, applis, paramètres et tout autre système. Impossible de revenir en arrière.",
        confirmErase: "Effacer",
        confirmReplaceTitle: "Supprimer %1\u00a0?",
        confirmReplaceText: "Tout ce qui se trouve sur %1 (%2) sera supprimé, y compris ses fichiers. Le reste du disque ne change pas. Impossible de revenir en arrière.",
        confirmReplace: "Supprimer",
        confirmShrinkTitle: "Réduire %1\u00a0?",
        confirmShrinkText: "Raye vérifie %1, puis le réduit pour faire de la place. Ses fichiers restent, mais une coupure de courant au milieu peut les abîmer\u00a0: sauvegardez d'abord ce qui compte.",
        confirmShrink: "Continuer",
        diskSlider: "La place donnée à chaque système",
        diskFreeTitle: "Utiliser l'espace libre",
        diskFreeLine: "%1 inutilisés. Rien d'autre ne change sur le disque.",
        diskReplaceTitle: "Remplacer %1",
        diskReplaceLine: "Tout ce qui se trouve sur %1 (%2) sera supprimé.",
        diskEraseTitle: "Effacer ce disque",
        diskEraseLine: "Tout ce qui se trouve sur ce disque sera supprimé.",
        diskEmptyTitle: "Utiliser ce disque",
        diskEmptyLine: "Ce disque est vide. Raye l'utilisera en entier.",
        diskOldTable: "Ce disque utilise une ancienne disposition : Raye ne peut s'y installer qu'en l'effaçant.",
        diskNow: "Maintenant",
        diskAfter: "Après l'installation",
        diskFreeWord: "Espace libre",
        diskEncrypt: "Chiffrer Raye avec un mot de passe",
        diskEncryptLine: "Si ce PC est perdu ou volé, personne ne pourra lire vos fichiers sans ce mot de passe.",
        diskPassLabel: "Mot de passe du disque",
        diskPassAgainLabel: "Confirmez le mot de passe du disque",
        diskPassShort: "Utilisez au moins %1 caractères.",
        diskPassMismatch: "Les mots de passe ne correspondent pas.",
        diskLookAgain: "Actualiser",
        diskDetailErase: "Tout ce qui se trouve sur %1 est supprimé.",
        diskDetailShrink: "%1 garde %2.",
        diskDetailRaye: "Raye obtient %1.",
        diskDetailReplace: "%1 (%2) est supprimé. Tout le reste ne change pas.",
        diskDetailEncrypted: "Raye est chiffré.",
        folderDesktop: "Bureau",
        folderDocuments: "Documents",
        folderDownloads: "Téléchargements",
        folderMusic: "Musique",
        folderPictures: "Images",
        folderVideos: "Vidéos",
        diskKeepTitle: "Remplacer %1 et garder mes fichiers",
        diskKeepLine: "Votre Bureau, vos Documents, Téléchargements, Musique, Images et Vidéos vous suivent (%2). Tout le reste de %1 est supprimé.",
        diskKeepRoom: "Raye ne peut pas garder vos fichiers de %1 ici\u00a0: les copier sans risque demande %2 sur ce disque, et il y a %3. Copiez-les d'abord sur une clé USB, ou libérez-y de la place.",
        diskKeepUnreadable: "Certains de vos fichiers de %1 ne peuvent pas être lus\u00a0: Raye ne peut pas promettre de les garder. Copiez-les d'abord sur une clé USB.",
        confirmKeepTitle: "Remplacer %1 et garder vos fichiers\u00a0?",
        confirmKeepStage: "Raye copie ces dossiers dans votre nouveau compte et vérifie chaque fichier. Ensuite %1 est supprimé, avec ses applis, ses paramètres et tous ses autres fichiers.",
        confirmKeepHome: "Ces dossiers vont dans votre nouveau compte. La partition où ils se trouvent ne change pas. %1 est supprimé, avec ses applis et ses paramètres.",
        confirmKeepSafe: "Si un seul fichier ne peut pas être copié, %1 n'est pas supprimé.",
        confirmKeepFolder: "%1 (%2)",
        confirmKeepFiles: "%1 · %2 fichiers",
        confirmKeep: "Remplacer et garder",
        diskDetailKeep: "%1 est remplacé par Raye. Vos dossiers (%2) vont d'abord dans votre nouveau compte.",
        keepDone: "Vos fichiers de %1 sont dans vos dossiers.",
        keepLeft: "Certains de vos fichiers n'ont pas pu être copiés. Rien n'est perdu\u00a0: ils sont tous encore sur ce PC, dans la partition nommée raye_files.",
        keepNotMoved: "Certains de vos dossiers n'ont pas pu être déplacés. Rien n'a été supprimé\u00a0: ils sont toujours dans votre dossier personnel.",
        doneDesktopFallback: "Hyprland n'a pas pu être installé, Raye démarrera donc avec KDE Plasma.",

        deviceTitle: "Donnons un nom à votre appareil",
        deviceText: "Un nom permet de reconnaître plus facilement ce PC sur votre réseau et quand vous partagez des fichiers.",
        deviceName: "Nom de l'appareil",
        deviceRules: "Lettres, chiffres et traits d'union, 63 caractères au plus. Pas d'espace.",
        deviceSkip: "Laissez vide et Raye en choisira un d'après votre nom.",

        accountTitle: "Connectez-vous avec votre compte Raye",
        accountText: "Retrouvez vos paramètres, votre fond d'écran et vos applications du Store. Vous terminerez la connexion sur le site du compte après le démarrage de Raye.",
        accountSignIn: "Me connecter avec mon compte Raye",
        accountLocal: "Utiliser plutôt un compte local",
        accountLater: "Me connecter plus tard",
        accountChosen: "Après l'installation, Raye ouvrira le site du compte pour vous connecter.",

        userTitle: "Qui va utiliser ce PC ?",
        userText: "Vous utiliserez ce nom et ce mot de passe pour ouvrir une session sur ce PC.",
        fullName: "Nom",
        userName: "Nom du compte",
        userNameLine: "Nom du compte : %1",
        password: "Mot de passe",
        confirmPassword: "Confirmez le mot de passe",
        passwordsDiffer: "Les mots de passe ne correspondent pas.",
        hint: "Indice de mot de passe (facultatif)",
        hintLine: "Affiché sur l'écran de connexion si vous oubliez votre mot de passe.",
        hintHasPassword: "L'indice ne peut pas contenir votre mot de passe.",

        privacyTitle: "Choisissez les paramètres de confidentialité de votre appareil",
        privacyText: "Raye n'envoie rien sur vous : ni publicité, ni pistage. Vous pourrez les changer quand vous voudrez dans Paramètres > Confidentialité et sécurité.",
        location: "Localisation",
        locationOn: "Les applications peuvent demander où vous êtes, pour la météo ou les cartes. Raye vous demande avant chacune.",
        locationOff: "Aucune application ne peut savoir où vous êtes.",
        diagnostics: "Statistiques d'utilisation",
        diagnosticsOn: "Envoyer des statistiques anonymes à KDE, qui conçoit le bureau sur lequel Raye est bâti. Rien qui vous identifie.",
        diagnosticsOff: "Rien n'est envoyé.",
        history: "Historique d'activité",
        historyOn: "Raye retient les fichiers et les applications que vous utilisez, pour les retrouver vite.",
        historyOff: "Raye ne retient pas les fichiers et les applications que vous utilisez.",
        on: "Activé",
        off: "Désactivé",

        desktopTitle: "Choisissez votre bureau",
        desktopText: "C'est ce que vous verrez après la connexion. Si vous hésitez, gardez celui que nous recommandons.",
        desktopPlasma: "KDE Plasma (recommandé)",
        desktopPlasmaLine: "Le bureau Raye complet, pensé pour fonctionner comme Windows\u00a0: barre des tâches, menu Démarrer, fenêtres qu'on déplace et qu'on aligne.",
        desktopHyprland: "Hyprland",
        desktopHyprlandLine: "Un bureau en mosaïque\u00a0: les fenêtres se rangent côte à côte d'elles-mêmes et presque tout se fait au clavier. Pour ceux qui connaissent déjà Hyprland.",
        desktopBoth: "KDE Plasma reste installé lui aussi. Vous pourrez passer de l'un à l'autre sur l'écran de connexion.",
        desktopDownload: "Raye télécharge Hyprland pendant l'installation, restez donc connecté à Internet.",

        readyTitle: "Prêt pour l'installation",
        readyText: "Vérifiez ces choix. L'installation commence quand vous sélectionnez Installer.",
        readyErase: "Tout ce qui se trouve sur ce disque sera supprimé, y compris vos fichiers, applications et paramètres.",
        readyRegionCard: "Langue et région",
        readyLanguage: "Langue",
        readyCountry: "Pays ou région",
        readyKeyboard: "Clavier",
        readyDiskCard: "Disque",
        readyDisk: "Lecteur",
        readyWhat: "Ce qui sera fait",
        readyWhatErase: "Effacer tout le disque et installer Raye",
        readyWhatAlongside: "Installer Raye à côté de ce qui se trouve déjà sur le disque",
        readyWhatReplace: "Remplacer une partition par Raye",
        readyWhatOther: "Installer Raye sur ce disque",
        readyEncryption: "Chiffrement",
        readyEncrypted: "Activé. Vous recevrez une clé de récupération après l'installation.",
        readyNotEncrypted: "Désactivé",
        readyAccountCard: "Compte",
        readyName: "Nom",
        readyPcName: "Nom du PC",
        readyDesktop: "Bureau",
        readyDetailsShow: "Afficher les détails du disque",
        readyDetailsHide: "Masquer les détails du disque",

        installingTitle: "Installation de Raye",
        installingText: "Cela prend quelques minutes. Vous pouvez laisser votre PC tranquille.",
        installStarting: "Préparation",
        installStepOf: "Étape %1 sur %2",
        installDisk: "Préparation du disque",
        installCopy: "Copie de Raye",
        installDownload: "Téléchargement des mises à jour et des langues",
        installDrivers: "Installation des pilotes",
        installSetup: "Configuration",
        installFinish: "Finalisation",
        showDetails: "Afficher les détails",
        hideDetails: "Masquer les détails",
        tipStart: "Appuyez sur la touche Windows pour ouvrir Démarrer : vos applications, fichiers et paramètres au même endroit.",
        tipStore: "Installez applications et jeux en un clic depuis Raye Store.",
        tipFiles: "Vos fichiers ont leur place dans Fichiers, avec Documents, Images et Téléchargements prêts.",
        tipUpdate: "Les mises à jour s'installent pendant que vous travaillez. Seules celles qui l'exigent attendent un redémarrage.",

        doneTitle: "Raye est installé",
        doneText: "Votre PC redémarre pour terminer. Retirez la clé USB quand l'écran devient noir.",
        restartIn: "Redémarrage dans %1 s",
        failedTitle: "Un problème est survenu",
        failedText: "Raye n'a pas pu être installé.",
        failedDetails: "Ce qui s'est passé",
        failedRestart: "Redémarrez votre PC et réessayez. Si cela se reproduit, les détails ci-dessous aident à en trouver la cause.",
        failedMedium: "La clé USB de démarrage n'a pas pu être lue correctement\u00a0: mal écrite ou usée, sans doute. Écrivez-la de nouveau, sur une autre clé si possible, et recommencez.",
        licences: "Licences",
        licenceText: "L'installation de Raye utilise Calamares, logiciel libre sous licence GNU GPL 3.0 ou ultérieure. © 2014-2017 Teo Mrnjavac, © 2017-2024 Adriaan de Groot et l'équipe Calamares."
    }
}

function t(lang, key, args) {
    var table = words[lang] || words.en
    var text = table[key] !== undefined ? table[key] : words.en[key]
    if (text === undefined)
        return key
    if (args)
        for (var i = 0; i < args.length; ++i)
            text = text.replace("%" + (i + 1), args[i])
    return text
}

// "en" or "fr": the language of Raye's own words, from what Calamares uses
// now (it follows the language page). Every other language reads English.
function current(locale) {
    return String(locale.name).indexOf("fr") === 0 ? "fr" : "en"
}

// the language itself, "es" for es_ES: for what Calamares translates
function code(locale) {
    return String(locale.name).split("_")[0]
}

// A language's own name, as Qt hands it over (QLocale::nativeLanguageName
// through config.languagesModel): "English", "Deutsch" -- but "français",
// "español", "italiano", lower case. That lower case is right in French
// prose and wrong in a LIST whose neighbours are capitals, which is how
// the 2026-11-02 image showed "français" between "English" and "Deutsch".
// Every row is capitalised, so the list reads one way; nothing else in
// Setup capitalises a language name.
function listName(label) {
    var name = String(label)
    return name.length === 0 ? name : name.charAt(0).toUpperCase() + name.slice(1)
}

// The name of a row of the language list. Calamares' "en" is English
// whatever the country: the region page decides en_CA, en_GB and so on. Qt
// calls that row "American English" (the native name of en_US), and the
// "Ready to install" page then spoke of another English than the one picked.
function languageRow(label, englishLabel) {
    return englishLabel === "English" ? "English" : listName(label)
}

// What raye-preflight can print, in the order the card shows them.
var diskFindings = ["bitlocker", "hibernated", "ntfs-dirty", "ntfs-check",
                    "ntfs-busy", "ntfs-unknown", "shared-efi", "linux-hibernated"]

// What the disk page can say about one volume it won't make smaller, on
// top of those: none of them comes from raye-preflight.
var volumeFindings = ["linux-check", "linux-unknown", "btrfs-multi", "xfs", "encrypted", "lvm"]

// The findings the language page warns about. shared-efi is not one any
// more: Raye makes its own EFI partition next to the other system.
function warnings(found) {
    return found.filter(function(f) { return diskFindings.indexOf(f) >= 0 && f !== "shared-efi" })
}

// The ones Windows itself has to fix. The rest are not Windows' doing, and
// the card's title must not say they are: the 2026-11-02 image headed a
// card "Before you install next to Windows" whose only line read "Another
// Linux system is on this disk".
// ntfs-busy and ntfs-unknown are not: something else is holding the
// volume, or we could not read it, and neither is a thing Windows fixes.
var windowsFindings = ["bitlocker", "hibernated", "ntfs-dirty", "ntfs-check"]

// raye-preflight prints "shared-efi"; the words of it are under "sharedEfi".
function findingKey(finding) {
    return String(finding).replace(/-([a-z])/g, function(all, letter) {
        return letter.toUpperCase()
    })
}

function beforeKey(found) {
    for (var i = 0; i < found.length; ++i)
        if (windowsFindings.indexOf(found[i]) >= 0)
            return "beforeTitle"
    return "beforeTitleDisk"
}

// What to tell the person under a failed install. Reading the image off
// the stick is the step a badly written or worn stick fails, and the cure
// is a new stick, not a restart.
var mediumErrors = ["casper/filesystem.squashfs", "Input/output error", "SQUASHFS error"]
function failureKey(message, details) {
    var text = String(message || "") + "\n" + String(details || "")
    for (var i = 0; i < mediumErrors.length; ++i)
        if (text.indexOf(mediumErrors[i]) >= 0)
            return "failedMedium"
    return "failedRestart"
}

// ------------------------------------------------ while Raye installs

// Calamares hands the slideshow NO progress, so this page must not
// invent any. Measured 2026-11-06 against Calamares 3.3.14:
// registerQmlModels (utils/Qml.h) publishes io.calamares.ui.Branding,
// io.calamares.core.ViewManager and io.calamares.core.Global -- and
// `strings` over libcalamares*.so finds exactly those three namespaces --
// while ViewManager carries no percent among its properties. The
// percentage is on JobQueue::progress(qreal, QString), a C++ signal
// ExecutionViewStep consumes to fill its OWN bar (#exec-progress) and its
// own message (#exec-message), both drawn under the slideshow and both
// styled in stylesheet.qss. The true figure is therefore already on
// screen; a second one interpolated on elapsed time could only disagree
// with it, and a bar stuck at 99 % is what makes people cut the power in
// the middle of a disk write.
//
// What this page adds is the stage in plain words, read from the job
// names in Calamares' session log.

// TWO orders, and they are NOT one list.
//
//   installStageOrder  where a stage sits in "Step N of M": the order the
//                      exec sequence of settings.conf runs them in.
//   installStageRules  the order the words are TRIED in, which has to
//                      disagree with the above in two measured places:
//                        "Unmount file systems."  holds "mount"    (disk)
//                        "Configure GRUB."        holds "configur" (setup)
//                      so installFinish is tried before both. Sorting the
//                      rules by the display order would put the end of the
//                      install back at its beginning, in silence.
var installStageOrder = ["installDisk", "installCopy", "installDownload",
                         "installDrivers", "installSetup", "installFinish"]

// Calamares' jobs, by words of their names in English and French. The
// names were read off the installed modules on 2026-11-06, French from
// /usr/share/locale/fr/LC_MESSAGES/calamares-python.mo.
var installStageRules = [
    // "filling"/"remplir" is unpackfs -- "Filling up filesystems." and
    // "Remplir les systèmes de fichiers." -- and NO word of this table
    // matched it until 2026-11-06. Copying is the longest part of an
    // install, and the page spent all of it still saying "Getting the disk
    // ready". "filling" rather than "filesystem": umount says "Unmount
    // file systems", which would have landed here.
    { key: "installCopy", words: ["filling", "remplir", "unpack", "extract", "décompress", "copie"] },
    { key: "installDownload", words: ["package", "paquet"] },
    { key: "installDrivers", words: ["driver", "pilote"] },
    // "log" was in this list and had to go. It was meant for
    // shellprocess@logs, which cannot match it -- shellprocess has no name
    // setting, so every one of the six instances is called Calamares' own
    // "Shell Processes Job" (measured on 3.3.14). Zero true matches, and one
    // real false one: the French name of the clock job, "Configuration de
    // l'horloge matériel.", holds l-o-g inside hor-LOG-e. The middle of a
    // French install therefore announced the LAST stage, then went back.
    { key: "installFinish", words: ["bootloader", "initramfs", "grub", "unmount", "démont", "chargeur"] },
    { key: "installSetup", words: ["user", "utilisateur", "locale", "keyboard", "clavier", "hostname", "machine",
                                   "fstab", "configur", "setting", "réglage", "network", "réseau", "clock",
                                   "horloge", "display", "affichage", "encrypt", "chiffr"] },
    { key: "installDisk", words: ["partition", "format", "mount", "flag", "luks", "disk", "disque"] }
]

// The stage a job name belongs to, "" when no rule knows it. The caller
// keeps the stage it had: a job nobody listed is no reason to claim a
// different part of the install, and it is no reason to claim one before
// the first job either.
function installStageOf(job) {
    var name = String(job).toLowerCase()
    for (var i = 0; i < installStageRules.length; ++i) {
        var rule = installStageRules[i]
        for (var w = 0; w < rule.words.length; ++w)
            if (name.indexOf(rule.words[w]) >= 0)
                return rule.key
    }
    return ""
}

// Where a stage sits: {step: 1..count, count: n}, and step 0 for a stage
// nobody ordered -- no number at all rather than a wrong one.
function installStep(stage) {
    return { step: installStageOrder.indexOf(stage) + 1,
             count: installStageOrder.length }
}

// The steps of settings.conf's show sequence, by position, and the stage
// each one belongs to in the progress line of the top bar.
var steps = ["language", "region", "keyboard", "network", "disk", "device",
             "account", "user", "privacy", "desktop", "ready", "installing", "done"]
var stages = [
    { key: "stageRegion", steps: ["language", "region", "keyboard"] },
    { key: "stageNetwork", steps: ["network"] },
    { key: "stageDisk", steps: ["disk"] },
    { key: "stageAccount", steps: ["device", "account", "user"] },
    { key: "stagePrivacy", steps: ["privacy"] },
    { key: "stageDesktop", steps: ["desktop"] },
    { key: "stageInstall", steps: ["ready", "installing", "done"] }
]

function stageOf(index) {
    var step = steps[index]
    for (var i = 0; i < stages.length; ++i)
        if (stages[i].steps.indexOf(step) >= 0)
            return i
    return 0
}
