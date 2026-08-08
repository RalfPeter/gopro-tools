#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 04-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/tracktraffic.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Program : prg_gopro2file_utils.py (main - GoPro Videos and Telemetry Export)
#  Version : 1.0
# ------------------------------------------------------------------------------
#  Klassen:
#    keine
#  Public Methods:
#     print_video_metadata(video_file, verbose) → Print all Metadata
#     write_video_datafiles(gopro_file, params) → Write files with telemetry data
#     rename_videofile(videofile, pattern) → rename a video file from name to a new created file name
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter61@email.de>
# ------------------------------------------------------------------------------

from utils_core import log_to_callback, CallbackTag as Tag, TRENNER
from utils_string import StringUtils as Str
from gpmf_const import SUFFIX_ZIP, GPS_PRINT_FORMAT, MAX_GPS_DISTANCE_METER
from gpmf_meta_video import VideoFile
from gpmf_meta_gopro import GoProFile
from gpmf_klv_points import AcclItems, GyroItems
from gpmf_writer import GoProFileWrite
from gpx_utils import haversine
from prg_gopro2file_map import GGPXMapProcessor
from prg_gopro2file_config import GoProParameters


# --------------------------------------------------------------------------------
def print_video_metadata(video_file: VideoFile, verbose: bool = False):
    """
    Print all Metadata
    """

    if verbose:
        log_to_callback(Tag.STATUS, 'Video', f'{video_file.file}')
        # - Metadaten -------------------------------------------------------------------------------
        log_to_callback(Tag.STATUS, 'Metadaten', TRENNER)
        if isinstance(video_file, GoProFile):
            log_to_callback(Tag.STATUS, 'Camera Model', f'GoPro Hero {video_file.model}')
        else:
            log_to_callback(Tag.STATUS, 'Camera Model', f'{video_file.model}')
        log_to_callback(Tag.STATUS, 'Camera Firmware', f'{video_file.firmware}')
        log_to_callback(Tag.STATUS, 'Camera User', video_file.user)
        log_to_callback(Tag.STATUS, 'Video Startzeit', f'{Str.safe_str(video_file.start_time)} sec')
        log_to_callback(Tag.STATUS, 'Video Dauer', f'{Str.safe_str(video_file.duration)} sec')
        log_to_callback(Tag.STATUS, 'Video Größe', f'{Str.safe_str(video_file.size)} byte')
        # - Dateinamen -------------------------------------------------------------------------------
        log_to_callback(Tag.STATUS, 'Dateinamen', TRENNER)
        log_to_callback(Tag.STATUS, 'Filename', video_file.name)
        log_to_callback(Tag.STATUS, 'Filepath', video_file.path)
        log_to_callback(Tag.STATUS, 'FileExt', video_file.extension)
        if isinstance(video_file, GoProFile):
            log_to_callback(Tag.STATUS, 'FileCore', video_file.basename)
        # - Aufnahmezeiten --------------------------------------------------------------------------
        log_to_callback(Tag.STATUS, 'Aufnahmezeiten', TRENNER)
        log_to_callback(Tag.STATUS, 'Datum aus Header', f'{Str.safe_str(video_file.creation)}')
        if video_file.gps_datetime is not None:
            log_to_callback(Tag.STATUS, 'Datum aus GPS', f'{Str.safe_str(video_file.gps_datetime)}')
        # - GPS / GPX Daten -------------------------------------------------------------------------
        if video_file.gps_point:
            log_to_callback(Tag.STATUS, 'Aufnahmeorte', TRENNER)
            log_to_callback(Tag.STATUS, 'Point aus GPS', f'{Str.safe_str(video_file.gps_point)}')
        # - Metadaten aus dem Header ----------------------------------------------------------------
        if video_file.gps_latitude and video_file.gps_longitude:
            log_to_callback(Tag.STATUS, 'Location aus MP4', f'GPS Punkt im Header ist: Lat/Lon:{Str.safe_str(video_file.gps_latitude):{GPS_PRINT_FORMAT}}, {Str.safe_str(video_file.gps_longitude):{GPS_PRINT_FORMAT}}')

        # Entfernung berechnen
        gps_pt = video_file.gps_point

        if gps_pt is not None and gps_pt.latitude is not None and gps_pt.longitude is not None:
            # Der Linter weiß hier sicher, dass gps_pt kein 'None' mehr sein kann
            distance = haversine(
                gps_pt.latitude,
                gps_pt.longitude,
                video_file.gps_latitude,
                video_file.gps_longitude
            )
            if distance > MAX_GPS_DISTANCE_METER:
                log_to_callback(Tag.STATUS, 'Location DIFFERENZ!!', f'Die beiden Punkte sind weiter als {MAX_GPS_DISTANCE_METER} Meter voneinander entfernt.')


# --------------------------------------------------------------------------------
def write_video_datafiles(gopro_file: GoProFile, params: GoProParameters) -> bool | None:
    """
    Write files with telemetry data
    """

    if gopro_file is None or not gopro_file.has_gpmf or gopro_file.klvlist is None:
        return False

    log_to_callback(Tag.STATUS, 'GPMF', f'Schreibe GPMF Daten für {gopro_file.name}')
    gps_items = gopro_file.gps_items
    accl_items = AcclItems(gopro_file.klvdict).parsed_items
    gyro_items = GyroItems(gopro_file.klvdict).parsed_items

    # Class for writing gopro data
    gopro_writer = GoProFileWrite(gopro_file.file, params.verbose)

    log_to_callback(Tag.STATUS, 'GPMF', 'Schreibe alle Dateien [bin, hex, gps, kml, gyro, accl, json, csv]')
    # BIN-File
    if params.file_bin or params.file_all:
        gopro_writer.write_bin(gopro_file.data)
    # HEX-File
    if params.file_csv_hex or params.file_all:
        gopro_writer.write_hex(gopro_file.klvlist)
    # KML-File
    if params.file_kml or params.file_all:
        gopro_writer.write_kml(gps_items)
    # GPX-File
    if params.file_gpx or params.file_all:
        outfile = gopro_writer.write_gpx(gps_items, locked=True)

        # try to create map file
        if params.generatemap or params.generatehtml:
            mapprocessor = GGPXMapProcessor(path=outfile, params=params)

            if params.generatemap:
                mapprocessor.process_gpx_jpeg()
            if params.generatehtml:
                mapprocessor.process_gpx_html()

    # Virb-File GPX
    if params.file_virb or params.file_all:
        gopro_writer.write_virb(gps_items, locked=True)
    # CSV-File GYRO
    if params.file_csv_gyr or params.file_all:
        gopro_writer.write_csv_gyro(gyro_items)
    # CSV-File ACCL
    if params.file_csv_acc or params.file_all:
        gopro_writer.write_csv_accl(accl_items)
    # CSV-File GPS5
    if params.file_csv_gps or params.file_all:
        gopro_writer.write_csv_gps(gps_items)
    # JSON-File: all fourCC as tree
    if params.file_json or params.file_all:
        gopro_writer.write_json(gopro_file.klvlist)

    # Zip interpreted data to files and delete them
    if params.zip or params.zip_delete:
        if params.zip_delete:
            log_to_callback(Tag.STATUS, 'GPMF', f'Erstelle Zip-Datei {gopro_file.file.with_suffix(SUFFIX_ZIP).name} und lösche Dateien')
        else:
            log_to_callback(Tag.STATUS, 'GPMF', f'Erstelle Zip-Datei {gopro_file.file.with_suffix(SUFFIX_ZIP).name}')
        gopro_writer.write_zip(remove=params.zip_delete)

    return True


# --------------------------------------------------------------------------------
def rename_videofile(videofile: VideoFile, pattern: str) -> bool:
    """
    rename a video file from name to a new created file name
    """
    old_name = videofile.name
    result = videofile.rename(pattern, videofile.gps_datetime, videofile.user)
    prefix = 'GoPro-Video' if isinstance(videofile, GoProFile) else 'Video'

    if result is not None:
        if result:
            if old_name != videofile.name:
                log_to_callback(Tag.STATUS, prefix, f'Die Datei wurde erfolgreich von {old_name} in {videofile.name} umbenannt.')
            return True
        else:
            log_to_callback(Tag.ERR, prefix, f'Could not rename {videofile.name}')
            return False
    else:
        # no need to rename
        return True
