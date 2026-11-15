# Raye Linux installer

Everything between the USB stick and the first desktop: the setup that
starts when the stick boots (language, keyboard, install or try), the
installer pages (network, disk, account, progress, done), the scripts the
install runs, and the welcome shown after the first sign-in. The installer
is [Calamares](https://calamares.io) with Raye's pages and look.

- `etc/calamares/` the Calamares settings and the Raye branding
- `qml/`, `app/` the setup and welcome screens
- `usr/` scripts and job modules installed on the live system
- `tests/` the tests

## Build and test

    cmake -S . -B out && cmake --build out && ctest --test-dir out --output-on-failure

To build the packages: `dpkg-buildpackage -b -us -uc`. `VERSION` mirrors
the one in the iso repository; a test keeps the two equal.

## License

GPL-3.0-or-later (`LICENSE`), artwork CC BY-SA 4.0.

## Links

- Website: https://rayelinux.com
- Discord: https://discord.gg/TrxhUkabyB (questions, bug reports, news)
