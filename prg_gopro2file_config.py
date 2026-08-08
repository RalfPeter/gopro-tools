#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 04-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/tracktraffic.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Program : prg_gopro2file_config.py (main - GoPro Videos and Telemetry Export)
#  Version : 1.0
# ------------------------------------------------------------------------------
#  Klassen:
#     GoProParameters
#  Public Methods:
#     GoProParameters.check_geonames_update(force_update) → Prüft, ob das GeoNames-Update basierend auf dem Intervall fällig ist.
#     GoProParameters.update_geonames_timestamp() → Setzt den Zeitstempel auf 'jetzt' und sichert ihn direkt in der YAML-Datei.
#     GoProParameters.parse_args()        → Parst alle Kommandozeilenparameter (geerbt + spezifisch) in diese Instanz.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter61@email.de>
# ------------------------------------------------------------------------------

from __future__ import annotations
from typing import final, Any, ClassVar
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, fields, field
import datetime

from utils_config import BaseParameters
from gpmf_const import MAP_WIDTH_PIXELS, MAP_HEIGHT_PIXELS, TRACK_DEFAULT_COLOR, ROUTE_DEFAULT_COLOR, THUMBNAIL_START_OFFSET_SEC, MAX_TIME_DIFFERENCE_SEC, MAX_EVENT_DISTANCE_METER

# Konstante für das Datumsformat (aus Ihrem utils_datetime Framework)
ISO_FORMAT: str = "%Y-%m-%d %H:%M:%S"  # Falls abweichend, Ihr ISO_FORMAT eintragen


# ================================================================================
# ================================================================================
@final
@dataclass
class GoProParameters(BaseParameters):
    """Parameter-Klasse speziell für das gopro2file Tool.

    Verwaltet sämtliche CLI-Optionen für den GoPro-Metadatenexport, die Ratenbegrenzung
    für GeoNames-API-Abfragen sowie die Ausgabeformate.
    """
    # mapsize und inputfiles werden von der Persistierung ausgeschlossen
    EXCLUDED_PERSISTENCE_FIELDS: ClassVar[set[str]] = {
        "mapsize",
        "inputfiles",
    }

    # ==========================================================================
    # Allgemeine Parameter (Nicht in BaseParameters enthalten)
    # ==========================================================================
    clean: bool = True
    recursive: bool = False
    no_cache: bool = False
    user: str = ''
    pattern: str = '%Y%m%d_%H%M%S-%c-%u'
    geonamesupdate: bool = False
    geonamesintervall: int = 30

    # ==========================================================================
    # GoPro & GPS/Geo Spezifische Parameter
    # ==========================================================================
    binary: bool = False
    goproonly: bool = False
    thumb: bool = False
    overwrite_thumb: bool = False
    delta: int = THUMBNAIL_START_OFFSET_SEC
    geo: bool = False
    geoonly: bool = False
    diff_time: int = MAX_TIME_DIFFERENCE_SEC
    diff_dist: int = MAX_EVENT_DISTANCE_METER
    gpsdescription: bool = False
    locked: bool = False
    namesequence: bool = False

    # ==========================================================================
    # Karten & Grafik Parameter
    # ==========================================================================
    mapwidth: int = MAP_WIDTH_PIXELS
    mapheight: int = MAP_HEIGHT_PIXELS
    mapsize: tuple[int, int] = field(init=False)
    color_track: str = TRACK_DEFAULT_COLOR
    color_route: str = ROUTE_DEFAULT_COLOR
    endingpoint: bool = True
    generatemap: bool = False
    generatehtml: bool = False

    # ==========================================================================
    # Datei und Pfad-Parameter
    # ==========================================================================
    zip: bool = False
    zip_delete: bool = False
    file_all: bool = False
    file_bin: bool = False
    file_kml: bool = False
    file_gpx: bool = False
    file_virb: bool = False
    file_json: bool = False
    file_csv_hex: bool = False
    file_csv_gyr: bool = False
    file_csv_acc: bool = False
    file_csv_gps: bool = False
    inputpaths: list[str] | None = None
    inputfiles: list[str] | None = None

    # ==========================================================================
    # GUI-Zustands-Parameter
    # ==========================================================================
    selected_folder: str = field(default='', init=False)

    # ==========================================================================
    # Interne GeoNames Maintenance (Automatisch via YAML gespeichert)
    # ==========================================================================
    geonames_last_update: str = field(default="1000-01-01 00:00:00", init=False)
    geonames_interval_days: int = field(default=30, init=False)

    # --------------------------------------------------------------------------------
    def __post_init__(self) -> None:
        """Initialisiert berechnete Verbund-Felder und Listen-Defaults sicher."""
        if not self.inputpaths:
            self.inputpaths = ['./']

        self.mapsize = (self.mapwidth, self.mapheight)

    # --------------------------------------------------------------------------------
    def check_geonames_update(self, force_update: bool = False) -> bool:
        """Prüft, ob das GeoNames-Update basierend auf dem Intervall fällig ist.

        :param force_update: (bool) Erzwingt das Update unabhängig vom Zeitstempel.
        :return: True, wenn aktualisiert werden muss, andernfalls False.
        :rtype: bool
        """
        if force_update:
            return True

        try:
            last_update = datetime.datetime.strptime(self.geonames_last_update, ISO_FORMAT)
            next_update = last_update + datetime.timedelta(days=self.geonames_interval_days)
            return datetime.datetime.now() > next_update
        except (ValueError, AttributeError):
            return True

    # --------------------------------------------------------------------------------
    def update_geonames_timestamp(self) -> None:
        """Setzt den Zeitstempel auf 'jetzt' und sichert ihn direkt in der YAML-Datei."""
        self.geonames_last_update = datetime.datetime.now().strftime(ISO_FORMAT)

    # --------------------------------------------------------------------------------
    def _update_from_namespace(self, args: Namespace) -> None:
        """Aktualisiert alle Attribute dieser Instanz inklusive Verbund-Feldern aus der CLI.

        :param args: (Namespace) Der Namespace aus dem ArgumentParser.
        """
        # Vorab-Zuweisung des Verbund-Feldes mapsize abfangen
        map_width = getattr(args, self.Fields.mapwidth, MAP_WIDTH_PIXELS)
        map_height = getattr(args, self.Fields.mapheight, MAP_HEIGHT_PIXELS)
        self.mapsize = (map_width, map_height)

        # Basis-Logik via Reflection ausführen
        super().update_from_namespace(args)

        # Finale Absicherung des Tupels nach dem Reflection-Loop
        self.mapsize = (self.mapwidth, self.mapheight)

    # --------------------------------------------------------------------------------
    def parse_args(self) -> GoProParameters:
        """Parst alle Kommandozeilenparameter (geerbt + spezifisch) in diese Instanz.

        :return: Das aktualisierte Instanzobjekt (Self).
        :rtype: GoProParameters
        """
        # F stellt alle Feldnamen als Attribute bereit (z. B. F.clean -> "clean")
        F = self.Fields
        class_defaults: dict[str, Any] = {f.name: f.default for f in fields(self)}
        parser = ArgumentParser(description="GoPro Export & Geocoding CLI")

        # 1. Argumente der geerbten Basisklasse BaseParameters
        parser.add_argument("-v", f"--{F.verbose}", action="store_true", default=class_defaults[F.verbose], help="Erhöht die Detailstufe der Log-Ausgabe")
        parser.add_argument("-l", f"--{F.log}", action="store_true", default=class_defaults[F.log], help="Aktiviert das Logging in eine Datei")

        # 2. Allgemeine Argumente der Subklasse
        parser.add_argument("-c", f"--{F.clean}", action="store_true", default=class_defaults[F.clean], help="Clean directory and delete all temp files")
        parser.add_argument("-r", f"--{F.recursive}", action="store_true", default=class_defaults[F.recursive], help="Recursive find all files by pattern in inputfiles")
        parser.add_argument("-n", f"--{F.no_cache}", action="store_true", default=class_defaults[F.no_cache], help="Disable caching of osm tiles")
        parser.add_argument("-u", f"--{F.user}", action="store", default=class_defaults[F.user], help="username for using in renaming the videos")
        parser.add_argument("-p", f"--{F.pattern}", action="store", default=class_defaults[F.pattern], help="new filename pattern for renaming the videos")
        parser.add_argument("-o", f"--{F.geonamesupdate}", action="store_true", default=class_defaults[F.geonamesupdate], help="Update Geonames data if needed")

        # 3. GoPro- und Geodaten-spezifische Argumente
        parser.add_argument("-b", f"--{F.binary}", action="store_true", default=class_defaults[F.binary], help="read data from bin file")
        parser.add_argument("-gp", f"--{F.goproonly}", action="store_true", default=class_defaults[F.goproonly], help="only edit gopro videos")
        parser.add_argument("-t", f"--{F.thumb}", action="store_true", default=class_defaults[F.thumb], help="create a thumbnail from video")
        parser.add_argument("-m", f"--{F.generatemap}", action="store_true", default=class_defaults[F.generatemap], help="create a jpeg from gpx")
        parser.add_argument("-ot", f"--{F.overwrite_thumb}", action="store_true", default=class_defaults[F.overwrite_thumb], help="overwrite existing thumbnails")
        parser.add_argument("-d", f"--{F.delta}", action="store", type=int, default=class_defaults[F.delta], help="time delta for thumbnail from video")
        parser.add_argument("-g", f"--{F.geo}", action="store_true", default=class_defaults[F.geo], help="geocode all photos in directory of video files")
        parser.add_argument("-go", f"--{F.geoonly}", action="store_true", default=class_defaults[F.geoonly], help="only geocode all photos in directory of video files")
        parser.add_argument("-et", f"--{F.diff_time}", action="store", type=int, default=class_defaults[F.diff_time], help="max time difference in sec for a gps point in gpx file")
        parser.add_argument("-ed", f"--{F.diff_dist}", action="store", type=int, default=class_defaults[F.diff_dist], help="max distance in meter for a gps point in gpx file")
        parser.add_argument("-x", f"--{F.gpsdescription}", action="store_true", default=class_defaults[F.gpsdescription], help="Add description to every gps point in a gpx file")
        parser.add_argument("-lock", f"--{F.locked}", action="store_true", default=class_defaults[F.locked], help="Use only locked GPS points from telemetry")

        # 4. Karten Layout Argumente
        parser.add_argument("-mw", f"--{F.mapwidth}", type=int, default=class_defaults[F.mapwidth], help="Map size from gpx file in pixels")
        parser.add_argument("-mh", f"--{F.mapheight}", type=int, default=class_defaults[F.mapheight], help="Map size from gpx file in pixels")
        parser.add_argument("-k", f"--{F.generatehtml}", action="store_true", default=class_defaults[F.generatehtml], help="Generate html even if cleaning directory")
        parser.add_argument("-ct", f"--{F.color_track}", action="store", default=class_defaults[F.color_track], help="Color for the track to plot on map")
        parser.add_argument("-cr", f"--{F.color_route}", action="store", default=class_defaults[F.color_route], help="Color for the route to plot on map")
        parser.add_argument("-e", f"--{F.endingpoint}", action="store_true", default=class_defaults[F.endingpoint], help="Last point as marker to plot on map")
        parser.add_argument("-s", f"--{F.namesequence}", action="store_true", default=class_defaults[F.namesequence], help="Rename all sequence GoPro Videos with prefix")

        # 5. Output-Dateiformate (Gruppe)
        fileformat = parser.add_argument_group("Output", "Output file formats")
        fileformat.add_argument("-z", f"--{F.zip}", action="store_true", default=class_defaults[F.zip], help="zip files generated with all and clear them")
        fileformat.add_argument("-zd", f"--{F.zip_delete}", action="store_true", default=class_defaults[F.zip_delete], help="zip generated files and clear")
        fileformat.add_argument("-all", f"--{F.file_all}", action="store_true", default=class_defaults[F.file_all], help="output all files generated from gpmf data")
        fileformat.add_argument("-bin", f"--{F.file_bin}", action="store_true", default=class_defaults[F.file_bin], help="output the raw data file")
        fileformat.add_argument("-kml", f"--{F.file_kml}", action="store_true", default=class_defaults[F.file_kml], help="output the gps points as kml file")
        fileformat.add_argument("-gpx", f"--{F.file_gpx}", action="store_true", default=class_defaults[F.file_gpx], help="output the gps points as gpx file")
        fileformat.add_argument("-vib", f"--{F.file_virb}", action="store_true", default=class_defaults[F.file_virb], help="output the gps points as virb-gpx file")
        fileformat.add_argument("-jsn", f"--{F.file_json}", action="store_true", default=class_defaults[F.file_json], help="output all data as json file")
        fileformat.add_argument("-hex", f"--{F.file_csv_hex}", action="store_true", default=class_defaults[F.file_csv_hex], help="output all data as hex file")
        fileformat.add_argument("-gyr", f"--{F.file_csv_gyr}", action="store_true", default=class_defaults[F.file_csv_gyr], help="output the gyroscope data as csv file")
        fileformat.add_argument("-acc", f"--{F.file_csv_acc}", action="store_true", default=class_defaults[F.file_csv_acc], help="output the accelerator data as csv file")
        fileformat.add_argument("-gps", f"--{F.file_csv_gps}", action="store_true", default=class_defaults[F.file_csv_gps], help="output the gps points as csv file")

        # 6. Positions-Argumente (inputpaths)
        fn_raw = F.inputpaths
        parser.add_argument(fn_raw, nargs='*', help="Path with video files or binary metadata dumps")

        # Parsen der CLI-Argumente
        l_args, _ = parser.parse_known_args()

        # Korrektur des Typs/Namens des Positions-Arguments im Namespace
        if hasattr(l_args, fn_raw):
            setattr(l_args, F.inputpaths, getattr(l_args, fn_raw))

        # Übergabe an das dynamische Mapping
        self._update_from_namespace(l_args)
        return self
