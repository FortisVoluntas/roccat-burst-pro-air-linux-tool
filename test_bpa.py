#!/usr/bin/python3
# Copyright (C) 2026 FortisVoluntas (https://github.com/FortisVoluntas)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prueft Blockaufbau, DPI-Grenzen, Sprachwechsel und Mausansicht.

Alles ohne die Maus: die beiden Bloecke werden gegen den Swarm-Mitschnitt
gestellt, die Oberflaeche laeuft ohne Bildschirm.
"""
import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import bpa_led

BELEUCHTUNG_MITSCHNITT = ("0000030106540f0000"
                          "0100000000" "02ffffffff" "03ffffffff" "04ffffffff"
                          "0164ffffffe615" + "00" * 12)
DPI_MITSCHNITT = bytes.fromhex("19063f010606" "0702" "2003c409ea0b")


def test_beleuchtungsblock():
    block = bpa_led.block_bauen([(0, 0, 0), (255, 255, 255), (255, 255, 255), (255, 255, 255)],
                                [0, 255, 255, 255])
    assert block.hex() == BELEUCHTUNG_MITSCHNITT


def test_dpi_block():
    block = bpa_led.dpi_block_bauen(bpa_led.DPI_VORGABE, 3)
    assert len(block) == 26
    assert block[:8] == DPI_MITSCHNITT[:8]
    assert block[8:14] == DPI_MITSCHNITT[8:]


@pytest.mark.parametrize("anzahl, maske", [(1, 1), (3, 7), (5, 31), (6, 63)])
def test_stufenmaske_ist_thermometer(anzahl, maske):
    assert bpa_led.dpi_block_bauen([800] * anzahl)[6] == maske


@pytest.mark.parametrize("start, byte", [(1, 0), (2, 1), (3, 2)])
def test_startstufe_zaehlt_ab_null(start, byte):
    assert bpa_led.dpi_block_bauen([800, 2500, 3050], start)[7] == byte


@pytest.mark.parametrize("stufen, start", [
    ([], 1),
    ([800] * 7, 1),
    ([10], 1),
    ([30000], 1),
    ([800, 2500], 3),
    ([800, 2500], 0),
])
def test_dpi_grenzfaelle_werden_abgewiesen(stufen, start):
    with pytest.raises(ValueError):
        bpa_led.dpi_block_bauen(stufen, start)


@pytest.fixture(scope="session")
def anwendung():
    from PyQt6.QtWidgets import QApplication
    return QApplication([])


@pytest.fixture
def fenster(anwendung, tmp_path, monkeypatch):
    import bpa_gui
    monkeypatch.setattr(bpa_gui, "EINSTELLUNGEN", str(tmp_path / "zonen.json"))
    monkeypatch.setattr(bpa_gui, "SPRACHE", "de")
    # Die Akkuanzeige liest beim Bauen sofort; ohne Ersatz griffe der Test auf die
    # echte Maus zu, und ohne sie liefe er in einen Fehler.
    monkeypatch.setattr(bpa_led, "akkustand", lambda: (90, 2854))
    return bpa_gui.Fenster()


def test_sprachwechsel_aendert_alle_texte(fenster):
    vorher = (fenster.windowTitle(), fenster.knopf.text(), fenster.zonen[0].beschriftung.text())
    fenster.sprache_setzen("en")
    nachher = (fenster.windowTitle(), fenster.knopf.text(), fenster.zonen[0].beschriftung.text())
    assert all(a != b for a, b in zip(vorher, nachher))


def test_sprachwechsel_wird_sofort_gespeichert(fenster):
    import bpa_gui
    fenster.sprache_setzen("en")
    assert json.load(open(bpa_gui.EINSTELLUNGEN))["sprache"] == "en"


def test_farbfelder_treffen_ihre_zone(fenster):
    from PyQt6.QtCore import QPointF
    maus = fenster.maus
    versatz = QPointF(maus.RAHMEN, maus.RAHMEN)
    treffer = [maus._treffer(maus._feldrechteck(i).center() + versatz) for i in range(4)]
    assert treffer == [0, 1, 2, 3]
    assert maus._treffer(QPointF(5, 5)) is None


def test_zonen_ueberlappen_nicht(fenster):
    flaechen = fenster.maus._zonenpfade()
    assert not any(p.isEmpty() for p in flaechen)
    paare = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    assert not any(not flaechen[i].intersected(flaechen[j]).isEmpty() for i, j in paare)


@pytest.mark.parametrize("prozent, farbe", [
    (100, "gruen"), (75, "gruen"), (74, "gelb"), (50, "gelb"),
    (49, "orange"), (25, "orange"), (24, "rot"), (0, "rot"),
])
def test_akkufarbe_springt_bei_25_prozent(prozent, farbe):
    import bpa_gui
    erwartet = {"gruen": bpa_gui.GRUEN, "gelb": bpa_gui.GELB,
                "orange": bpa_gui.ORANGE, "rot": bpa_gui.ROT}[farbe]
    assert bpa_gui.akkufarbe(prozent) == erwartet


def test_akkuanzeige_zeigt_wert_und_spannung(fenster):
    fenster.akku.anzeigen((90, 2854))
    assert fenster.akku.wert.text() == "90 %"
    assert fenster.akku.spannung.text() == "2854 mV"


def test_akkuanzeige_ohne_maus_bleibt_stumm(fenster):
    fenster.akku.anzeigen(None)
    assert fenster.akku.wert.text() == "--"
    assert fenster.akku.spannung.text() == " "
