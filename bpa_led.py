#!/usr/bin/python3
# Copyright (C) 2026 FortisVoluntas (https://github.com/FortisVoluntas)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Beleuchtung der ROCCAT Burst Pro Air setzen.

Das Protokoll stammt aus einem USB-Mitschnitt von ROCCAT Swarm 1.9481:
HID-Feature-Report 0x06 an Interface 2, je 30 Byte, nach jedem Kommando eine
Statusabfrage. Geschrieben wird das im Geraet gespeicherte Profil, die Farben
bleiben deshalb auch im Funkbetrieb erhalten.

Der Dongle (1e7d:2ca6) nimmt diese Pakete nicht an - zum Setzen muss die Maus
am Kabel haengen (1e7d:2cab).
"""
import fcntl
import os
import sys
import time

KENNUNGEN = {"0003:00001E7D:00002CAB": "kabel", "0003:00001E7D:00002CA6": "funk"}
PAKETLAENGE = 30

SETFEATURE = (3 << 30) | (PAKETLAENGE << 16) | (ord("H") << 8) | 0x06
GETFEATURE = (3 << 30) | (PAKETLAENGE << 16) | (ord("H") << 8) | 0x07

ZONEN = ("Mausrad", "Linke Taste", "Rechte Taste", "Handablage")

# Beleuchtungsblock, wie Swarm ihn schreibt (48 Byte). Byte 9..28 sind die vier
# Zoneneintraege (Zone, Helligkeit, R, G, B), Byte 34/35 die Pruefsumme.
VORLAGE = bytes.fromhex(
    "0000030106540f0000"
    + "0100000000" + "02ffffffff" + "03ffffffff" + "04ffffffff"
    + "0164ffffff" + "0000" + "00" * 12
)
PRUEFSUMME_START = 0x0619

# DPI-Block (26 Byte): Kopf, Stufenmaske, aktive Stufe, dann neun 16-Bit-Werte
# little-endian - sechs Stufenplaetze und drei feste Werte aus dem Mitschnitt.
DPI_KOPF = bytes.fromhex("19063f010606")
DPI_NACHSPANN = (800, 1200, 1600)
DPI_PLAETZE = 6
DPI_VORGABE = (800, 2500, 3050)
# Vorsichtsgrenze des Programms - die Grenzen der Maus sind nicht ausgelotet.
DPI_MIN, DPI_MAX, DPI_SCHRITT = 50, 19000, 50


def geraet_finden():
    """Gibt (hidraw-Pfad, 'kabel'|'funk') zurueck oder None.

    Steckt der Dongle waehrend des Kabelbetriebs weiter, meldet sich die Maus
    zweimal - dann hat das Kabel Vorrang.
    """
    treffer = {}
    for eintrag in sorted(os.listdir("/sys/class/hidraw")):
        try:
            with open(f"/sys/class/hidraw/{eintrag}/device/uevent") as fd:
                inhalt = fd.read()
        except OSError:
            continue
        if "/input2" not in inhalt:
            continue
        for kennung, modus in KENNUNGEN.items():
            if kennung in inhalt:
                treffer.setdefault(modus, f"/dev/{eintrag}")
    for modus in ("kabel", "funk"):
        if modus in treffer:
            return treffer[modus], modus
    return None


def dpi_block_bauen(stufen, start=1):
    """Baut den DPI-Block aus 1 bis 6 Stufen. Die Maske ist ein Thermometer-Code.

    `start` ist die Stufe, auf der die Maus steht - auch nach dem Aufwachen, denn
    sie laedt dabei ihr Profil neu. Gezaehlt wie am Geraet, ab 1.
    """
    if not 1 <= len(stufen) <= DPI_PLAETZE:
        raise ValueError(f"1 bis {DPI_PLAETZE} DPI-Stufen nötig, nicht {len(stufen)}")
    if not 1 <= start <= len(stufen):
        raise ValueError(f"Startstufe außerhalb 1-{len(stufen)}: {start}")
    for wert in stufen:
        if not DPI_MIN <= wert <= DPI_MAX:
            raise ValueError(f"DPI außerhalb {DPI_MIN}-{DPI_MAX}: {wert}")
    block = bytearray(DPI_KOPF)
    block += bytes(((1 << len(stufen)) - 1, start - 1))
    for wert in list(stufen) + [stufen[-1]] * (DPI_PLAETZE - len(stufen)) + list(DPI_NACHSPANN):
        block += wert.to_bytes(2, "little")
    return bytes(block)


def block_bauen(farben, helligkeiten):
    block = bytearray(VORLAGE)
    for i, ((r, g, b), hell) in enumerate(zip(farben, helligkeiten)):
        block[9 + 5 * i : 14 + 5 * i] = bytes((i + 1, hell, r, g, b))
    block[34:36] = b"\x00\x00"
    block[34:36] = ((sum(block) + PRUEFSUMME_START) & 0xFFFF).to_bytes(2, "little")
    return bytes(block)


def _kommando(fd, rumpf):
    buf = bytearray(PAKETLAENGE)
    buf[0] = 0x06
    buf[1 : 1 + len(rumpf)] = rumpf
    fcntl.ioctl(fd, SETFEATURE, bytes(buf))
    time.sleep(0.08)
    _status(fd)


def _status(fd):
    buf = bytearray(PAKETLAENGE)
    buf[0:5] = bytes((0x06, 0x00, 0x44, 0x07, 0x00))
    fcntl.ioctl(fd, SETFEATURE, bytes(buf))
    time.sleep(0.08)
    antwort = bytearray(PAKETLAENGE)
    antwort[0] = 0x06
    fcntl.ioctl(fd, GETFEATURE, antwort)
    return bytes(antwort)


def setzen(farben, helligkeiten, dpi_stufen, dpi_start=1):
    """Schreibt Zonen und DPI-Stufen ins Profil der Maus. Verlangt Kabelbetrieb.

    Die DPI-Stufen sind Pflicht: die Maus nimmt die DPI-Seite nur zusammen mit den
    Beleuchtungsseiten an, jedes Setzen der Farben schreibt sie also mit.
    """
    gefunden = geraet_finden()
    if gefunden is None:
        raise RuntimeError("Burst Pro Air nicht gefunden.")
    pfad, modus = gefunden
    if modus != "kabel":
        raise RuntimeError("Nur im Kabelbetrieb möglich, der Dongle nimmt die Pakete nicht an.")

    block = block_bauen(farben, helligkeiten)
    dpi = dpi_block_bauen(dpi_stufen, dpi_start)
    with open(pfad, "wb") as datei:
        fd = datei.fileno()
        _kommando(fd, bytes((0x00, 0x46, 0x06, 0x02, 0x00, 0x01)))
        _kommando(fd, bytes((0x00, 0x46, 0x06)) + dpi)
        _kommando(fd, bytes((0x00, 0x46, 0x06, 0x02, 0x01, 0x01)))
        _kommando(fd, bytes((0x00, 0x46, 0x06, 0x19, 0x80, 0x0C)) + block[:23])
        _kommando(fd, bytes((0x00, 0x46, 0x06, 0x02, 0x02, 0x01)))
        _kommando(fd, bytes((0x00, 0x46, 0x06, 0x0D)) + block[23:48])
        _kommando(fd, bytes((0x00, 0x4E, 0x06, 0x04, 0x01, 0x00, 0x00, 0xFF)))
    return pfad, block


def zone_lesen(text):
    """'RRGGBB' oder 'RRGGBB:helligkeit' (0-100) -> ((r, g, b), helligkeit)."""
    farbe, _, prozent = text.lstrip("#").partition(":")
    wert = int(farbe, 16)
    hell = int(prozent) if prozent else 100
    if not 0 <= hell <= 100:
        raise SystemExit(f"Helligkeit außerhalb 0-100: {hell}")
    return ((wert >> 16) & 0xFF, (wert >> 8) & 0xFF, wert & 0xFF), round(hell * 255 / 100)


if __name__ == "__main__":
    if not 5 <= len(sys.argv) <= 6:
        raise SystemExit(
            f"Aufruf: {os.path.basename(sys.argv[0])} <Mausrad> <links> <rechts> <Handablage> [DPI-Stufen]\n"
            "  je Zone:    RRGGBB oder RRGGBB:helligkeit (0-100, Vorgabe 100)\n"
            f"  DPI-Stufen: 1 bis {DPI_PLAETZE} Werte mit Komma, dahinter optional"
            " :Startstufe, z. B. 800,2500,3050:3\n"
            f"              (Vorgabe {','.join(str(w) for w in DPI_VORGABE)}, Startstufe 1)"
        )
    werte = [zone_lesen(a) for a in sys.argv[1:5]]
    stufen, start = DPI_VORGABE, 1
    if len(sys.argv) == 6:
        liste, _, gewaehlt = sys.argv[5].partition(":")
        try:
            stufen = [int(w) for w in liste.split(",")]
            start = int(gewaehlt) if gewaehlt else 1
        except ValueError:
            raise SystemExit(f"DPI-Stufen nicht lesbar: {sys.argv[5]}")
    try:
        pfad, block = setzen([f for f, _ in werte], [h for _, h in werte], stufen, start)
    except (ValueError, RuntimeError) as fehler:
        raise SystemExit(str(fehler))
    print(f"gesendet an {pfad}")
    for i, name in enumerate(ZONEN):
        print(f"  {name:13s} {block[9 + 5 * i:14 + 5 * i].hex(' ')}")
    print(f"  DPI-Stufen    {', '.join(str(w) for w in stufen)} (Start: Stufe {start})")
