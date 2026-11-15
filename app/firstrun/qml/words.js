// Words of the welcome after the first sign-in, English and French. The
// pages read them through t(); tst_firstrun.qml checks both languages
// carry the same keys and that none is left untranslated.
//
//   import "words.js" as W
//   Text { text: W.t(page.lang, "heading") }
//
// No key here is called "title", "text", "description", "detail",
// "errorText" or "placeholderText". tests/test_i18n.py sweeps every .qml
// and .js of this folder for those names followed by a literal, because
// that is a string going on the screen without passing through t(); a
// table key spelled like one of them would be read as exactly that
// defect. Same rule as the branding's strings.js.
.pragma library

var words = {
    en: {
        heading: "Write down your recovery key",
        why: "Your disk is encrypted. If you forget its password or move the disk to "
             + "another PC, this key is the only way to open it. Keep it somewhere other "
             + "than this PC.",
        copy: "Copy",
        copied: "Copied",
        save: "Save a copy…",
        savedBox: "I saved my recovery key",
        done: "Done",
        later: "Later",
        fileKind: "Text file (*.txt)"
    },
    fr: {
        heading: "Notez votre clé de récupération",
        why: "Votre disque est chiffré. Si vous oubliez son mot de passe ou si vous "
             + "déplacez le disque dans un autre PC, cette clé est le seul moyen de "
             + "l'ouvrir. Gardez-la ailleurs que sur ce PC.",
        copy: "Copier",
        copied: "Copiée",
        save: "Enregistrer une copie…",
        savedBox: "J'ai noté ma clé de récupération",
        done: "Terminé",
        later: "Plus tard",
        fileKind: "Fichier texte (*.txt)"
    }
};

// The word for key in lang, falling back to English rather than showing
// the key name: a missing translation must read as a sentence, not as
// "heading". tst_firstrun.qml is what keeps the two tables level.
function t(lang, key) {
    var table = words[lang] || words.en;
    if (table[key] !== undefined)
        return table[key];
    return words.en[key] !== undefined ? words.en[key] : "";
}

function keys(lang) {
    return Object.keys(words[lang] || {}).sort();
}

function languages() {
    return Object.keys(words).sort();
}
