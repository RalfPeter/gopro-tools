#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : prg_gopro2file.py
#  Version           : 2.0
#  Beschreibung      : Führt den Export und die Telemetrie-Extraktion für alle Verzeichnisse aus.
#  Zeilen            : 570
#  Abhängigkeiten    : cProfile, collections, fnmatch, io, pathlib, pstats, sys
#  Eigene Frameworks : rpg_geo, rpg_gpmf, rpg_gpx, rpg_utils
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    main(GoProParameters, Profile)                       → Führt den Export und die Telemetrie-Extraktion für alle Verzeichnisse aus.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

import sys
from cProfile import Profile
import pstats
from io import StringIO
from collections import defaultdict
from pathlib import Path
import fnmatch

from rpg_utils import AppLogger, TRENNER, fatal, CallbackTag as Tag, log_to_callback, ProgressEvent, DateTimeUtils, ISO_FORMAT_TZ
from rpg_utils import PathUtils, StringUtils as Str

from rpg_gpmf import GOPRO_USER_09, GOPRO_USER_10, TRASH_EXTENSIONS
from rpg_gpmf import VideoFile, VideoFiles, NoVideoError, NoMetaError, NoSRTError, SRTFiles, SRTExtractor, GOPRO_08, GOPRO_09
from rpg_gpmf import GoProFile, NoGoProError, GpmfFiles, GpmfFile, NoGpmfError, ExtractionMethod, GoProRecordingGroups, GoProRenamer
from rpg_gpmf import EExiv2, GGPXManager, GGPXJpegManager, GoProFileWrite, gpmf_geo as geoinfo
from rpg_gpx import GeoPointTime

from prg_gopro2file_map import GGPXMapProcessor
from prg_gopro2file_config import GoProParameters
from prg_gopro2file_utils import rename_videofile, print_video_metadata, write_video_datafiles


# ###########################################################################################
# ###########################################################################################
# ===========================================================================================
# MAIN part of gopro_export
# ===========================================================================================
# ###########################################################################################
# ###########################################################################################
# -------------------------------------------------------------------------------------------
def main(params: GoProParameters, profiler: Profile | None = None) -> int | None:
    """Führt den Export und die Telemetrie-Extraktion für alle Verzeichnisse aus.
    
    :param params: (GoProParameters) Das zentral validierte Konfigurationsobjekt.
    :param profiler: (Profile | None) Performanceuntersuchung
    :return: (int | None) Beschreibung
    """
    # Lokale Pfadzuweisung ist durch die präzise __main__-Vorbereitung garantiert
    inputpaths = params.inputpaths
    # inputfiles = params.inputfiles

    # ----------------------------------------------------------------------
    # ZENTRALE KONFIGURATION für GeoNames HIER VORNEHMEN
    # ----------------------------------------------------------------------
    # Sie müssen nur sicherstellen, dass die Zuweisung VOR JEDEM AUFRUF erfolgt.
    # Wir setzen den globalen Standardwert für alle zukünftigen get_geoname_service() Aufrufe.
    # -------------------------------------------------------------------------------------------
    geoinfo.DEFAULT_GEONAMES_FILES = geoinfo.GEONAMES_DEFAULT
    geoinfo.DEFAULT_GEOALTERNATENAMES_FILES = geoinfo.GEOALTERNATENAMES_DEFAULT

    # -------------------------------------------------------------------------------------------
    # Prüfen der essentiellen Parameter
    # -------------------------------------------------------------------------------------------
    if not PathUtils.validate_input_directories(inputpaths):
        fatal(msg=f'Ungültige Verzeichnisse in [{Str.safe_str(inputpaths)}] gefunden', exitcode=10)

    alldirs = PathUtils.get_subdirectories(inputpaths, recursive=params.recursive)
    nn = len(alldirs)

    if nn <= 0:
        fatal(msg='Keine Verzeichnisse gefunden', exitcode=20)

    # -------------------------------------------------------------------------------------------
    # laden der Geonames Daten provozieren
    # -------------------------------------------------------------------------------------------
    log_to_callback(Tag.STATUS)
    log_to_callback(Tag.STATUS, 'Daten initialisieren für Geodaten ... (Geduld)')
    log_to_callback(Tag.STATUS)
    # Bestimme über die zentrale Klasse, ob ein Update-Lauf fällig ist
    is_offline = not params.check_geonames_update(force_update=params.geonamesupdate)
    # alle singletons initialisieren
    geoinfo.initialize_all_geo_services(verbose=params.verbose, offline_mode=is_offline, profiler=profiler)
    # Wenn ein Update stattgefunden hat (also nicht offline gearbeitet wurde), Zeitstempel sichern
    if not is_offline:
        params.update_geonames_timestamp()
        params.save_to_yaml()

    # -------------------------------------------------------------------------------------------
    # scan all files *.mp4, mov in the given paths
    # -------------------------------------------------------------------------------------------
    log_to_callback(Tag.STATUS)
    log_to_callback(Tag.STATUS, 'Alle Videos suchen und prüfen')
    log_to_callback(Tag.STATUS)

    pattern_groups: GoProRecordingGroups = defaultdict(list)
    for n, fpath in enumerate(alldirs, 1):
        fpath = Path(fpath)

        log_to_callback(Tag.STATUS, TRENNER)
        log_to_callback(Tag.STATUS, f'Pfad {n}/{nn}', f'Videos im Pfad [{str(fpath)}] suchen')

        if not params.geoonly:
            # -------------------------------------------------------------------------------------------
            # are there any Video files in the list.
            # -------------------------------------------------------------------------------------------
            videofiles = VideoFiles(filepath=fpath)
            gpmffiles = GpmfFiles(filepath=fpath)
            srtfiles = SRTFiles(filepath=fpath)
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
                    GoProFile(file, verbose=params.verbose)
                except NoGoProError as e:
                    if params.verbose:
                        log_to_callback(Tag.STATUS, 'Datei', e.message)
                    if not params.goproonly:
                        nongoprovideos.append(file)
                    continue
                except NoVideoError as e:
                    log_to_callback(Tag.STATUS, 'Datei', e.message)
                    continue
                else:
                    goprovideos.append(file)

            # ###########################################################################################
            # GoPro Videos verarbeiten
            #
            # ###########################################################################################
            ii = len(goprovideos)
            i = 0

            # Noch VOR der Schleife die Progressbar vorbereiten (selbst bei 0 Videos!)
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(ii))

            if ii > 0:
                log_to_callback(Tag.STATUS, )
                log_to_callback(Tag.STATUS, f'Alle {ii} GoPro Videos bearbeiten')
                log_to_callback(Tag.STATUS, )

            for file in goprovideos:
                i += 1
                log_to_callback(Tag.STATUS, TRENNER)
                log_to_callback(Tag.STATUS, f'GoPro Video {i}/{ii}', f'{file.name} wird verarbeitet')
                # -> Fortschritt an die GUI / den Logger melden:
                log_to_callback(Tag.PROGRESS, ProgressEvent.update(i, ii))
                # -------------------------------------------------------------------------------------------
                # Schritt 0:    benötigte Variablen ermitteln
                #               Kamera Modell ermitteln
                # -------------------------------------------------------------------------------------------
                # - Metadaten aus Video ------------------------------------------------------------------
                log_to_callback(Tag.STATUS, f'Metadaten', f'Metadaten aus GoPro Video {file.name} lesen')
                try:
                    gopro_file = GoProFile(file, verbose=params.verbose)
                except NoVideoError as e:
                    log_to_callback(Tag.STATUS, 'Datei', e.message)
                    continue
                except NoGoProError as e:
                    log_to_callback(Tag.STATUS, 'Datei', e.message)
                    continue
                else:
                    try:
                        # -------------------------------------------------------------------------------------------
                        # Schritt 1:    CeateDate und Timecode des Videos ermitteln
                        #               'exiftool "%%F" -s3 -CreateDate -d !DateFormat!'
                        #               ffprobe liefert die Beginnzeit aus "timecode"
                        #               'ffprobe -v quiet -i "%%F" -select_streams v:0 -show_entries stream_tags=timecode -of default=noprint_wrappers=1:nokey=1'
                        # -------------------------------------------------------------------------------------------
                        # -----------------------------------------------------------------------------
                        # Extract the gpmf data from inputfile: mp4 or bin
                        # -----------------------------------------------------------------------------
                        log_to_callback(Tag.STATUS, 'Lese Telemetrie', f'Telemetrie Daten aus GoPro Video {gopro_file.name} lesen')
                        if not gopro_file.get_gpmf(binary=params.binary, clean=False, profiler=profiler):
                            continue

                        # -----------------------------------------------------------------------------
                        # Set User of GoPro
                        # -----------------------------------------------------------------------------
                        if params.user:
                            gopro_file.user = params.user
                        else:
                            gopro_file.user = GOPRO_USER_09 if gopro_file.model in [GOPRO_08, GOPRO_09] else GOPRO_USER_10

                        # -----------------------------------------------------------------------------
                        # GPS Points are in UTC, read first with and without lock from GPX or Header
                        # -----------------------------------------------------------------------------
                        if params.verbose:
                            log_to_callback(Tag.STATUS, 'Datum aus Header', f'{DateTimeUtils.format_datetime(gopro_file.creation, ISO_FORMAT_TZ)}')
                            log_to_callback(Tag.STATUS, 'Datum aus GPS   ', f'{DateTimeUtils.format_datetime(gopro_file.gps_datetime, ISO_FORMAT_TZ)}')

                        # -------------------------------------------------------------------------------------------
                        # Schritt 3:    ausgeben aller Metadaten
                        # -------------------------------------------------------------------------------------------
                        print_video_metadata(gopro_file, params.verbose)
                        log_to_callback(Tag.STATUS, 'Aktionen', TRENNER)

                        # -------------------------------------------------------------------------------------------
                        # Schritt 4:    Umbenennen des GoPro-Videos entsprechend des ermittelten Namens (Schritt 2)
                        #               ren "%%F" "!Filename!!ExtVideo!"
                        #               der Name des Videos wird entsprechend des gewünschten Formates zusammengesetzt
                        #               Zeit ist in der Form: HH:MM:SS:ss -^> also brauchen wir Pos 0, 3, 6 jeweils Länge 2
                        #               Datum, Zeit, GoProName, GoProUser zusammensetzen
                        #               set "Zeit=!ZeitU:~0,2!!ZeitU:~3,2!!ZeitU:~6,2!"
                        #               set "Filename=!Datum!_!Zeit!-!GoProName!!GoProUser!"
                        # -------------------------------------------------------------------------------------------
                        if not rename_videofile(gopro_file, params.pattern):
                            continue

                        # Sequence ermitteln und sammeln
                        # Ein expliziter Check entfernt das 'None' aus dem Typen 'datetime | None'
                        current_gps_dt = gopro_file.gps_datetime
                        if current_gps_dt is not None:
                            # file.recording ist z. B. 1118 (int)
                            # Wir speichern path und das Datum
                            pattern_groups[gopro_file.recording].append((gopro_file.file, current_gps_dt))
                        else:
                            log_to_callback(Tag.ERR, 'Sequence Fehler', f'Datei {gopro_file.name} hat kein gültiges GPS-Datum für die Sequenz.')

                        # -------------------------------------------------------------------------------------------
                        # Schritt 5:    der Name des Thumbnails wird ermittelt
                        #               Zeitversatz für Thumbs = 5 sec
                        #               set "thumb_position=00:00:05.00"
                        #               set "thumb_time=5"
                        #               call :addSeconds !Zeit! !thumb_time! NeueZeit
                        #               set "FilenameThumb=!Datum!_!NeueZeit!-!GoProName!!GoProUser!"
                        # -------------------------------------------------------------------------------------------
                        #               aus dem GoPro-Video ein Thumbnail extrahieren
                        #               ffmpeg -y -hide_banner -loglevel error -nostats -ss !thumb_position! -i "!Filename!!ExtVideo!" -frames:v 1 "!FilenameThumb!!ExtPhoto!"
                        # -------------------------------------------------------------------------------------------
                        if params.thumb:
                            # -------------------------------------------------------------------------------------------
                            # Thumbnail-Name mit Zeitversatz für Thumbs = 5 sec
                            # -------------------------------------------------------------------------------------------
                            thumbfile = gopro_file.thumbnail(
                                delta=params.delta,
                                over=params.overwrite_thumb)
                            if thumbfile:
                                log_to_callback(Tag.STATUS, f'Thumbnail', f'{thumbfile.name} wird ergänzt')

                                thumb_exif = EExiv2(thumbfile, verbose=params.verbose)
                                thumb_exif.write_exif(
                                    creation_date=gopro_file.gps_datetime,
                                    creation_author=gopro_file.user,
                                    nearest_point=gopro_file.gps_point,
                                    target_tz=gopro_file.tz
                                )

                                log_to_callback(Tag.STATUS, "Datum einsetzen", f'Das Aufnahmedatum wurde in {thumbfile.name} gesetzt')
                                if not (gopro_file.user is None
                                        or gopro_file.user == ''):
                                    log_to_callback(Tag.STATUS, "Autor einsetzen", f'Der Autor wurde in {thumbfile.name} gesetzt')

                        # -------------------------------------------------------------------------------------------
                        # Schritt 6:    aus dem GoPro-Video die Telemetrie-Metadaten extrahieren und ggfls in eine Zip-Datei schreiben
                        #               echo gopro2zip -f -all "!Filename!!ExtVideo!"
                        #               gopro2zip -f -all "!Filename!!ExtVideo!"
                        # -------------------------------------------------------------------------------------------
                        log_to_callback(Tag.STATUS, f'Schreibe Items', f'Schreibe {gopro_file.gps_anzitems} Einzelinformationen in Dateien ...')
                        write_video_datafiles(gopro_file=gopro_file, params=params)

                    except (TypeError, EOFError):
                        continue

            # ###########################################################################################
            # Nicht-GoPro Videos verarbeiten
            #
            # ###########################################################################################
            ii = len(nongoprovideos)
            i = 0

            # Noch VOR der Schleife die Progressbar vorbereiten (selbst bei 0 Videos!)
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(ii))

            if ii > 0:
                log_to_callback(Tag.STATUS, )
                log_to_callback(Tag.STATUS, f'Alle {ii} Nicht-GoPro Videos bearbeiten')
                log_to_callback(Tag.STATUS, )

                for file in nongoprovideos:
                    i += 1
                    log_to_callback(Tag.STATUS, TRENNER)
                    log_to_callback(Tag.STATUS, f'Nicht-GoPro Video {i}/{ii}', f'{file.name} wird verarbeitet')
                    # -> Fortschritt an die GUI / den Logger melden:
                    log_to_callback(Tag.PROGRESS, ProgressEvent.update(i, ii))

                    # - Metadaten aus Video ------------------------------------------------------------------
                    log_to_callback(Tag.STATUS, f'Metadaten', f'Metadaten aus Nicht-GoPro Video {file.name} lesen')

                    try:
                        video_file = VideoFile(file, verbose=params.verbose)
                    except NoVideoError as e:
                        log_to_callback(Tag.STATUS, 'Datei', e.message)
                        continue
                    except NoMetaError as e:
                        log_to_callback(Tag.STATUS, 'Metadaten', e.message)
                        continue
                    else:
                        try:
                            # -------------------------------------------------------------------------------------------
                            # ausgeben aller Metadaten
                            # -------------------------------------------------------------------------------------------
                            # print all metadata from video
                            print_video_metadata(video_file, params.verbose)
                            log_to_callback(Tag.STATUS, 'Aktionen', TRENNER)

                            # -------------------------------------------------------------------------------------------
                            # Umbenennen des Videos entsprechend des Patterns
                            # -------------------------------------------------------------------------------------------
                            if not rename_videofile(video_file, params.pattern):
                                continue

                            if params.thumb:
                                # -------------------------------------------------------------------------------------------
                                # Thumbnail-Name mit Zeitversatz für Thumbs = delta_thumb
                                # -------------------------------------------------------------------------------------------
                                dt = video_file.creation

                                thumbfile = video_file.thumbnail(
                                    delta=params.delta,
                                    over=params.overwrite_thumb)
                                if thumbfile:
                                    thumb_exif = EExiv2(
                                        thumbfile,
                                        verbose=params.verbose)

                                    # ToDo: woher kommt die timezone bei non-GoPro Videos? Aus allen vorhandenen GPX? Über das creationdate?
                                    if video_file.gps_latitude is None or video_file.gps_longitude is None or dt is None:
                                        pt = None
                                    else:
                                        pt: GeoPointTime = GeoPointTime(latitude=video_file.gps_latitude, longitude=video_file.gps_longitude, timestamp=dt, tz=video_file.tz)

                                    thumb_exif.write_exif(
                                        creation_date=dt,
                                        nearest_point=pt,
                                        target_tz=video_file.tz)

                                    log_to_callback(Tag.STATUS, "Datum/Geodaten einsetzen", f"Das Aufnahmedatum/Geoinfo wurde in {thumbfile.name} gesetzt")

                        except TypeError:
                            log_to_callback(Tag.ERR, 'ERROR', f'Nicht-GoPro Video {i}/{ii}', f'{video_file.name} wurde nicht verarbeitet!')
                            continue

            # ###########################################################################################
            # SRT Dateien verarbeiten
            #
            # ###########################################################################################
            ii = len(srtfiles.files)
            i = 0

            # Noch VOR der Schleife die Progressbar vorbereiten (selbst bei 0 Videos!)
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(ii))

            if ii > 0:
                log_to_callback(Tag.STATUS, )
                log_to_callback(Tag.STATUS, f'Alle {ii} SRT Dateien bearbeiten')
                log_to_callback(Tag.STATUS, )

                for file in srtfiles.files:
                    i += 1
                    # -> Fortschritt an die GUI / den Logger melden:
                    log_to_callback(Tag.PROGRESS, ProgressEvent.update(i, ii))

                    log_to_callback(Tag.STATUS, TRENNER)
                    try:
                        log_to_callback(Tag.STATUS, f'SRT Datei {i}/{ii}', f'{file.name} wird verarbeitet')
                        srt_file = SRTExtractor(file=file, verbose=params.verbose)
                        log_to_callback(Tag.STATUS, f'Metadaten', f'Metadaten aus SRT Datei {srt_file.name} lesen')
                        log_to_callback(Tag.STATUS, f'Schreibe Punkte', f'Schreibe {srt_file.gps_anzitems} GPX Punkte in Datei ...')
                        gopro_writer = GoProFileWrite(filepath=file, verbose=params.verbose)
                        outfile = gopro_writer.write_srt(points=srt_file.trackinfo)
                        if outfile.is_file():
                            log_to_callback(Tag.STATUS, f'Schreibe Punkte', f'GPX Datei {outfile} geschrieben ...')

                    except ValueError as e:
                        log_to_callback(Tag.STATUS, 'Datei', str(e))
                        continue
                    except NoSRTError as e:
                        log_to_callback(Tag.STATUS, 'Datei', e.message)
                        continue

            # ###########################################################################################
            # GPMF Dateien verarbeiten
            #
            # ###########################################################################################
            ii = len(gpmffiles.files)
            i = 0

            # Noch VOR der Schleife die Progressbar vorbereiten (selbst bei 0 Videos!)
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(ii))

            if ii > 0:
                log_to_callback(Tag.STATUS, )
                log_to_callback(Tag.STATUS, f'Alle {ii} GPMF Dateien bearbeiten')
                log_to_callback(Tag.STATUS, )

                for file in gpmffiles.files:
                    i += 1

                    log_to_callback(Tag.STATUS, TRENNER)
                    # -> Fortschritt an die GUI / den Logger melden:
                    log_to_callback(Tag.PROGRESS, ProgressEvent.update(i, ii))

                    try:
                        gpmf_file = GpmfFile(file=file, verbose=params.verbose)
                        log_to_callback(Tag.STATUS, f'GPMF Datei {i}/{ii}', f'{gpmf_file.name} wird verarbeitet')

                        log_to_callback(Tag.STATUS, f'Metadaten', f'Metadaten aus GPMF Datei {gpmf_file.name} lesen')
                        gpmf_file.get_raw_telemetry(method=ExtractionMethod.FILE, clean=False, profiler=profiler)

                        log_to_callback(Tag.STATUS, f'Schreibe Punkte', f'Schreibe {gpmf_file.gps_anzitems} GPX Punkte in Datei ...')
                        gopro_writer = GoProFileWrite(filepath=file, verbose=params.verbose)
                        outfile = gopro_writer.write_gpx(points=gpmf_file.gps_items, locked=True)  # nur locked Punkte schreiben
                        if outfile.is_file():
                            log_to_callback(Tag.STATUS, f'Schreibe Punkte', f'GPX Datei {outfile} geschrieben ...')

                    except ValueError as e:
                        log_to_callback(Tag.STATUS, 'Datei', str(e))
                        continue
                    except NoGpmfError as e:
                        log_to_callback(Tag.STATUS, 'Datei', e.message)
                        continue

        # ###########################################################################################
        # alle Fotos mit den Geokoordinaten der GPX-Dateien versorgen
        #
        # ###########################################################################################
        if not params.goproonly:
            log_to_callback(Tag.STATUS, )
            manager = GGPXJpegManager(path_jpeg=fpath,
                                      path_gpx=fpath,
                                      diff_time=params.diff_time,
                                      diff_dist=params.diff_dist,
                                      verbose=params.verbose,
                                      )
            total_jpgs = len(manager.jpg_items)
            log_to_callback(Tag.STATUS, f'Alle {total_jpgs} Fotos bearbeiten')
            log_to_callback(Tag.STATUS, )

            newjpeglist, restjpeglist = manager.nearest_location_or_time()

            # Setze Progressbar-Maximum auf die Gesamtzahl der Fotos für die Umbenennung
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(total_jpgs))
            # rename jpeg files
            log_to_callback(Tag.STATUS, TRENNER)
            log_to_callback(Tag.STATUS, 'Fotos mit Aufnahmedatum umbenennen ->', f'{str(fpath)}')
            newjpeglist, restjpeglist = manager.rename_jpegfiles(newjpeglist, restjpeglist)
            # add metadata and correct timestamps, jpeg with coordinates
            log_to_callback(Tag.STATUS, TRENNER)
            log_to_callback(Tag.STATUS, 'Mit Geokoordinaten ->', f'{str(fpath)}')
            total_new = len(newjpeglist)
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(total_new))
            manager.add_metadata(newjpeglist)
            # add metadata and correct timestamps, jpeg with no coordinates
            log_to_callback(Tag.STATUS, TRENNER)
            log_to_callback(Tag.STATUS, 'Ohne Geokoordinaten ->', f'{str(fpath)}')
            total_rest = len(restjpeglist)
            log_to_callback(Tag.PROGRESS, ProgressEvent.start(total_rest))
            manager.add_metadata(restjpeglist)

        # ###########################################################################################
        # alle GPX Dateien mit description und name tag ergänzen
        #
        # ###########################################################################################
        if params.gpsdescription:
            log_to_callback(Tag.STATUS, )
            log_to_callback(Tag.STATUS, 'Alle GPX Dateien bearbeiten')
            log_to_callback(Tag.STATUS, )
            # find all gpx files and add description to all points
            log_to_callback(Tag.STATUS, 'GPX ergänzen', f'alle im Ordner {str(fpath)} befindlichen GPX Dateien mit ihren Punkten werden um eine Beschreibung (Ortschaft) ergänzt.')
            gpx_manager = GGPXManager(path=fpath, load_on_init=False, verbose=params.verbose)
            gpx_manager.add_description_to_gpxfiles()

        # ###########################################################################################
        # alle GPX Dateien als jpg und html ausgeben
        #
        # ###########################################################################################
        if params.generatemap or params.generatehtml:
            log_to_callback(Tag.STATUS, )
            log_to_callback(Tag.STATUS, 'Alle GPXmaps / GPXhtml aus GPX Dateien erzeugen')
            log_to_callback(Tag.STATUS, )
            mapprocessor = GGPXMapProcessor(path=fpath, params=params)

            if params.generatemap:
                mapprocessor.process_gpx_jpeg()

            if params.generatehtml:
                mapprocessor.process_gpx_html()

        # ###########################################################################################
        # temporäre Dateien aufräumen
        #
        # ###########################################################################################
        if params.clean:
            # Alle zu löschenden Dateien sammeln
            log_to_callback(Tag.STATUS, )
            log_to_callback(Tag.STATUS, 'Alle temporären Dateien löschen')
            log_to_callback(Tag.STATUS, )

            base_path = Path(fpath)

            if base_path.is_dir():
                # 2. Einmaliger, effizienter Verzeichnis-Scan
                # fnmatch.fnmatch prüft, ob der Dateiname auf eines der Patterns passt
                files_to_delete = [
                    file for file in base_path.iterdir()
                    if file.is_file() and any(fnmatch.fnmatch(file.name.casefold(), pattern.casefold()) for pattern in TRASH_EXTENSIONS)
                ]

                # 3. Sicheres Löschen der gesammelten Dateien
                for file in files_to_delete:
                    try:
                        log_to_callback(Tag.STATUS, 'Cleaning', f'Datei {file.name} wird gelöscht ...')
                        file.unlink(missing_ok=True)
                    except OSError as e:
                        log_to_callback(Tag.STATUS, 'Cleaning', f'Fehler beim Löschen der Datei {file.name}: {e}')

        # -------------------------------------------------------------------------------------------
        # Schritt 7:    aus der Liste der GoPro-Videos alle Sequenzen umbenennen
        #               mit einem 2 stelligen numerischen Präfix
        # -------------------------------------------------------------------------------------------
        if params.namesequence:
            renamer = GoProRenamer()
            renamer.rename_sequences(pattern_groups=pattern_groups)

        # Bearbeitung beendet signalisieren
        log_to_callback(Tag.STATUS, 'Ende', f'Alle Verarbeitungsschritte beendet!')

    return 0


# ==========================================================================
# ==========================================================================
if __name__ == "__main__":
    profiling: bool = False
    l_profiler: Profile | None = None

    try:
        if profiling:
            l_profiler = Profile()
            if l_profiler:
                l_profiler.enable()

        # 1. Optionale YAML-Konfiguration laden (Konfigurations-Datei-Priorität: niedrig)
        appp: GoProParameters = GoProParameters()
        appp.load_from_yaml()

        # 2. CLI-Argumente parsen & Werte überschreiben (Kommandozeilen-Priorität: hoch)
        # Die Methode aktualisiert die Instanz 'appp' intern und gibt sie zurück
        appp.parse_args()

        # 3. Hauptprogramm mit allen Abhängigkeiten (inkl. Logger) aufrufen
        logpath = PathUtils.get_script_dir()
        my_logger = AppLogger.create(logfile_path=logpath, use_console=True)
        exit_code = main(params=appp, profiler=l_profiler)

        # 4. Profiling Auswertung
        if l_profiler:
            l_profiler.disable()
            s = StringIO()
            ps = pstats.Stats(l_profiler, stream=s).sort_stats("cumtime")
            print("\n=== TOP 20 PROFILING ZEITFRESSER ===")
            ps.print_stats(20)
            print(s.getvalue())

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
