#!/bin/bash
# Copyright (C) 2026 FortisVoluntas (https://github.com/FortisVoluntas)
# SPDX-License-Identifier: GPL-3.0-or-later
# Legt den Menueintrag an und installiert die udev-Regel. Laeuft als normaler
# Benutzer; nur die Regel geht ueber sudo.
set -e

hier="$(dirname "$(readlink -f "$0")")"

if ! /usr/bin/python3 -c 'import PyQt6.QtWidgets' 2>/dev/null; then
    echo "PyQt6 is missing, so the window will not start."
    echo "Install python3-pyqt6 (python-pyqt6 on Arch) and run this again."
    echo "The command line tool bpa_led.py works without it."
    echo
fi

anwendungen="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$anwendungen"
while IFS= read -r zeile; do
    case "$zeile" in
        # gequotet, sonst zerfaellt ein Pfad mit Leerzeichen in zwei Argumente
        Exec=*) printf 'Exec="%s"\n' "$hier/burst-pro-air" ;;
        *) printf '%s\n' "$zeile" ;;
    esac
done < "$hier/burst-pro-air.desktop" > "$anwendungen/burst-pro-air.desktop"
echo "Menu entry written to $anwendungen/burst-pro-air.desktop"

# Das Symbol in der Kontrollleiste startet mit der Sitzung. Es braucht einen
# Tray nach StatusNotifierItem; GNOME Shell hat keinen, siehe README.
autostart="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$autostart"
while IFS= read -r zeile; do
    case "$zeile" in
        Exec=*) printf 'Exec="%s"\n' "$hier/bpa_tray.py" ;;
        *) printf '%s\n' "$zeile" ;;
    esac
done < "$hier/burst-pro-air-tray.desktop" > "$autostart/burst-pro-air-tray.desktop"
echo "Battery icon autostart written to $autostart/burst-pro-air-tray.desktop"

echo "The udev rule needs root:"
sudo install -m 644 "$hier/udev/99-roccat-burst-pro-air.rules" /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger

echo
echo "Done. Plug the cable in again so the new permissions apply."
