#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : prg_gpx2map.py
#  Version           : 2.0
#  Beschreibung      : Führt die Beschreibungs-Generierung und das Mapping für GPX-Dateien aus.
#  Zeilen            : 84
#  Abhängigkeiten    : pathlib, sys
#  Eigene Frameworks : rpg_geo, rpg_gpmf, rpg_gpx, rpg_utils
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    main(GoProParameters)                                → Führt die Beschreibungs-Generierung und das Mapping für GPX-Dateien aus.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

import sys
from pathlib import Path

from rpg_utils import TRENNER, AppLogger, fatal, CallbackTag as Tag, log_to_callback, PathUtils
from rpg_gpmf import gpmf_geo as geoinfo

from prg_gopro2file_config import GoProParameters
from prg_gopro2file_map import GGPXMapProcessor


# --------------------------------------------------------------------------------
def main(params: GoProParameters) -> int | None:
    """Führt die Beschreibungs-Generierung und das Mapping für GPX-Dateien aus.

    :param params: (AppParameters) Das zentral validierte Konfigurationsobjekt.
    :return: Exit-Code der Anwendung.
    :rtype: int
    """
    # -------------------------------------------------------------------------------------------
    # GeoNames initialisieren (Daten laden)
    # -------------------------------------------------------------------------------------------
    geoinfo.DEFAULT_GEONAMES_FILES = geoinfo.GEONAMES_DEFAULT
    geoinfo.DEFAULT_GEONAMES_USE = True

    inputpaths = params.inputpaths

    # -------------------------------------------------------------------------------------------
    # get all dirs and subdirs
    # -------------------------------------------------------------------------------------------
    alldirs = PathUtils.get_subdirectories(inputpaths, recursive=params.recursive)
    nn = len(alldirs)

    if nn <= 0:
        fatal(msg='Keine Verzeichnisse gefunden', exitcode=20)

    # scan all files *.gpx in the given paths
    log_to_callback(Tag.STATUS)
    log_to_callback(Tag.STATUS, 'Alle GPX Dateien suchen und prüfen')
    log_to_callback(Tag.STATUS)

    # -------------------------------------------------------------------------------------------
    # set some variables and initialize the logger, ffmpeg, geonames and geocountries
    # -------------------------------------------------------------------------------------------
    for n, fpath in enumerate(alldirs, 1):
        fpath = Path(fpath)

        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, f'Pfad {n}/{nn}', f'GPX im Pfad [{str(fpath)}] suchen')

        # alle gpx Dateien verarbeiten
        # whole map with all tracks / routes
        mapprocessor = GGPXMapProcessor(path=fpath, params=params)
        mapprocessor.process_gpx_jpeg()

        if params.generatehtml:
            mapprocessor.process_gpx_html()

    return 0


# ==========================================================================
# ==========================================================================
# ==========================================================================
# Execution Entry Point
# ==========================================================================
if __name__ == "__main__":
    try:
        # 1. Optionale YAML-Konfiguration laden (Konfigurations-Datei-Priorität: niedrig)
        appp: GoProParameters = GoProParameters()
        appp.load_from_yaml()

        # 2. CLI-Argumente parsen & Werte überschreiben (Kommandozeilen-Priorität: hoch)
        # Die Methode aktualisiert die Instanz 'appp' intern und gibt sie zurück
        appp.parse_args()

        # 3. Hauptprogramm ausführen
        logpath = PathUtils.get_script_dir()
        my_logger = AppLogger.create(logfile_path=logpath, use_console=True)
        exit_code = main(params=appp)
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
