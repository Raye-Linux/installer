// SPDX-License-Identifier: GPL-3.0-or-later
//
// raye-first-run: the welcome after the first sign-in. Today it owns one
// page, the one that hands over the disk recovery key of an encrypted
// install.
//
// Why this program exists at all. The installer's encryption job
// (usr/lib/calamares/modules/rayeencryption/main.py) shows the key itself
// ONLY when /usr/bin/raye-first-run is missing from the new system, and
// what it shows is a kdialog --msgbox: a QtWidgets message box, carrying
// the 48 digits in plain text, with one OK button and none of the Raye
// look, because kdialog cannot load org.raye.setup. That box had been the
// first window of every encrypted Raye install since the job was written,
// for the simple reason that this binary did not exist. Shipping it is
// what turns that branch off -- leave_notice() already looks for this
// path.
//
// The window and the page do no file work: everything that touches the
// disk is in Keeper below, so the page can be driven with a fake key
// (tests/ui/tst_firstrun.qml).
#include <QGuiApplication>
#include <QDir>
#include <QFile>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QSaveFile>
#include <QStandardPaths>
#include <QTextStream>
#include <QUrl>

namespace {

// Where the installer leaves the key, and where Settings' security page
// is meant to read it (rayeencryption/main.py: KEY_FILE).
QString keyPath()
{
    return QDir::homePath() + QStringLiteral("/.local/share/raye/recovery-key");
}

// Written once the person says the key is written down. Its presence is
// what keeps the welcome from coming back.
QString stampPath()
{
    const QString config = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    return (config.isEmpty() ? QDir::homePath() + QStringLiteral("/.config") : config)
           + QStringLiteral("/raye-first-run");
}

class Keeper : public QObject
{
    Q_OBJECT
public:
    using QObject::QObject;

    // The key as the installer wrote it, or empty when there is none --
    // an install that was not encrypted, or a key already dealt with.
    Q_INVOKABLE QString readKey() const
    {
        QFile file(keyPath());
        if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
            return {};
        // a key is 55 characters; refuse to read a file that is not one
        return QString::fromLatin1(file.read(256)).trimmed();
    }

    Q_INVOKABLE QString documentsFolder() const
    {
        const QString documents = QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation);
        return QUrl::fromLocalFile(documents.isEmpty() ? QDir::homePath() : documents).toString();
    }

    Q_INVOKABLE QString suggestedName() const
    {
        return QStringLiteral("Raye recovery key.txt");
    }

    // A copy the person keeps. 0600 like the key file itself: a copy of a
    // secret is still a secret, even when its owner chose where it goes.
    Q_INVOKABLE bool saveCopy(const QUrl &where, const QString &key, const QString &why) const
    {
        if (!where.isLocalFile() || key.isEmpty())
            return false;
        QSaveFile file(where.toLocalFile());
        if (!file.open(QIODevice::WriteOnly | QIODevice::Text))
            return false;
        file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
        QTextStream out(&file);
        out << key << "\n\n" << why << "\n";
        return out.status() == QTextStream::Ok && file.commit();
    }

    Q_INVOKABLE void markSaved() const
    {
        QDir().mkpath(QFileInfo(stampPath()).path());
        QSaveFile stamp(stampPath());
        if (stamp.open(QIODevice::WriteOnly | QIODevice::Text)) {
            stamp.write("[First run]\nRecoveryKey=saved\n");
            stamp.commit();
        }
    }
};

} // namespace

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QGuiApplication::setApplicationName(QStringLiteral("raye-first-run"));
    QGuiApplication::setDesktopFileName(QStringLiteral("raye-first-run"));

    Keeper keeper;
    // Already done, so nothing to show. No window is ever created: the
    // autostart entry can stay in place without costing a flash of night.
    if (QFile::exists(stampPath()))
        return 0;
    // Nothing to hand over -- an install that was not encrypted. No stamp
    // either, so the day the welcome grows its other pages it still runs.
    if (keeper.readKey().isEmpty())
        return 0;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("Keeper"), &keeper);
    engine.load(QUrl(QStringLiteral("qrc:/raye/firstrun/Main.qml")));
    if (engine.rootObjects().isEmpty())
        return 1;
    return QGuiApplication::exec();
}

#include "main.moc"
