#!/usr/bin/python3
# Copyright (C) 2026 FortisVoluntas (https://github.com/FortisVoluntas)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Oberflaeche fuer Beleuchtung und DPI der ROCCAT Burst Pro Air."""
import json
import math
import os
import random
import sys
import threading

from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath,
    QPainterPathStroker, QPen, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QApplication, QColorDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

import bpa_led

GRUND = "#0a0a0b"
FLAECHE_OBEN = "#121215"
FLAECHE_UNTEN = "#191a1e"
LINIE = "rgba(255,255,255,0.075)"
TEXT = "#dfe1e5"
TEXT_GEDAEMPFT = "#8d9097"
TEXT_LEISE = "#5c5f66"
SILBER = "#d4dae2"
GRUEN = "#82ab7c"
NEUTRAL = "#8e959f"
ROT = "#8c2b23"

# Vier Stufen zu 25 Prozent fuer den Ladestand. Gelb und Orange sind eigens
# entsaettigt, damit neben Gruen und Rot keine Ampel entsteht.
GELB = "#b3a45c"
ORANGE = "#b07a45"
AKKUSTUFEN = ((75, GRUEN), (50, GELB), (25, ORANGE), (0, ROT))
AKKU_TAKT = 60_000

SANS = ["Inter", "Noto Sans", "DejaVu Sans", "Segoe UI", "Roboto", "Arial", "sans-serif"]
SCHREIBMASCHINE = ["Special Elite", "Courier New", "DejaVu Sans Mono", "monospace"]
EMOJI = ["Noto Color Emoji", "Noto Emoji"] + SANS

EINSTELLUNGEN = os.path.expanduser("~/.config/burst-pro-air/zonen.json")
VORGABE = [{"farbe": "#000000", "hell": 0}] + [{"farbe": "#ffffff", "hell": 100}] * 3

TEXTE = {
    "de": {
        "flagge": "\U0001F1E9\U0001F1EA",
        "titel": "Burst Pro Air - Beleuchtung",
        "zonen": bpa_led.ZONEN,
        "kabel": "KABEL",
        "kabel_hinweis": "Die Maus hängt am Kabel. Ein Druck auf ÜBERNEHMEN schreibt "
                         "Farben und DPI-Stufen in ihr Profil.",
        "funk": "FUNK",
        "funk_hinweis": "Die Maus läuft über den Dongle und nimmt auf diesem Weg keine "
                        "Änderungen an. Zum Ändern das USB-Kabel einstecken, die "
                        "Einstellung bleibt danach auch im Funkbetrieb erhalten.",
        "fehlt": "NICHT GEFUNDEN",
        "fehlt_hinweis": "Keine Burst Pro Air gefunden, weder am Kabel noch über den "
                         "Dongle. Kabel einstecken; die Anzeige prüft alle zwei Sekunden nach.",
        "akku": "AKKU",
        "beleuchtung": "BELEUCHTUNG",
        "beleuchtung_hinweis": "Auf ein Farbfeld in der Mausansicht klicken, um die Farbe "
                               "der Zone zu wählen. Der Regler daneben stellt ihre "
                               "Helligkeit ein, 0 % schaltet die Zone aus.",
        "dpi": "DPI-STUFEN",
        "dpi_hinweis": "ANZAHL ist die Zahl der Stufen, die der DPI-Knopf durchschaltet, "
                       "START die Stufe nach dem Aufwachen. Übernehmen schreibt Farben "
                       "und DPI immer zusammen.",
        "anzahl": "ANZAHL",
        "start": "START",
        "uebernehmen": "ÜBERNEHMEN",
        "fuss": "DIE EINSTELLUNG LIEGT IM PROFIL DER MAUS UND GILT AUCH IM FUNKBETRIEB",
        "farbe_waehlen": "Farbe wählen",
        "erfolg": "Farben und DPI-Stufen stehen im Profil der Maus (geschrieben über {pfad}).",
    },
    "en": {
        "flagge": "\U0001F1EC\U0001F1E7",
        "titel": "Burst Pro Air - Lighting",
        "zonen": ("Scroll Wheel", "Left Button", "Right Button", "Palm Rest"),
        "kabel": "CABLE",
        "kabel_hinweis": "The mouse is connected by cable. Pressing APPLY writes colours "
                         "and DPI stages into its profile.",
        "funk": "WIRELESS",
        "funk_hinweis": "The mouse runs over the dongle and accepts no changes that way. "
                        "Plug in the USB cable to change it, the setting stays in place "
                        "in wireless mode afterwards.",
        "fehlt": "NOT FOUND",
        "fehlt_hinweis": "No Burst Pro Air found, neither by cable nor over the dongle. "
                         "Plug in the cable; the display checks again every two seconds.",
        "akku": "BATTERY",
        "beleuchtung": "LIGHTING",
        "beleuchtung_hinweis": "Click a colour patch on the mouse view to choose that "
                               "zone's colour. The slider next to it sets the brightness, "
                               "0 % turns the zone off.",
        "dpi": "DPI STAGES",
        "dpi_hinweis": "COUNT is how many stages the DPI button cycles through, START the "
                       "stage after the wake-up. Applying always writes colours and DPI "
                       "together.",
        "anzahl": "COUNT",
        "start": "START",
        "uebernehmen": "APPLY",
        "fuss": "THE SETTING LIVES IN THE MOUSE PROFILE AND APPLIES OVER THE DONGLE",
        "farbe_waehlen": "Choose colour",
        "erfolg": "Colours and DPI stages are in the mouse profile (written via {pfad}).",
    },
}
SPRACHE = "de"


def t(schluessel):
    return TEXTE[SPRACHE][schluessel]


def akkufarbe(prozent):
    for grenze, farbe in AKKUSTUFEN:
        if prozent >= grenze:
            return farbe
    return ROT


_KORN = None


def korn():
    """Kachelbares Filmkorn, einmal erzeugt (Farbschema: Deckkraft rund 5 %)."""
    global _KORN
    if _KORN is None:
        zufall = random.Random(7)
        punkte = bytearray()
        for _ in range(128 * 128):
            a = zufall.randrange(15)
            punkte += bytes((a, a, a, a))
        bild = QImage(bytes(punkte), 128, 128,
                      QImage.Format.Format_ARGB32_Premultiplied).copy()
        _KORN = QPixmap.fromImage(bild)
    return _KORN


def schrift(familien, groesse, fett=False, sperrung=0.0):
    f = QFont()
    f.setFamilies(familien)
    f.setPointSize(groesse)
    f.setBold(fett)
    if sperrung:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, sperrung)
    return f


class Panel(QFrame):
    """Flaeche mit L-foermigen Eckwinkeln statt durchgezogenem Rahmen."""

    def paintEvent(self, ereignis):
        super().paintEvent(ereignis)
        maler = QPainter(self)
        # Korn am Fenster ausgerichtet, damit es ueber die Panelkanten durchlaeuft.
        maler.drawTiledPixmap(self.rect(), korn(), self.mapTo(self.window(), QPoint(0, 0)))
        maler.setPen(QPen(QColor(255, 255, 255, 20), 1))
        maler.drawLine(self.rect().left() + 3, self.rect().top(),
                       self.rect().right() - 3, self.rect().top())
        maler.setPen(QPen(QColor(255, 255, 255, 107), 1))
        laenge = 9
        r = self.rect().adjusted(0, 0, -1, -1)
        for x, y, dx, dy in (
            (r.left(), r.top(), 1, 1), (r.right(), r.top(), -1, 1),
            (r.left(), r.bottom(), 1, -1), (r.right(), r.bottom(), -1, -1),
        ):
            maler.drawLine(x, y, x + dx * laenge, y)
            maler.drawLine(x, y, x, y + dy * laenge)


class Haarlinie(QFrame):
    """Duenner Trenner ueber die volle Breite."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(1)
        self.setObjectName("haarlinie")


class Abschnitt(QWidget):
    """Ueberschrift mit auslaufender Haarlinie."""

    def __init__(self):
        super().__init__()
        self.beschriftung = QLabel()
        self.beschriftung.setFont(schrift(SCHREIBMASCHINE, 9, sperrung=1.6))
        self.beschriftung.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")

        aufbau = QHBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.setSpacing(12)
        aufbau.addWidget(self.beschriftung)
        aufbau.addWidget(Haarlinie(), 1)

    def beschriften(self, text):
        self.beschriftung.setText(text)


class Statuslicht(QWidget):
    """Punkt mit Lichthof, langsam pulsierend."""

    def __init__(self):
        super().__init__()
        self.farbe = QColor(NEUTRAL)
        self.phase = 0.0
        self.setFixedSize(18, 18)
        self.takt = QTimer(self)
        self.takt.timeout.connect(self._weiter)
        self.takt.start(90)

    def setzen(self, farbe):
        self.farbe = QColor(farbe)
        self.update()

    def _weiter(self):
        self.phase = (self.phase + 0.09) % (2 * math.pi)
        self.update()

    def paintEvent(self, ereignis):
        anteil = 0.62 + 0.38 * (math.sin(self.phase) + 1) / 2
        mitte = QPointF(self.width() / 2, self.height() / 2)
        maler = QPainter(self)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)
        maler.setPen(Qt.PenStyle.NoPen)

        hof = QRadialGradient(mitte, 9)
        glut = QColor(self.farbe)
        glut.setAlpha(int(80 * anteil))
        hof.setColorAt(0.0, glut)
        hof.setColorAt(1.0, QColor(self.farbe.red(), self.farbe.green(), self.farbe.blue(), 0))
        maler.setBrush(hof)
        maler.drawEllipse(mitte, 9, 9)

        kern = QColor(self.farbe)
        kern.setAlpha(int(200 + 55 * anteil))
        maler.setBrush(kern)
        maler.drawEllipse(mitte, 3.2, 3.2)


class Akku(QWidget):
    """Ladestand der Maus: Licht in der Stufenfarbe, Prozentwert daneben.

    Gelesen wird in einem eigenen Faden, weil die Abfrage ueber den Dongle rund
    eine halbe Sekunde dauert und das Fenster so lange stehenbliebe.
    """

    gelesen = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.laeuft = False

        self.licht = Statuslicht()
        self.beschriftung = QLabel()
        self.beschriftung.setFont(schrift(SCHREIBMASCHINE, 9, sperrung=1.6))
        self.beschriftung.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")
        self.wert = QLabel("--")
        self.wert.setFont(schrift(SCHREIBMASCHINE, 11))
        self.spannung = QLabel(" ")
        self.spannung.setFont(schrift(SCHREIBMASCHINE, 8))
        self.spannung.setStyleSheet(f"color: {TEXT_LEISE};")

        kopf = QHBoxLayout()
        kopf.setSpacing(9)
        kopf.addWidget(self.licht)
        kopf.addWidget(self.beschriftung)
        kopf.addStretch()
        kopf.addWidget(self.wert)

        aufbau = QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.setSpacing(2)
        aufbau.addLayout(kopf)
        aufbau.addWidget(self.spannung, 0, Qt.AlignmentFlag.AlignRight)

        self.gelesen.connect(self.anzeigen)
        self.takt = QTimer(self)
        self.takt.timeout.connect(self.nachsehen)
        self.takt.start(AKKU_TAKT)
        self.nachsehen()

    def beschriften(self):
        self.beschriftung.setText(t("akku"))

    def nachsehen(self):
        if self.laeuft:
            return
        self.laeuft = True
        threading.Thread(target=self._lesen, daemon=True).start()

    def _lesen(self):
        try:
            werte = bpa_led.akkustand()
        except (OSError, RuntimeError):
            werte = None
        self.gelesen.emit(werte)

    def anzeigen(self, werte):
        self.laeuft = False
        if werte is None:
            self.licht.setzen(NEUTRAL)
            self.wert.setText("--")
            self.wert.setStyleSheet(f"color: {TEXT_LEISE};")
            self.spannung.setText(" ")
            return
        prozent, millivolt = werte
        farbe = akkufarbe(prozent)
        self.licht.setzen(farbe)
        self.wert.setText(f"{prozent} %")
        self.wert.setStyleSheet(f"color: {farbe};")
        self.spannung.setText(f"{millivolt} mV")


class Maus(QWidget):
    """Die Maus von oben. Jede Zone leuchtet in ihrer Farbe und traegt ein Feld,
    das den Farbwaehler oeffnet."""

    BREITE, HOEHE = 200, 313
    RAHMEN = 22       # Platz um die Silhouette, in dem der Lichtschein liegt
    FELD = 19
    WABE = 7.4
    RAND = 9          # geschlossener Rand, in dem keine Waben sitzen
    # Mittelpunkte der Farbfelder, als Anteil der Zeichenflaeche.
    FELDER = ((0.500, 0.150), (0.300, 0.230), (0.700, 0.230), (0.500, 0.700))
    RAD = QRectF(0.452, 0.058, 0.096, 0.190)   # Mausrad

    def __init__(self, zonen, waehlen):
        super().__init__()
        self.zonen = zonen
        self.waehlen = waehlen
        self.unter_zeiger = None
        self.setFixedSize(self.BREITE + 2 * self.RAHMEN, self.HOEHE + 2 * self.RAHMEN)
        self.setMouseTracking(True)

    # --- Geometrie ---------------------------------------------------------

    def _punkt(self, x, y):
        return QPointF(x * self.BREITE, y * self.HOEHE)

    def _schale(self):
        p = QPainterPath()
        P = self._punkt
        p.moveTo(P(0.500, 0.000))
        p.cubicTo(P(0.652, 0.002), P(0.762, 0.032), P(0.824, 0.108))
        p.cubicTo(P(0.886, 0.192), P(0.924, 0.302), P(0.930, 0.424))
        p.cubicTo(P(0.936, 0.566), P(0.902, 0.686), P(0.860, 0.784))
        p.cubicTo(P(0.808, 0.914), P(0.684, 1.000), P(0.500, 1.000))
        p.cubicTo(P(0.316, 1.000), P(0.192, 0.914), P(0.140, 0.784))
        p.cubicTo(P(0.098, 0.686), P(0.064, 0.566), P(0.070, 0.424))
        p.cubicTo(P(0.076, 0.302), P(0.114, 0.192), P(0.176, 0.108))
        p.cubicTo(P(0.238, 0.032), P(0.348, 0.002), P(0.500, 0.000))
        p.closeSubpath()
        return p

    def _naht(self):
        """Kurve zwischen Tastenpaar und Handablage."""
        p = QPainterPath()
        P = self._punkt
        p.moveTo(P(0.080, 0.400))
        p.cubicTo(P(0.300, 0.520), P(0.700, 0.520), P(0.920, 0.400))
        return p

    def _radbett(self):
        r = self.RAD
        return QRectF(r.x() * self.BREITE, r.y() * self.HOEHE,
                      r.width() * self.BREITE, r.height() * self.HOEHE)

    def _lochflaeche(self):
        """Schale ohne den geschlossenen Rand - nur hier sitzen die Waben."""
        schale = self._schale()
        streifen = QPainterPathStroker()
        streifen.setWidth(2 * self.RAND)
        return schale.subtracted(streifen.createStroke(schale))

    def _zonenpfade(self):
        """Die vier Zonen als Flaechen: Rad, linke Taste, rechte Taste, Handablage."""
        loch = self._lochflaeche()
        oben = QPainterPath()
        oben.moveTo(self._punkt(-0.2, -0.2))
        oben.lineTo(self._punkt(1.2, -0.2))
        oben.lineTo(self._punkt(1.2, 0.400))
        naht = self._naht().toReversed()
        oben.connectPath(naht)
        oben.lineTo(self._punkt(-0.2, 0.400))
        oben.closeSubpath()

        rad = QPainterPath()
        rad.addRoundedRect(self._radbett().adjusted(-3, -3, 3, 3), 4, 4)

        naht_streifen = QPainterPathStroker()
        naht_streifen.setWidth(7)
        graben = naht_streifen.createStroke(self._naht())

        tasten = loch.intersected(oben).subtracted(rad).subtracted(graben)
        links = QPainterPath()
        links.addRect(QRectF(0, 0, 0.486 * self.BREITE, self.HOEHE))
        rechts = QPainterPath()
        rechts.addRect(QRectF(0.514 * self.BREITE, 0, 0.486 * self.BREITE, self.HOEHE))

        return (
            rad.intersected(self._schale()),
            tasten.intersected(links),
            tasten.intersected(rechts),
            loch.subtracted(oben).subtracted(graben),
        )

    def _waben(self, flaeche):
        """Mittelpunkte des versetzten Wabenrasters ueber der Flaeche."""
        r = self.WABE
        breit, hoch = math.sqrt(3) * r, 1.5 * r
        grenzen = flaeche.boundingRect()
        mitten = []
        y = grenzen.top() - hoch
        reihe = 0
        while y < grenzen.bottom() + hoch:
            versatz = breit / 2 if reihe % 2 else 0
            x = grenzen.left() - breit + versatz
            while x < grenzen.right() + breit:
                mitten.append((x, y))
                x += breit
            y += hoch
            reihe += 1
        return mitten

    def _sechseck(self, cx, cy, r):
        ecken = []
        for i in range(6):
            winkel = math.radians(60 * i - 90)
            ecken.append(QPointF(cx + r * math.cos(winkel), cy + r * math.sin(winkel)))
        p = QPainterPath(ecken[0])
        for ecke in ecken[1:]:
            p.lineTo(ecke)
        p.closeSubpath()
        return p

    def _feldrechteck(self, i):
        x, y = self.FELDER[i]
        return QRectF(x * self.BREITE - self.FELD / 2,
                      y * self.HOEHE - self.FELD / 2, self.FELD, self.FELD)

    # --- Zeichnen ----------------------------------------------------------

    def _lichtschein(self, maler):
        """Dunkle Buehne, darauf der Schein in der Mischfarbe der leuchtenden Zonen."""
        mitte = QPointF(self.width() / 2, self.height() * 0.52)
        halb_x, halb_y = self.width() * 0.62, self.height() * 0.56
        buehne = QRadialGradient(mitte, halb_y)
        buehne.setColorAt(0.0, QColor(0, 0, 0, 120))
        buehne.setColorAt(1.0, QColor(0, 0, 0, 0))
        maler.setPen(Qt.PenStyle.NoPen)
        maler.setBrush(buehne)
        maler.drawEllipse(mitte, halb_x, halb_y)

        rot = gruen = blau = gewicht = 0.0
        for zone in self.zonen:
            anteil = zone.regler.value() / 100
            rot += zone.farbe.red() * anteil
            gruen += zone.farbe.green() * anteil
            blau += zone.farbe.blue() * anteil
            gewicht += anteil
        if gewicht <= 0:
            return
        farbe = QColor(int(rot / gewicht), int(gruen / gewicht), int(blau / gewicht))
        schein = QRadialGradient(mitte, halb_y)
        innen = QColor(farbe)
        innen.setAlpha(int(96 * min(1.0, gewicht / len(self.zonen))))
        schein.setColorAt(0.0, innen)
        schein.setColorAt(0.62, QColor(farbe.red(), farbe.green(), farbe.blue(),
                                       innen.alpha() // 4))
        schein.setColorAt(1.0, QColor(farbe.red(), farbe.green(), farbe.blue(), 0))
        maler.setBrush(schein)
        maler.drawEllipse(mitte, halb_x, halb_y)

    def paintEvent(self, ereignis):
        maler = QPainter(self)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._lichtschein(maler)
        maler.translate(self.RAHMEN, self.RAHMEN)

        schale = self._schale()
        verlauf = QLinearGradient(0, 0, 0, self.HOEHE)
        verlauf.setColorAt(0.0, QColor("#1b1c21"))
        verlauf.setColorAt(1.0, QColor("#0e0e11"))
        maler.setBrush(verlauf)
        maler.setPen(QPen(QColor(255, 255, 255, 46), 1.4))
        maler.drawPath(schale)

        # Das Rad ist ein durchgehender Streifen, die drei anderen Zonen sind
        # Lochschale - deshalb die Fallunterscheidung.
        for i, (zone, flaeche) in enumerate(zip(self.zonen, self._zonenpfade())):
            self._zone_leuchten(maler, zone, flaeche, waben=i > 0)

        maler.setPen(QPen(QColor(255, 255, 255, 28), 1.2))
        maler.setBrush(Qt.BrushStyle.NoBrush)
        maler.drawPath(self._naht())
        maler.drawLine(self._punkt(0.5, 0.004), self._punkt(0.5, 0.058))
        maler.drawLine(self._punkt(0.5, 0.248), self._punkt(0.5, 0.452))
        self._rad_zeichnen(maler)

        for i, zone in enumerate(self.zonen):
            self._feld_zeichnen(maler, i, zone)

    def _rad_zeichnen(self, maler):
        """Mausrad mit Riffelung; das Farbfeld sitzt mittig darauf."""
        bett = self._radbett()
        maler.setPen(QPen(QColor(255, 255, 255, 34), 1.2))
        maler.setBrush(Qt.BrushStyle.NoBrush)
        maler.drawRoundedRect(bett, 3, 3)
        maler.setPen(QPen(QColor(0, 0, 0, 120), 1))
        frei = self._feldrechteck(0).adjusted(-3, -3, 3, 3)
        for i in range(1, 9):
            y = bett.top() + bett.height() * i / 9
            if not frei.top() <= y <= frei.bottom():
                maler.drawLine(QPointF(bett.left() + 2, y), QPointF(bett.right() - 2, y))

    def _zone_leuchten(self, maler, zone, flaeche, waben=True):
        anteil = zone.regler.value() / 100
        if anteil <= 0:
            return
        farbe = zone.farbe
        maler.save()
        maler.setClipPath(flaeche)
        maler.setPen(Qt.PenStyle.NoPen)
        kern = QColor(farbe)
        kern.setAlpha(int(200 * anteil))
        if not waben:
            maler.setBrush(kern)
            maler.drawPath(flaeche)
            maler.restore()
            return

        schimmer = QColor(farbe)
        schimmer.setAlpha(int(28 * anteil))
        maler.setBrush(schimmer)
        maler.drawPath(flaeche)

        maler.setBrush(kern)
        for x, y in self._waben(flaeche):
            maler.drawPath(self._sechseck(x, y, self.WABE * 0.78))

        # Bloom: zur Mitte hin heller, damit es nach Licht aussieht und nicht
        # nach lackiertem Kunststoff.
        grenzen = flaeche.boundingRect()
        mitte = grenzen.center()
        bloom = QRadialGradient(mitte, max(grenzen.width(), grenzen.height()) * 0.62)
        hell = QColor(farbe)
        hell.setAlpha(int(70 * anteil))
        bloom.setColorAt(0.0, hell)
        bloom.setColorAt(1.0, QColor(farbe.red(), farbe.green(), farbe.blue(), 0))
        maler.setBrush(bloom)
        maler.drawPath(flaeche)
        maler.restore()

    def _feld_zeichnen(self, maler, i, zone):
        rechteck = self._feldrechteck(i)
        maler.setBrush(zone.farbe)
        gewaehlt = self.unter_zeiger == i
        rand = QColor(SILBER) if gewaehlt else QColor(0, 0, 0, 190)
        maler.setPen(QPen(rand, 2 if gewaehlt else 1.4))
        maler.drawRect(rechteck)
        if not gewaehlt:
            maler.setPen(QPen(QColor(255, 255, 255, 90), 1))
            maler.drawRect(rechteck.adjusted(-1.4, -1.4, 1.4, 1.4))

    # --- Bedienung ---------------------------------------------------------

    def _treffer(self, punkt):
        innen = QPointF(punkt) - QPointF(self.RAHMEN, self.RAHMEN)
        for i in range(len(self.zonen)):
            if self._feldrechteck(i).adjusted(-3, -3, 3, 3).contains(innen):
                return i
        return None

    def mouseMoveEvent(self, ereignis):
        treffer = self._treffer(ereignis.position())
        if treffer != self.unter_zeiger:
            self.unter_zeiger = treffer
            self.setCursor(Qt.CursorShape.PointingHandCursor if treffer is not None
                           else Qt.CursorShape.ArrowCursor)
            self.setToolTip(f'{t("zonen")[treffer]}: {t("farbe_waehlen")}'
                            if treffer is not None else "")
            self.update()

    def leaveEvent(self, ereignis):
        if self.unter_zeiger is not None:
            self.unter_zeiger = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mousePressEvent(self, ereignis):
        treffer = self._treffer(ereignis.position())
        if treffer is not None:
            self.waehlen(treffer)


class Zone(QWidget):
    """Beschriftung, Werteanzeige und Helligkeitsregler einer Zone.

    Die Farbe selbst wird in der Mausansicht gewaehlt.
    """

    def __init__(self, name, zustand):
        super().__init__()

        self.chip = QLabel()
        self.chip.setFixedSize(9, 9)

        self.beschriftung = QLabel(name.upper())
        self.beschriftung.setFont(schrift(SCHREIBMASCHINE, 9, sperrung=1.6))
        self.beschriftung.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")

        self.wert = QLabel()
        self.wert.setFont(schrift(SCHREIBMASCHINE, 9))
        self.wert.setStyleSheet(f"color: {TEXT_LEISE};")

        self.regler = QSlider(Qt.Orientation.Horizontal)
        self.regler.setRange(0, 100)
        self.regler.setValue(zustand["hell"])
        self.regler.valueChanged.connect(self.beschriften)

        kopf = QHBoxLayout()
        kopf.setSpacing(9)
        kopf.addWidget(self.chip)
        kopf.addWidget(self.beschriftung)
        kopf.addStretch()
        kopf.addWidget(self.wert)

        aufbau = QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.setSpacing(5)
        aufbau.addLayout(kopf)
        aufbau.addWidget(self.regler)

        self.faerben(QColor(zustand["farbe"]))

    def faerben(self, farbe):
        """Farbe uebernehmen; das Stylesheet des Farbfelds nur dabei neu setzen."""
        self.farbe = farbe
        self.chip.setStyleSheet(f"background: {farbe.name()};"
                                f" border: 1px solid rgba(255,255,255,0.28);")
        self.beschriften()

    def beschriften(self):
        self.wert.setText(f"{self.farbe.name().upper()[1:]}  {self.regler.value():3d} %")

    def umbenennen(self, name):
        self.beschriftung.setText(name.upper())

    def zustand(self):
        return {"farbe": self.farbe.name(), "hell": self.regler.value()}

    def werte(self):
        return (
            (self.farbe.red(), self.farbe.green(), self.farbe.blue()),
            round(self.regler.value() * 255 / 100),
        )


def drehfeld():
    """Zahlenfeld ohne Systempfeile; Wert per Tastatur oder Mausrad."""
    feld = QSpinBox()
    feld.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    feld.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return feld


class Dpi(Panel):
    """Stufenzahl, Startstufe und die DPI-Werte. Nur die ersten N sind aktiv."""

    def __init__(self, stufen, start):
        super().__init__()
        self.setObjectName("panel")

        self.beschriftung = Abschnitt()

        self.hinweis = QLabel()
        self.hinweis.setFont(schrift(SANS, 9))
        self.hinweis.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")
        self.hinweis.setWordWrap(True)

        self.anzahl_text = QLabel()
        self.start_text = QLabel()
        for kennzeichnung in (self.anzahl_text, self.start_text):
            kennzeichnung.setFont(schrift(SCHREIBMASCHINE, 9, sperrung=1.6))
            kennzeichnung.setStyleSheet(f"color: {TEXT_LEISE};")

        self.anzahl = drehfeld()
        self.anzahl.setFixedWidth(46)
        self.anzahl.setRange(1, bpa_led.DPI_PLAETZE)
        self.anzahl.setValue(len(stufen))
        self.anzahl.valueChanged.connect(self.freischalten)

        self.start = drehfeld()
        self.start.setFixedWidth(46)
        self.start.setRange(1, len(stufen))
        self.start.setValue(start)
        self.start.valueChanged.connect(self.freischalten)

        kopf = QHBoxLayout()
        kopf.setSpacing(8)
        kopf.addWidget(self.beschriftung, 1)
        kopf.addSpacing(6)
        kopf.addWidget(self.anzahl_text)
        kopf.addWidget(self.anzahl)
        kopf.addSpacing(6)
        kopf.addWidget(self.start_text)
        kopf.addWidget(self.start)

        self.felder = []
        self.nummern = []
        gitter = QGridLayout()
        gitter.setHorizontalSpacing(10)
        gitter.setVerticalSpacing(3)
        for i in range(bpa_led.DPI_PLAETZE):
            nummer = QLabel(f"{i + 1}")
            nummer.setFont(schrift(SCHREIBMASCHINE, 8, sperrung=1.2))
            feld = drehfeld()
            feld.setMaximumWidth(96)
            feld.setRange(bpa_led.DPI_MIN, bpa_led.DPI_MAX)
            feld.setSingleStep(bpa_led.DPI_SCHRITT)
            feld.setValue(stufen[i] if i < len(stufen) else stufen[-1])
            self.nummern.append(nummer)
            self.felder.append(feld)
            gitter.addWidget(nummer, 2 * (i // 3), i % 3)
            gitter.addWidget(feld, 2 * (i // 3) + 1, i % 3,
                             Qt.AlignmentFlag.AlignLeft)

        aufbau = QVBoxLayout(self)
        aufbau.setContentsMargins(16, 13, 16, 14)
        aufbau.setSpacing(11)
        aufbau.addLayout(kopf)
        aufbau.addWidget(self.hinweis)
        aufbau.addLayout(gitter)

        self.beschriften()
        self.freischalten()

    def beschriften(self):
        self.beschriftung.beschriften(t("dpi"))
        self.hinweis.setText(t("dpi_hinweis"))
        self.anzahl_text.setText(t("anzahl"))
        self.start_text.setText(t("start"))

    def freischalten(self):
        """Sperrt die ungenutzten Stufen und hebt die Startstufe hervor."""
        self.start.setRange(1, self.anzahl.value())
        for i, (feld, nummer) in enumerate(zip(self.felder, self.nummern)):
            aktiv = i < self.anzahl.value()
            feld.setEnabled(aktiv)
            if not aktiv:
                farbe = TEXT_LEISE
            elif i + 1 == self.start.value():
                farbe = SILBER
            else:
                farbe = TEXT_GEDAEMPFT
            nummer.setStyleSheet(f"color: {farbe};")

    def werte(self):
        return [f.value() for f in self.felder[: self.anzahl.value()]]


class Sprachschalter(QWidget):
    """Zwei Flaggenknoepfe, von denen immer genau einer gedrueckt ist."""

    def __init__(self, sprache, gewechselt):
        super().__init__()
        self.knoepfe = {}
        aufbau = QHBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.setSpacing(6)
        for kennung, texte in TEXTE.items():
            knopf = QPushButton(texte["flagge"])
            knopf.setObjectName("flagge")
            knopf.setFont(schrift(EMOJI, 13))
            knopf.setCheckable(True)
            knopf.setChecked(kennung == sprache)
            knopf.setFixedSize(40, 26)
            knopf.setCursor(Qt.CursorShape.PointingHandCursor)
            knopf.clicked.connect(lambda _, k=kennung: gewechselt(k))
            self.knoepfe[kennung] = knopf
            aufbau.addWidget(knopf)

    def anzeigen(self, sprache):
        for kennung, knopf in self.knoepfe.items():
            knopf.setChecked(kennung == sprache)


class Fenster(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(600)

        global SPRACHE
        gespeichert, dpi_stufen, dpi_start, SPRACHE = self.laden()

        titel = QLabel("BURST PRO AIR")
        titel.setFont(schrift(SCHREIBMASCHINE, 17, sperrung=3.6))
        titel.setStyleSheet(f"color: {TEXT};")

        self.sprachschalter = Sprachschalter(SPRACHE, self.sprache_setzen)

        kopf = QHBoxLayout()
        kopf.addWidget(titel)
        kopf.addStretch()
        kopf.addWidget(self.sprachschalter, 0, Qt.AlignmentFlag.AlignBottom)

        self.licht = Statuslicht()
        self.zustandswort = QLabel()
        self.zustandswort.setFont(schrift(SCHREIBMASCHINE, 10, sperrung=2.0))
        self.hinweis = QLabel()
        self.hinweis.setFont(schrift(SANS, 10))
        self.hinweis.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")
        self.hinweis.setWordWrap(True)

        zustand = QHBoxLayout()
        zustand.setSpacing(6)
        zustand.addWidget(self.licht)
        zustand.addWidget(self.zustandswort)
        zustand.addStretch()

        self.zonen = [Zone(name, gespeichert[i]) for i, name in enumerate(t("zonen"))]
        self.maus = Maus(self.zonen, self.farbe_waehlen)
        for zone in self.zonen:
            zone.regler.valueChanged.connect(self.maus.update)

        self.beleuchtung_text = Abschnitt()
        self.beleuchtung_hinweis = QLabel()
        self.beleuchtung_hinweis.setFont(schrift(SANS, 9))
        self.beleuchtung_hinweis.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")
        self.beleuchtung_hinweis.setWordWrap(True)

        self.akku = Akku()

        regler = QVBoxLayout()
        regler.setSpacing(18)
        regler.addWidget(self.akku)
        regler.addStretch()
        for zone in self.zonen:
            regler.addWidget(zone)
        regler.addStretch()

        felder = QHBoxLayout()
        felder.setSpacing(12)
        felder.addWidget(self.maus)
        felder.addLayout(regler)

        beleuchtung = Panel()
        beleuchtung.setObjectName("panel")
        innen = QVBoxLayout(beleuchtung)
        innen.setContentsMargins(16, 13, 18, 12)
        innen.setSpacing(9)
        innen.addWidget(self.beleuchtung_text)
        innen.addWidget(self.beleuchtung_hinweis)
        innen.addLayout(felder)

        self.dpi = Dpi(dpi_stufen, dpi_start)

        self.knopf = QPushButton()
        self.knopf.setObjectName("primaer")
        self.knopf.setFont(schrift(SCHREIBMASCHINE, 11, sperrung=2.4))
        self.knopf.setFixedHeight(42)
        self.knopf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.knopf.clicked.connect(self.uebernehmen)

        self.meldung = QLabel(" ")
        self.meldung.setFont(schrift(SANS, 10))
        self.meldung.setStyleSheet(f"color: {TEXT_GEDAEMPFT};")
        self.meldung.setWordWrap(True)

        self.fuss = QLabel()
        self.fuss.setFont(schrift(SCHREIBMASCHINE, 8, sperrung=1.4))
        self.fuss.setWordWrap(True)
        self.fuss.setStyleSheet(f"color: {TEXT_LEISE};")

        aufbau = QVBoxLayout(self)
        aufbau.setContentsMargins(22, 20, 22, 18)
        aufbau.setSpacing(14)
        aufbau.addLayout(kopf)
        aufbau.addWidget(Haarlinie())
        aufbau.addLayout(zustand)
        aufbau.addWidget(self.hinweis)
        aufbau.addWidget(beleuchtung)
        aufbau.addWidget(self.dpi)
        aufbau.addWidget(self.knopf)
        aufbau.addWidget(self.meldung)
        aufbau.addWidget(Haarlinie())
        aufbau.addWidget(self.fuss)

        self.setStyleSheet(f"""
            QWidget {{ color: {TEXT}; }}
            QDialog {{ background: {GRUND}; }}
            QDialog QPushButton {{
                background: {FLAECHE_UNTEN}; color: {TEXT};
                border: 1px solid rgba(255,255,255,0.15); border-radius: 2px;
                padding: 4px 12px;
            }}
            QDialog QPushButton:hover {{ background: #23242a; }}
            QDialog QPushButton:disabled {{ color: {TEXT_LEISE}; }}
            QDialog QLineEdit {{
                background: rgba(0,0,0,0.45); color: {TEXT};
                border: 1px solid rgba(255,255,255,0.15); border-radius: 2px;
                padding: 2px 5px;
            }}
            QFrame#panel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {FLAECHE_OBEN}, stop:1 {FLAECHE_UNTEN});
                border: 1px solid {LINIE}; border-radius: 3px;
            }}
            QFrame#haarlinie {{ background: rgba(255,255,255,0.085); border: none; }}
            QPushButton#primaer {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #1d1e24, stop:1 #131418);
                color: {SILBER}; border: 1px solid rgba(212,218,226,0.45);
                border-radius: 2px;
            }}
            QPushButton#primaer:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #24252c, stop:1 #17181d);
                border-color: {SILBER};
            }}
            QPushButton#primaer:pressed {{ background: #0f1013; }}
            QPushButton#primaer:disabled {{
                background: rgba(255,255,255,0.015); color: {TEXT_LEISE};
                border-color: rgba(255,255,255,0.10);
            }}
            QSlider::groove:horizontal {{
                height: 2px; background: rgba(255,255,255,0.10);
            }}
            QSlider::sub-page:horizontal {{
                height: 2px; background: rgba(212,218,226,0.55);
            }}
            QSlider::handle:horizontal {{
                width: 3px; height: 13px; margin: -6px 0; background: {SILBER};
            }}
            QSlider::handle:horizontal:hover {{ background: #ffffff; }}
            QSpinBox {{
                background: rgba(0,0,0,0.45); color: {TEXT};
                border: 1px solid rgba(255,255,255,0.15); border-radius: 2px;
                padding: 3px 5px;
            }}
            QSpinBox:hover {{ border-color: rgba(255,255,255,0.28); }}
            QSpinBox:focus {{ border-color: {SILBER}; }}
            QSpinBox:disabled {{
                background: rgba(0,0,0,0.25); color: {TEXT_LEISE};
                border-color: {LINIE};
            }}
            QPushButton#flagge {{
                background: rgba(255,255,255,0.03); border: 1px solid {LINIE};
                border-radius: 2px;
            }}
            QPushButton#flagge:hover {{ background: rgba(255,255,255,0.08); }}
            QPushButton#flagge:checked {{ border-color: {SILBER}; }}
            QToolTip {{
                background: {FLAECHE_UNTEN}; color: {TEXT};
                border: 1px solid rgba(255,255,255,0.15); padding: 3px;
            }}
        """)

        self.beschriften()
        self.takt = QTimer(self)
        self.takt.timeout.connect(self.pruefen)
        self.takt.start(2000)

    def paintEvent(self, ereignis):
        maler = QPainter(self)
        flaeche = self.rect()
        vignette = QRadialGradient(QPointF(flaeche.center().x(), flaeche.height() * 0.3),
                                   flaeche.height() * 0.95)
        vignette.setColorAt(0.0, QColor("#141519"))
        vignette.setColorAt(1.0, QColor(GRUND))
        maler.fillRect(flaeche, vignette)
        maler.drawTiledPixmap(flaeche, korn())

    def farbe_waehlen(self, i):
        zone = self.zonen[i]
        gewaehlt = QColorDialog.getColor(zone.farbe, self, t("farbe_waehlen"))
        if gewaehlt.isValid():
            zone.faerben(gewaehlt)
            self.maus.update()

    def beschriften(self):
        """Setzt alle sichtbaren Texte in der gewaehlten Sprache."""
        self.setWindowTitle(t("titel"))
        for zone, name in zip(self.zonen, t("zonen")):
            zone.umbenennen(name)
        self.beleuchtung_text.beschriften(t("beleuchtung"))
        self.beleuchtung_hinweis.setText(t("beleuchtung_hinweis"))
        self.akku.beschriften()
        self.dpi.beschriften()
        self.knopf.setText(t("uebernehmen"))
        self.fuss.setText(t("fuss"))
        self.meldung.setText(" ")
        self.pruefen()

    def sprache_setzen(self, kennung):
        global SPRACHE
        SPRACHE = kennung
        self.sprachschalter.anzeigen(kennung)
        self.beschriften()
        self.sichern()

    def laden(self):
        try:
            with open(EINSTELLUNGEN) as fd:
                gespeichert = json.load(fd)
            zonen = [{**VORGABE[i], **gespeichert["zonen"][i]} for i in range(4)]
            stufen = [int(w) for w in gespeichert["dpi"]]
            start = int(gespeichert["dpi_start"])
            sprache = gespeichert["sprache"]
            if not 1 <= len(stufen) <= bpa_led.DPI_PLAETZE:
                raise ValueError("Stufenzahl ausserhalb des Bereichs")
            if not all(bpa_led.DPI_MIN <= w <= bpa_led.DPI_MAX for w in stufen):
                raise ValueError("DPI-Wert ausserhalb des Bereichs")
            if not 1 <= start <= len(stufen):
                raise ValueError("Startstufe ausserhalb des Bereichs")
            if sprache not in TEXTE:
                raise ValueError("Sprache unbekannt")
            return zonen, stufen, start, sprache
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            return list(VORGABE), list(bpa_led.DPI_VORGABE), 1, SPRACHE

    def sichern(self):
        os.makedirs(os.path.dirname(EINSTELLUNGEN), exist_ok=True)
        with open(EINSTELLUNGEN, "w") as fd:
            json.dump({"zonen": [z.zustand() for z in self.zonen],
                       "dpi": self.dpi.werte(),
                       "dpi_start": self.dpi.start.value(),
                       "sprache": SPRACHE}, fd, indent=2)

    def pruefen(self):
        gefunden = bpa_led.geraet_finden()
        modus = gefunden[1] if gefunden else None
        farbe, schluessel = {
            "kabel": (GRUEN, "kabel"),
            "funk": (NEUTRAL, "funk"),
            None: (ROT, "fehlt"),
        }[modus]
        self.licht.setzen(farbe)
        self.zustandswort.setText(t(schluessel))
        self.zustandswort.setStyleSheet(f"color: {farbe};")
        self.hinweis.setText(t(schluessel + "_hinweis"))
        self.knopf.setEnabled(modus == "kabel")

    def uebernehmen(self):
        werte = [z.werte() for z in self.zonen]
        try:
            pfad, _ = bpa_led.setzen([f for f, _ in werte], [h for _, h in werte],
                                     self.dpi.werte(), self.dpi.start.value())
        except (ValueError, RuntimeError, OSError) as fehler:
            self.meldung.setStyleSheet(f"color: {ROT};")
            self.meldung.setText(str(fehler))
            return
        self.sichern()
        self.meldung.setStyleSheet(f"color: {GRUEN};")
        self.meldung.setText(t("erfolg").format(pfad=pfad))


if __name__ == "__main__":
    anwendung = QApplication(sys.argv)
    anwendung.setFont(schrift(SANS, 10))
    fenster = Fenster()
    fenster.show()
    sys.exit(anwendung.exec())
