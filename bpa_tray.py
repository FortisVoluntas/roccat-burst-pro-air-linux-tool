#!/usr/bin/python3
# Copyright (C) 2026 FortisVoluntas (https://github.com/FortisVoluntas)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ladestand der ROCCAT Burst Pro Air als Symbol in der Kontrollleiste.

Das Symbol erscheint nur, solange die Maus per USB erreichbar ist, am Kabel oder
ueber den Dongle. Im Bluetooth-Betrieb bleibt es aus: Dort fuehrt der Rechner das
Geraet ueber UPower bereits selbst, es gaebe sonst zwei Anzeigen nebeneinander.

Der erste Blick kommt AUFSCHUB Millisekunden nach dem Start, damit die Maus nach
dem Hochfahren sicher angemeldet ist, danach alle ABFRAGE Millisekunden.
"""
import json
import os
import sys

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import bpa_led
from bpa_gui import EINSTELLUNGEN, GRUND, akkufarbe

HIER = os.path.dirname(os.path.abspath(__file__))
AUFSCHUB = 60_000
ABFRAGE = 60_000
KANTE = 64

TEXTE = {
    "de": {
        "stand": "Burst Pro Air: {prozent} %",
        "zeile2": "{modus}, Zellspannung {mv} mV",
        "kabel": "Kabel",
        "funk": "Funk",
        "nachsehen": "Jetzt nachsehen",
        "oeffnen": "Beleuchtung öffnen",
        "beenden": "Beenden",
    },
    "en": {
        "stand": "Burst Pro Air: {prozent} %",
        "zeile2": "{modus}, cell voltage {mv} mV",
        "kabel": "wired",
        "funk": "dongle",
        "nachsehen": "Check now",
        "oeffnen": "Open lighting",
        "beenden": "Quit",
    },
}


def sprache():
    """Nimmt die Sprache, die in der Oberflaeche gewaehlt wurde."""
    try:
        with open(EINSTELLUNGEN) as fd:
            gewaehlt = json.load(fd)["sprache"]
    except (OSError, ValueError, KeyError):
        return "de"
    return gewaehlt if gewaehlt in TEXTE else "de"


def symbol(farbe):
    """Zeichnet die Maus von oben, durchgefaerbt in der Farbe des Ladestands.

    Der Koerper traegt die Farbe als Flaeche, Rad und Tastentrennung sind dunkel
    hineingeschnitten. Ein blosser Umriss war in Leistengroesse zu duenn, um die
    Farbe noch zu erkennen.
    """
    bild = QPixmap(KANTE, KANTE)
    bild.fill(Qt.GlobalColor.transparent)
    maler = QPainter(bild)
    maler.setRenderHint(QPainter.RenderHint.Antialiasing)
    ton = QColor(farbe)
    dunkel = QColor(GRUND)
    maler.setPen(QPen(ton.darker(135), 3))
    maler.setBrush(ton)
    maler.drawRoundedRect(14, 4, 36, 56, 17, 17)
    maler.setPen(QPen(dunkel, 4))
    maler.drawLine(32, 6, 32, 25)
    maler.setPen(Qt.PenStyle.NoPen)
    maler.setBrush(dunkel)
    maler.drawRoundedRect(29, 13, 7, 15, 3, 3)
    maler.end()
    return QIcon(bild)


class Anzeige(QSystemTrayIcon):
    """Symbol in der Leiste, das sich einmal je Minute selbst nachfuehrt."""

    def __init__(self):
        super().__init__()
        self.texte = TEXTE[sprache()]
        menue = QMenu()
        for schluessel, tat in (("nachsehen", self.nachsehen),
                                ("oeffnen", self.oberflaeche_starten),
                                ("beenden", QApplication.quit)):
            eintrag = QAction(self.texte[schluessel], menue)
            eintrag.triggered.connect(tat)
            menue.addAction(eintrag)
        self.menue = menue
        self.setContextMenu(menue)
        self.activated.connect(self.angeklickt)

        self.takt = QTimer(self)
        self.takt.timeout.connect(self.nachsehen)
        QTimer.singleShot(AUFSCHUB, self.erster_blick)

    def erster_blick(self):
        self.nachsehen()
        self.takt.start(ABFRAGE)

    def nachsehen(self):
        """Liest den Ladestand; bleibt beim letzten Wert, wenn er ausbleibt."""
        gefunden = bpa_led.geraet_finden()
        if gefunden is None:
            self.hide()
            return
        try:
            prozent, millivolt = bpa_led.akkustand()
        except (OSError, RuntimeError):
            return
        _pfad, modus = gefunden
        self.setIcon(symbol(akkufarbe(prozent)))
        self.setToolTip(f"{self.texte['stand'].format(prozent=prozent)}\n"
                        f"{self.texte['zeile2'].format(modus=self.texte[modus], mv=millivolt)}")
        self.show()

    def angeklickt(self, grund):
        if grund == QSystemTrayIcon.ActivationReason.Trigger:
            self.nachsehen()

    def oberflaeche_starten(self):
        # startDetached statt subprocess: Das Symbol laeuft die ganze Sitzung und
        # muesste sonst jedes gestartete Fenster abholen.
        QProcess.startDetached(os.path.join(HIER, "burst-pro-air"))


if __name__ == "__main__":
    anwendung = QApplication(sys.argv)
    anwendung.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        raise SystemExit("Keine Kontrollleiste gefunden.")
    anzeige = Anzeige()
    sys.exit(anwendung.exec())
