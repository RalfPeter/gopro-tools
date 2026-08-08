#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 04-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/tracktraffic.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Program : prg_desc2gpx.py (main - GoPro Videos and Telemetry Export)
#  Version : 1.0
# ------------------------------------------------------------------------------
#  Klassen:
#    keine
#  Public Methods:
#     main(params)                        → Führt die Beschreibungs-Generierung und das Mapping für GPX-Dateien aus.
# ------------------------------------------------------------------------------
#  Benutzte eigene Framework:
#    geo, gpmf, gpx, utils
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter61@email.de>
# ------------------------------------------------------------------------------

import sys
from pathlib import Path

from utils_core import AppLogger, TRENNER, fatal, CallbackTag as Tag, log_to_callback
from utils_filepath import PathUtils
from gpmf_gpx import GGPXManager
import gpmf_geo as geoinfo
from prg_gopro2file_config import GoProParameters
from prg_gopro2file_map import GGPXMapProcessor


# --------------------------------------------------------------------------------
def main(params: GoProParameters) -> int | None:
    """Führt die Beschreibungs-Generierung und das Mapping für GPX-Dateien aus.

    :param params: (AppParameters) Das zentral validierte Konfigurationsobjekt.
    :return: Exit-Code der Anwendung.
    :rtype: int
    """
    geoinfo.DEFAULT_GEONAMES_FILES = geoinfo.GEONAMES_DEFAULT
    geoinfo.DEFAULT_GEONAMES_USE = True

    inputpaths = params.inputpaths

    # Verzeichnis-Struktur ermitteln
    alldirs = PathUtils.get_subdirectories(inputpaths, recursive=params.recursive)
    nn = len(alldirs)

    if nn <= 0:
        fatal(msg='Keine Verzeichnisse gefunden', exitcode=20)

    log_to_callback(Tag.STATUS)
    log_to_callback(Tag.STATUS, 'Alle GPX Dateien suchen und prüfen')
    log_to_callback(Tag.STATUS)

    for n, fpath in enumerate(alldirs, 1):
        fpath = Path(fpath)

        # log path
        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, f'Pfad {n}/{nn}', f'GPX im Pfad [{str(fpath)}] ergänzen')
        gpx_manager = GGPXManager(path=fpath, load_on_init=False, diff_time=appp.diff_time, diff_dist=appp.diff_dist, verbose=params.verbose)
        gpx_manager.add_description_to_gpxfiles()

        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, 'Alle GPXmaps / GPXhtml aus GPX Dateien erzeugen')
        mapprocessor = GGPXMapProcessor(path=fpath, params=params)

        if params.generatemap:
            mapprocessor.process_gpx_jpeg()

        if params.generatehtml:
            mapprocessor.process_gpx_html()

        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, 'GPX zusammensetzen', TRENNER)
        # find all gpx files and add description to all points
        log_to_callback(Tag.STATUS, 'GPX zusammensetzen', f'Im Ordner {str(fpath)}: GPX-Dateien zu einer einzigen zusammensetzen...')
        # gpx_gopro.merge_overlapping_gpx_files_2(gpx_path=fpath)
        gpx_manager.merge_gpx_files(gpx_path=fpath, gpx_pattern='*FILE*.gpx')

    return 0


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
