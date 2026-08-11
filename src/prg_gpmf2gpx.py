#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : prg_gpmf2gpx.py
#  Version           : 3.0
#  Beschreibung      : Generierung einer GPX aus gpmf binary Dateien.
#  Zeilen            : 97
#  Abhängigkeiten    : pathlib, sys
#  Eigene Frameworks : rpg_geo, rpg_gpmf, rpg_gpx, rpg_utils
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    main(GoProParameters)                                → Generierung einer GPX aus gpmf binary Dateien.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

import sys
from pathlib import Path

from rpg_utils import TRENNER, AppLogger, fatal, CallbackTag as Tag, log_to_callback, PathUtils
from rpg_gpmf import GpmfFiles, GpmfFile, ExtractionMethod, NoGpmfError, GoProFileWrite, gpmf_geo as geoinfo

from prg_gopro2file_map import GGPXMapProcessor
from prg_gopro2file_config import GoProParameters


# --------------------------------------------------------------------------------
def main(params: GoProParameters) -> int | None:
    """Generierung einer GPX aus gpmf binary Dateien.

    :param params: (GoProParameters) Das zentral validierte Konfigurationsobjekt.
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

    # scan all files *.gpmf in the given paths
    log_to_callback(Tag.STATUS)
    log_to_callback(Tag.STATUS, 'Alle GPMF Dateien suchen und prüfen')
    log_to_callback(Tag.STATUS)

    for n, fpath in enumerate(alldirs, 1):
        fpath = Path(fpath)

        # log path
        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, f'Pfad {n}/{nn}', f'GPMF im Pfad [{str(fpath)}] suchen')

        gpmf_files = GpmfFiles(fpath)
        # alle gpmf Dateien verarbeiten
        for f in gpmf_files.files:
            try:
                log_to_callback(Tag.STATUS, 'Verarbeite:', f)
                gpmf_file = GpmfFile(file=f, verbose=params.verbose)
                log_to_callback(Tag.STATUS, f'Metadaten', f'Metadaten aus GPMF Datei {gpmf_file.name} lesen')
                gpmf_file.get_raw_telemetry(method=ExtractionMethod.FILE, clean=False)

                log_to_callback(Tag.STATUS, f'Schreibe Punkte', f'Schreibe GPX Punkte in temporäre Datei ...')
                gopro_writer = GoProFileWrite(filepath=f, verbose=params.verbose)
                outfile = gopro_writer.write_gpx_temp(points=gpmf_file.gps_items)

                # whole map with all tracks / routes
                # generate jpg and html
                mapprocessor = GGPXMapProcessor(path=outfile, params=params)
                mapprocessor.process_gpx_jpeg()
                if params.generatehtml:
                    mapprocessor.process_gpx_html()

            except ValueError as e:
                log_to_callback(Tag.ERR, 'Datei', str(e))
                continue
            except NoGpmfError as e:
                log_to_callback(Tag.ERR, 'Datei', e.message)
                continue


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
