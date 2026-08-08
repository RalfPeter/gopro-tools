#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 07-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : prg_gopro2overlay.py
#  Version           : 2.0
#  Beschreibung      : Keine Beschreibung verfügbar.
#  Zeilen            : 212
#  Abhängigkeiten    : pathlib, sys
#  Eigene Frameworks : geo, gpmf, gpx, utils
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    main(params)                                         → Führt die Overlay-Erzeugung für GoPro Videos aus
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter61@email.de>
# ------------------------------------------------------------------------------

import sys
from pathlib import Path

from utils_core import TRENNER, AppLogger, fatal, CallbackTag as Tag, log_to_callback
from utils_filepath import PathUtils
from gpmf_const import SUFFIX_OVERLAY
from gpmf_meta_video import VideoFile, VideoFiles, NoVideoError
from gpmf_meta_gopro import GoProFile, NoGoProError
from gpmf_overlay import create_gopro_overlay
from prg_gopro2overlay_config import OverlayParameters


# ###########################################################################################
# ###########################################################################################
# ===========================================================================================
# MAIN part of gopro2overlay
# ===========================================================================================
# ###########################################################################################
# ###########################################################################################
# --------------------------------------------------------------------------------
def main(params: OverlayParameters) -> int | None:
    """Führt die Overlay-Erzeugung für GoPro Videos aus

    :param params: (OverlayParameters) Das zentral validierte Konfigurationsobjekt.
    :return: Exit-Code der Anwendung.
    :rtype: int
    """
    # -------------------------------------------------------------------------------------------
    # get all dirs and subdirs
    # -------------------------------------------------------------------------------------------
    alldirs = PathUtils.get_subdirectories(params.inputpaths, recursive=params.recursive)
    nn = len(alldirs)

    if nn <= 0:
        fatal(msg='Keine Verzeichnisse gefunden', exitcode=20)

    # layout Datei vorhanden?
    if not Path(params.layout_xml).exists():
        fatal(msg=f'Layout Datei {params.layout_xml} fehlt', exitcode=40)

    # -------------------------------------------------------------------------------------------
    # scan all files *.mp4, mov in the given paths
    # -------------------------------------------------------------------------------------------
    log_to_callback(Tag.STATUS)
    log_to_callback(Tag.STATUS, 'Alle Videos suchen und prüfen')
    log_to_callback(Tag.STATUS)

    for n, fpath in enumerate(alldirs, 1):
        fpath = Path(fpath)

        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, f'Pfad {n}/{nn}', f'Videos im Pfad [{str(fpath)}] suchen')

        # -------------------------------------------------------------------------------------------
        # are there any Video files in the list.
        # -------------------------------------------------------------------------------------------
        videofiles = VideoFiles(filepath=fpath)
        goprovideos = []
        nongoprovideos = []

        # -------------------------------------------------------------------------------------------
        # Schritt 0:    GoPro Videos ermitteln
        #               Nicht-GoPro Videos ermitteln
        # -------------------------------------------------------------------------------------------
        i = 0
        for file in videofiles.files:
            i += 1
            log_to_callback(Tag.STATUS, TRENNER)
            log_to_callback(Tag.STATUS, f'Video {i}/{len(videofiles.files)}', f'{file.name} wird überprüft')
            # - Metadaten aus Video ------------------------------------------------------------------
            log_to_callback(Tag.STATUS, f'Metadaten', f'Metadaten aus Video {file.name} lesen')
            try:
                GoProFile(file, verbose=params.verbose, use_geocities=False)
            except NoGoProError as e:
                if params.verbose:
                    log_to_callback(Tag.STATUS, 'Datei', e.message)
                nongoprovideos.append(file)
                continue
            except NoVideoError as e:
                log_to_callback(Tag.ERR, 'Datei', e.message)
                continue
            else:
                goprovideos.append(file)

        # ###########################################################################################
        # GoPro Videos verarbeiten
        #
        # ###########################################################################################
        ii = len(goprovideos)
        i = 0

        if ii > 0:
            log_to_callback(Tag.STATUS)
            log_to_callback(Tag.STATUS, f'Alle {ii} GoPro Videos bearbeiten')
            log_to_callback(Tag.STATUS)

        for file in goprovideos:
            i += 1
            log_to_callback(Tag.STATUS, TRENNER)
            log_to_callback(Tag.STATUS, f'GoPro Video {i}/{ii}', f'{file.name} wird verarbeitet')
            # -------------------------------------------------------------------------------------------
            # Schritt 0: benötigte Variablen ermitteln
            #            Kamera Modell ermitteln
            # -------------------------------------------------------------------------------------------
            # - Metadaten aus Video ------------------------------------------------------------------
            try:
                if file.exists():
                    gopro_file = GoProFile(file, verbose=params.verbose,)
                else:
                    continue
            except NoVideoError as e:
                log_to_callback(Tag.STATUS, 'Datei', e.message)
                continue
            except NoGoProError as e:
                log_to_callback(Tag.STATUS, 'Datei', e.message)
                continue
            else:
                try:
                    # -------------------------------------------------------------------------------------------
                    # Overlay erzeugen, Video rendern
                    # -------------------------------------------------------------------------------------------
                    log_to_callback(Tag.STATUS, f'Erzeuge Overlay', f'Overlay aus GoPro Video {gopro_file.name} erstellen ...')

                    input_file = file
                    output_file = file.with_suffix(SUFFIX_OVERLAY)

                    if params.verbose:
                        log_to_callback(Tag.STATUS, f'input_file = {input_file}')
                        log_to_callback(Tag.STATUS, f'output_file = {output_file}')
                        log_to_callback(Tag.STATUS, f'layout_file = {params.layout_xml}')
                        log_to_callback(Tag.STATUS, f'font = {params.font}')

                    log_file = input_file.with_suffix(".overlay.txt")
                    log_to_callback(Tag.STATUS, '=')
                    create_gopro_overlay(
                        input_file=input_file,
                        output_file=output_file,
                        layout_file=params.layout_xml,
                        profile_str=params.profile,
                        font=params.font,
                        log_file=log_file,
                        verbose=params.verbose,
                    )
                    log_to_callback(Tag.STATUS, '=')

                except TypeError:
                    continue

        # ###########################################################################################
        # Nicht-GoPro Videos verarbeiten
        #
        # ###########################################################################################
        ii = len(nongoprovideos)
        i = 0

        if ii > 0:
            log_to_callback(Tag.STATUS)
            log_to_callback(Tag.STATUS, f'Alle {ii} anderen Videos bearbeiten')
            log_to_callback(Tag.STATUS)

        for file in nongoprovideos:
            i += 1
            log_to_callback(Tag.STATUS, TRENNER)
            log_to_callback(Tag.STATUS, f'Nicht-GoPro Video {i}/{ii}', f'{file.name} wird verarbeitet')
            # - Metadaten aus Video ------------------------------------------------------------------

            try:
                if file.exists():
                    video_file = VideoFile(file, verbose=params.verbose)
                else:
                    continue
            except NoVideoError as e:
                log_to_callback(Tag.ERR, 'Datei', e.message)
                continue

            else:
                try:
                    # -------------------------------------------------------------------------------------------
                    # Overlay erzeugen, Video rendern
                    # -------------------------------------------------------------------------------------------
                    log_to_callback(Tag.STATUS, f'Erzeuge Overlay', f'Overlay aus Video {video_file.name} mithilfe GPX Datei erstellen ... demnächst')
                    # overlay = create_overlay(video_file, geonames, geocountries, arg_verbose)

                except TypeError:
                    continue

        log_to_callback(Tag.STATUS)

    return 0


# ==========================================================================
# ==========================================================================
if __name__ == "__main__":
    try:
        # 1. Optionale YAML-Konfiguration laden (Konfigurations-Datei-Priorität: niedrig)
        appp: OverlayParameters = OverlayParameters()
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
