#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : prg_gopro2file_map.py
#  Version           : 2.0
#  Beschreibung      : Keine Beschreibung verfügbar.
#  Zeilen            : 674
#  Abhängigkeiten    : PIL, abc, contextlib, dataclasses, datetime, folium, functools, geotiler, hashlib, math, pathlib
#                     re
#  Klassen           : GeoBounds, TileCache, GpxMapCalculator, GpxMapGeneratorBase (ABC), GpxMapGeneratorHtml
#                     GpxMapGeneratorJPG, GGPXMapProcessor
# ------------------------------------------------------------------------------
#  Public Methoden:
#    GpxMapCalculator                                     → Berechnet die Bounding Box und den optimalen Zoom-Level für eine Menge von Geo-Punkten.
#      get_bounds(list[GPXTrackInfo], bool)               → Berechnet die Bounding Box (min_lon, min_lat, max_lon, max_lat) aller Punkte.
#      calculate_zoom_level(GeoBounds, tuple[int, 
#                           int], float, float)           → Berechnet den Zoom-Level, um die Bounding Box in die Kartengröße einzupassen.
#
#    GpxMapGeneratorBase                                  → Abstrakte Basisklasse für die Generierung von GPX-Karten.
#      generate()                                         → Steuert die Generierung aller Karten für Tracks und Routen.
#
#    GGPXMapProcessor                                     → Koordiniert den gesamten Prozess des Ladens von GPX-Daten und der Generierung von.
#      process_gpx_jpeg()                                 → Führt den gesamten Prozess der Kartengenerierung durch.
#      process_gpx_html()                                 → Führt den gesamten Prozess der Kartengenerierung durch.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from contextlib import suppress
import re
import math
from datetime import datetime
import geotiler
from geotiler.cache import caching_downloader
from geotiler.tile.io import fetch_tiles
from functools import partial
import hashlib
from PIL import Image, ImageDraw as PILImageDrawModule
from folium import Map, PolyLine, Marker, CustomIcon

from rpg_utils.utils_core import log_to_callback, CallbackTag as Tag
from rpg_utils.utils_datetime import TZ_UTC
from rpg_utils.utils_filepath import PathUtils
from rpg_gpmf.gpmf_const import SUFFIX_JPEG, SUFFIX_HTML
from rpg_gpx.gpx_schema import GeoPointTime, GPXTrackInfo
from rpg_gpmf.gpmf_exif import EExiv2
from rpg_gpmf.gpmf_gpx import GGPX
from prg_gopro2file_config import GoProParameters

# Constants for Map and OSM tile calculation
MAP_ZOOM = 15     # Map zoom
MIN_ZOOM_LEVEL: int = 0
MAX_ZOOM_LEVEL: int = 19
# OSM Tiles
TILE_SIZE = 256   # OSM tile size in pixels
TILE_CACHE: str = "tilecache"

# Konstanten für Tile-Provider
CARTO_TILE_URL = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
CARTO_TILE_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)
OSM_TILE_URL: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_TILE_ATTR: str = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'


# ================================================================================
# ================================================================================
@dataclass(frozen=True)
class GeoBounds:
    """Repräsentiert die geografische Bounding Box eines Tracks."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


# ================================================================================
# ================================================================================
class TileCache:
    """GeoTiler-kompatibler Tile-Cache mit persistentem Dateisystem-Backend."""

    # --------------------------------------------------------------------------------
    def __init__(self, cache_dir: Path) -> None:
        """Initialisiert den TileCache und legt das Cache-Verzeichnis an.
        
        :param cache_dir: (Path) Wurzelverzeichnis für gespeicherte Tiles.
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Geotiler-kompatibler Downloader mit File-Cache
        self.downloader = partial(
            caching_downloader,
            self._cache_get,
            self._cache_set,
            fetch_tiles,
        )

    # ---------------------------------------------------------------------
    def _tile_path(self, url: str) -> Path:
        """Erzeugt einen Dateipfad für eine Tile-URL.
        
        :param url: (str) Vollständige Tile-URL.
        :return: (Path) Beschreibung
        """
        match = re.search(r"/(\d+)/(\d+)/(\d+)\.png", url)
        if match:
            z, x, y = match.groups()
            return self.cache_dir / z / x / f"{y}.png"
        hash_name = hashlib.md5(url.encode("utf-8")).hexdigest()
        return self.cache_dir / hash_name[:2] / f"{hash_name}.png"

    # ---------------------------------------------------------------------
    def _cache_get(self, url: str) -> bytes | None:
        """Liest ein gecachtes Tile vom Dateisystem.
        
        :param url: (str) Vollständige Tile-URL als Cache-Schlüssel.
        :return: (bytes | None) Beschreibung
        """
        path = self._tile_path(url)
        return path.read_bytes() if path.exists() else None

    # ---------------------------------------------------------------------
    def _cache_set(self, url: str, data: bytes | None) -> None:
        """Speichert ein Tile auf dem Dateisystem.
        
        :param url: (str) Vollständige Tile-URL als Cache-Schlüssel.
        :param data: (bytes | None) PNG-Bytes des Tiles, oder None bei Fehler.
        """
        if not data:
            return
        path = self._tile_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


# ================================================================================
# ================================================================================
class GpxMapCalculator:
    """Berechnet die Bounding Box und den optimalen Zoom-Level für eine Menge von Geo-Punkten."""

    DEFAULT_MIN_LAT_LON_DIFF: float = 0.0001
    WORLD_WIDTH_DEGREES: float = 360.0
    WORLD_HEIGHT_DEGREES: float = 180.0

    # -------------------------------------------------------------------------------------------
    @classmethod
    def get_bounds(cls, track_routes: list[GPXTrackInfo], verbose: bool = False) -> GeoBounds | None:
        """Berechnet die Bounding Box (min_lon, min_lat, max_lon, max_lat) aller Punkte.
        
        :param track_routes: (list[GPXTrackInfo]) :type track_routes: list[GpxTrackInfo] Liste der zu prüfenden Track-Informationen.
        :param verbose: (bool) :type verbose: bool Gibt zusätzliche Debug-Informationen aus.
        :return: (GeoBounds | None) Beschreibung
        """
        if verbose:
            log_to_callback(Tag.STATUS, cls.__name__, "Bounding Box der Tracks/Routen ermitteln ...")

        if not track_routes:
            return None

        # Wir sammeln Latitudes und Longitudes in einem Rutsch, um die Performance zu verdoppeln
        lats: list[float] = []
        lons: list[float] = []

        # Iteration über die Werte des Dictionarys (GpxTrackInfo-Objekte)
        # und dann über das 'locations'-Attribut jedes Objekts.
        for track_info in track_routes:
            for point in track_info.points:
                if point.latitude is not None and point.longitude is not None:
                    lats.append(point.latitude)
                    lons.append(point.longitude)

        if not lats or not lons:
            return None

        return GeoBounds(
            min_lon=min(lons),
            min_lat=min(lats),
            max_lon=max(lons),
            max_lat=max(lats)
        )

    # -------------------------------------------------------------------------------------------
    @staticmethod
    def calculate_zoom_level(bounds: GeoBounds, map_size: tuple[int, int], min_lat_diff: float = DEFAULT_MIN_LAT_LON_DIFF, min_lon_diff: float = DEFAULT_MIN_LAT_LON_DIFF) -> int:
        """Berechnet den Zoom-Level, um die Bounding Box in die Kartengröße einzupassen.
        
        :param bounds: (GeoBounds) :type bounds: GeoBounds Die geografische Bounding Box.
        :param map_size: (tuple[int, int]) :type map_size: tuple[int, int] Kartengröße (Breite, Höhe) in Pixeln.
        :param min_lat_diff: (float) :type min_lat_diff: float Minimale Breitengraddifferenz, um zu hohe Zooms zu vermeiden.
        :param min_lon_diff: (float) :type min_lon_diff: float Minimale Längengraddifferenz, um zu hohe Zooms zu vermeiden.
        :return: (int) Beschreibung
        """
        lat_diff = max(bounds.max_lat - bounds.min_lat, min_lat_diff)
        lon_diff = max(bounds.max_lon - bounds.min_lon, min_lon_diff)

        map_width, map_height = map_size

        # Berechnung basierend auf der Mercator-Projektion
        zoom_lon = math.log2(GpxMapCalculator.WORLD_WIDTH_DEGREES / lon_diff * (map_width / TILE_SIZE))
        zoom_lat = math.log2(GpxMapCalculator.WORLD_HEIGHT_DEGREES / lat_diff * (map_height / TILE_SIZE))

        zoom = min(zoom_lon, zoom_lat)

        # Sicheres Klemmen des Zoom-Levels mithilfe der extrahierten Konstanten
        return max(MIN_ZOOM_LEVEL, min(math.floor(zoom), MAX_ZOOM_LEVEL))


# ================================================================================
# ================================================================================
class GpxMapGeneratorBase(ABC):
    """Abstrakte Basisklasse für die Generierung von GPX-Karten."""

    # --------------------------------------------------------------------------------
    def __init__(self,
                 tracks: dict[Path, list[GPXTrackInfo]],
                 routes: dict[Path, list[GPXTrackInfo]],
                 ct: str, cr: str,
                 ending_point: bool,
                 map_size: tuple[int, int],
                 user: str = '',
                 cache: bool = False,
                 clean: bool = True,
                 verbose: bool = False):
        """Funktionsbeschreibung.
        
        :param tracks: (dict[Path, list[GPXTrackInfo]]) Zuordnung von Dateipfaden zu Tracks.
        :param routes: (dict[Path, list[GPXTrackInfo]]) Zuordnung von Dateipfaden zu Routen.
        :param ct: (str) Farbe für Tracks.
        :param cr: (str) Farbe für Routen.
        :param ending_point: (bool) Flag, ob der Endpunkt markiert werden soll.
        :param map_size: (tuple[int, int]) Kartengröße in Pixeln zur Zoom-Berechnung.
        :param user: (str) Name des Erstellers für Autorenschaft / Metadaten.
        :param cache: (bool) Instanz des Tile-Caches für den Karten-Downloader nutzen.
        :param clean: (bool) Flag, ob temporäre Arbeitsdateien gelöscht werden sollen.
        :param verbose: (bool) Gibt zusätzliche Debug-Informationen aus.
        """
        self.classname: str = self.__class__.__name__
        self.tracks: dict[Path, list[GPXTrackInfo]] = tracks
        self.routes: dict[Path, list[GPXTrackInfo]] = routes
        self.ct: str = ct
        self.cr: str = cr
        self.ending_point: bool = ending_point
        self.map_size: tuple[int, int] = map_size
        self.user: str = user
        self.cache: bool = cache
        self.clean: bool = clean
        self.verbose: bool = verbose
        self.resourcedir: Path = PathUtils.get_resource_dir()

        # Pfade zu den physischen Bilddateien aus der Basisklasse nutzen und skalieren
        self.icon_size: tuple[int, int] = (32, 32)
        self.start_icon_path = self.resourcedir / 'start_icon.png'
        self.end_icon_path = self.resourcedir / 'end_icon.png'
        # Tile-Cache autonom auf Basis des Boolean-Flags instanziieren
        self.tile_cache = TileCache(cache_dir=Path(PathUtils.get_data_dir() / TILE_CACHE)) if cache else None

    # -------------------------------------------------------------------------------------------
    @staticmethod
    def _get_map_filename(filename: Path, suffix: str) -> str | None:
        """Dateinamen der Html- und JPG-Datei.
        
        :param filename: (Path) Beschreibung
        :param suffix: (str) Beschreibung
        :return: (str | None) Beschreibung
        """
        basename = Path(filename).with_suffix('')  # mögliches suffix / extension entfernen
        map_file = basename.with_suffix(suffix)
        return str(map_file)

    # -------------------------------------------------------------------------------------------
    def generate(self) -> bool:
        """Steuert die Generierung aller Karten für Tracks und Routen.
        
        :return: (bool) Beschreibung des Rückgabewerts.
        """

        if not self.tracks and not self.routes:
            return False

        all_paths: set[Path] = set(self.tracks.keys()) | set(self.routes.keys())
        any_generated: bool = False

        for trackpath in all_paths:
            trackinfos: list[GPXTrackInfo] = self.tracks.get(trackpath, [])
            routeinfos: list[GPXTrackInfo] = self.routes.get(trackpath, [])
            total_elements: int = len(trackinfos) + len(routeinfos)

            # 1. Gesamtübersicht generieren (Tracks UND Routen auf einer Map)
            if total_elements > 0:
                if self._generate(trackpath, trackinfos, routeinfos):
                    any_generated = True

            # Optimierung: Wenn nur 1 Element existiert, ist die Einzelkarte identisch zu "_O"
            if total_elements <= 1:
                if self.verbose and total_elements == 1:
                    log_to_callback(Tag.STATUS, self.classname, f"Überspringe Einzelkarten für {trackpath.name}, da nur ein Element existiert.")
                continue

            map_counter: int = 1
            # 2. Einzelkarten für jeden Track generieren (nur bei mehreren Elementen)
            for trackroute in trackinfos:
                suffix: str = f"_{map_counter:02d}"
                self._generate(trackpath, [trackroute], [], suffix=suffix)
                map_counter += 1

            # 3. Einzelkarten für jede Route generieren (nur bei mehreren Elementen)
            for trackroute in routeinfos:
                suffix: str = f"_{map_counter:02d}"
                self._generate(trackpath, [], [trackroute], suffix=suffix)
                map_counter += 1

        return any_generated

    # --------------------------------------------------------------------------------
    @abstractmethod
    def _generate(self,
                  trackpath: Path,
                  tracks: list[GPXTrackInfo],
                  routes: list[GPXTrackInfo],
                  suffix: str = "") -> bool:
        """Abstrakte Methode zur formatspezifischen Kartenerstellung.
        
        :param trackpath: (Path) Der ursprüngliche Dateipfad der GPX-Datei.
        :param tracks: (list[GPXTrackInfo]) Liste der zu zeichnenden Tracks.
        :param routes: (list[GPXTrackInfo]) Liste der zu zeichnenden Routen.
        :param suffix: (str) Das Suffix für den Dateinamen (z. B. '_O', '_01').
        :return: (bool) Beschreibung
        """
        pass


# ================================================================================
# ================================================================================
class GpxMapGeneratorHtml(GpxMapGeneratorBase):
    """Generiert eine interaktive Karte im HTML-Format unter Verwendung von Folium."""

    # --------------------------------------------------------------------------------
    def __init__(self,
                 tracks: dict[Path, list[GPXTrackInfo]],
                 routes: dict[Path, list[GPXTrackInfo]],
                 ct: str, cr: str,
                 ending_point: bool,
                 map_size: tuple[int, int],
                 verbose: bool = False):
        """Initialisiert den HTML-Generator über die Basisklasse.
        
        :param tracks: (dict[Path, list[GPXTrackInfo]]) Beschreibung
        :param routes: (dict[Path, list[GPXTrackInfo]]) Beschreibung
        :param ct: (str) Beschreibung
        :param cr: (str) Beschreibung
        :param ending_point: (bool) Beschreibung
        :param map_size: (tuple[int, int]) Beschreibung
        :param verbose: (bool) Beschreibung
        """
        super().__init__(tracks, routes, ct, cr, ending_point, map_size, '', False, False, verbose)

    # --------------------------------------------------------------------------------
    def _draw_path(self, mymap: Map, trackroutes: list[GPXTrackInfo], color: str) -> None:
        """Zeichert die übergebenen Tracks oder Routen als PolyLines und Marker auf die Folium-Map.
        
        :param mymap: (Map) Beschreibung
        :param trackroutes: (list[GPXTrackInfo]) Beschreibung
        :param color: (str) Beschreibung
        """
        for trackroute in trackroutes:
            if not trackroute.points:
                continue

            PolyLine(
                [(loc.latitude, loc.longitude) for loc in trackroute.points],
                color=color,
                weight=5,
                opacity=0.5
            ).add_to(mymap)

            first_point = trackroute.points[0]
            if first_point.latitude is not None and first_point.longitude is not None:
                start_point: list[float] = [first_point.latitude, first_point.longitude]
                # Folium CustomIcon erstellen (icon_size analog zur Basisklasse)
                html_start_icon = CustomIcon(
                    icon_image=str(self.start_icon_path),
                    icon_size=self.icon_size  # Nutzt (32, 32) aus der Basisklasse
                )
                Marker(location=start_point, icon=html_start_icon).add_to(mymap)

            if self.ending_point:
                last_point = trackroute.points[-1]
                if last_point.latitude is not None and last_point.longitude is not None:
                    end_point: list[float] = [last_point.latitude, last_point.longitude]
                    # Folium CustomIcon erstellen (icon_size analog zur Basisklasse)
                    html_end_icon = CustomIcon(
                        icon_image=str(self.end_icon_path),
                        icon_size=self.icon_size
                    )
                    Marker(location=end_point, icon=html_end_icon).add_to(mymap)

    # --------------------------------------------------------------------------------
    def _generate(self,
                  trackpath: Path,
                  tracks: list[GPXTrackInfo],
                  routes: list[GPXTrackInfo],
                  suffix: str = "") -> bool:
        """Erzeugt eine interaktive HTML-Karte aus den übergebenen Tracks und Routen.
        
        :param trackpath: (Path) Beschreibung
        :param tracks: (list[GPXTrackInfo]) Beschreibung
        :param routes: (list[GPXTrackInfo]) Beschreibung
        :param suffix: (str) Beschreibung
        :return: (bool) Beschreibung
        """
        all_elements: list[GPXTrackInfo] = tracks + routes
        if not all_elements:
            return False

        trackpath = trackpath.with_suffix(suffix)
        htm_file = self._get_map_filename(Path(trackpath), SUFFIX_HTML)

        if not htm_file:
            return False
        msg_map = f" ({suffix})" if suffix else ""
        log_to_callback(Tag.STATUS, self.classname, f"Generiere Html{msg_map} aus {len(tracks)} Tracks und {len(routes)} Routen: {Path(htm_file).name}")

        bounds = GpxMapCalculator.get_bounds(all_elements, self.verbose)
        if bounds is None:
            log_to_callback(Tag.STATUS, self.classname, "Keine gültigen Koordinaten gefunden.")
            return False

        zoom = GpxMapCalculator.calculate_zoom_level(bounds, self.map_size)

        with suppress(FileNotFoundError):
            Path(htm_file).unlink(missing_ok=True)

        center_lat: float = (bounds.min_lat + bounds.max_lat) / 2
        center_lon: float = (bounds.min_lon + bounds.max_lon) / 2

        mymap = Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles=OSM_TILE_URL,
            attr=OSM_TILE_ATTR,
        )
        mymap.fit_bounds([[bounds.min_lat, bounds.min_lon], [bounds.max_lat, bounds.max_lon]])

        self._draw_path(mymap=mymap, trackroutes=tracks, color=self.ct)
        self._draw_path(mymap=mymap, trackroutes=routes, color=self.cr)

        if self.verbose:
            log_to_callback(Tag.STATUS, self.classname, f'{Path(htm_file).name} wird geschrieben')

        mymap.save(htm_file)
        return True


# ================================================================================
# ================================================================================
class GpxMapGeneratorJPG(GpxMapGeneratorBase):
    """Generiert eine Rasterkarte im JPEG-Format unter Verwendung von GeoTiler."""

    # --------------------------------------------------------------------------------
    def __init__(self,
                 tracks: dict[Path, list[GPXTrackInfo]],
                 routes: dict[Path, list[GPXTrackInfo]],
                 ct: str, cr: str,
                 ending_point: bool,
                 map_size: tuple[int, int],
                 user: str = '',
                 cache: bool = False,
                 clean: bool = True,
                 verbose: bool = False):
        """Initialisiert den JPG-Generator über die Basisklasse.
        
        :param tracks: (dict[Path, list[GPXTrackInfo]]) Beschreibung
        :param routes: (dict[Path, list[GPXTrackInfo]]) Beschreibung
        :param ct: (str) Beschreibung
        :param cr: (str) Beschreibung
        :param ending_point: (bool) Beschreibung
        :param map_size: (tuple[int, int]) Beschreibung
        :param user: (str) Beschreibung
        :param cache: (bool) Beschreibung
        :param clean: (bool) Beschreibung
        :param verbose: (bool) Beschreibung
        """
        super().__init__(tracks, routes, ct, cr, ending_point, map_size, user, cache, clean, verbose)

    # --------------------------------------------------------------------------------
    def _draw_path(self, gmap: geotiler.Map, image: Image.Image, draw: PILImageDrawModule.ImageDraw, trackroutes: list[GPXTrackInfo], color: str) -> datetime | None:
        """Zechnet die übergebenen Tracks oder Routen und platziert die vordefinierten Icons.
        
        :param gmap: (geotiler.Map) Die Geotiler-Karteninstanz zur Koordinatenkonvertierung.
        :param image: (Image.Image) Das PIL-Image, auf das die Icons kopiert werden.
        :param draw: (PILImageDrawModule.ImageDraw) Das PIL-Draw-Objekt zum Zeichnen auf dem Bild.
        :param trackroutes: (list[GPXTrackInfo]) Liste der zu zeichnenden Track- oder Routeninformationen.
        :param color: (str) Die Farbe, in der die Linien gezeichnet werden sollen.
        :return: (datetime | None) Beschreibung
        """
        trackroute_time: datetime | None = None

        for trackroute in trackroutes:
            if not trackroute.points:
                continue

            if not trackroute_time and trackroute.points[0].timestamp:
                trackroute_time = trackroute.points[0].timestamp

            pixel_coords = [
                gmap.rev_geocode((pt.longitude, pt.latitude))
                for pt in trackroute.points
            ]

            # Linien zeichnen
            for i in range(1, len(pixel_coords)):
                draw.line(
                    [pixel_coords[i - 1], pixel_coords[i]],
                    fill=color,
                    width=3
                )

            # Startpunkt: Vorgefertigtes Icon zentriert platzieren
            if pixel_coords:
                x0, y0 = pixel_coords[0]
                start_icon = Image.open(self.start_icon_path).convert('RGBA').resize(self.icon_size, Image.Resampling.LANCZOS)
                image.paste(start_icon, (int(x0) - 16, int(y0) - 16), start_icon)

            # Endpunkt: Vorgefertigtes Icon zentriert platzieren
            if self.ending_point and pixel_coords:
                x1, y1 = pixel_coords[-1]
                end_icon = Image.open(self.end_icon_path).convert('RGBA').resize(self.icon_size, Image.Resampling.LANCZOS)
                image.paste(end_icon, (int(x1) - 16, int(y1) - 16), end_icon)

        return trackroute_time

    # --------------------------------------------------------------------------------
    def _generate(self,
                  trackpath: Path,
                  tracks: list[GPXTrackInfo],
                  routes: list[GPXTrackInfo],
                  suffix: str = "") -> bool:
        """Erzeugt eine JPG-Rasterkarte aus den übergebenen Tracks und Routen mit GeoTiler.
        
        :param trackpath: (Path) Beschreibung
        :param tracks: (list[GPXTrackInfo]) Beschreibung
        :param routes: (list[GPXTrackInfo]) Beschreibung
        :param suffix: (str) Beschreibung
        :return: (bool) Beschreibung
        """
        all_elements: list[GPXTrackInfo] = tracks + routes
        if not all_elements:
            return False

        trackpath = trackpath.with_suffix(suffix)
        jpg_file = self.__class__._get_map_filename(trackpath, SUFFIX_JPEG)

        if jpg_file is None:
            log_to_callback(Tag.STATUS, self.classname, f"Name der jpeg Datei ist leer: keine Verarbeitung von {trackpath}")
            return False

        msg_map = f" ({suffix})" if suffix else ""
        log_to_callback(Tag.STATUS, self.classname, f"Generiere Map{msg_map} aus {len(tracks)} Tracks und {len(routes)} Routen: {Path(jpg_file).name}")

        bounds = GpxMapCalculator.get_bounds(all_elements, self.verbose)
        if bounds is None:
            log_to_callback(Tag.STATUS, self.classname, "Keine gültigen Koordinaten gefunden.")
            return False

        center_lat = (bounds.min_lat + bounds.max_lat) / 2
        center_lon = (bounds.min_lon + bounds.max_lon) / 2
        first_lat = all_elements[0].points[0].latitude
        first_lon = all_elements[0].points[0].longitude

        zoom = GpxMapCalculator.calculate_zoom_level(bounds, self.map_size)

        if zoom <= 18:
            gmap = geotiler.Map(extent=(bounds.min_lon, bounds.min_lat, bounds.max_lon, bounds.max_lat), size=self.map_size)
        else:
            gmap = geotiler.Map(center=(center_lon, center_lat), zoom=zoom, size=self.map_size)

        # Download über den autonom verwalteten Cache steuern
        downloader_instance = self.tile_cache.downloader if self.tile_cache else None
        base_image = geotiler.render_map(gmap, downloader=downloader_instance)

        image = base_image.copy()
        draw = PILImageDrawModule.Draw(image)

        # Das 'image'-Objekt wird nun mit übergeben, um die vorbereiteten Icons aufzubringen
        track_time = self._draw_path(gmap=gmap, image=image, draw=draw, trackroutes=tracks, color=self.ct)
        route_time = self._draw_path(gmap=gmap, image=image, draw=draw, trackroutes=routes, color=self.cr)
        trackroute_time = track_time or route_time

        image = image.convert("RGB")
        image.save(jpg_file, "JPEG", quality=95)

        exif_processor = EExiv2(jpg_file, verbose=self.verbose)
        tz = exif_processor.geolocator.get_tzinfo(latitude=first_lat, longitude=first_lon)

        exif_processor.write_exif(
            creation_date=trackroute_time,
            creation_author=self.user,
            nearest_point=GeoPointTime(latitude=first_lat, longitude=first_lon, elevation=None, timestamp=trackroute_time, tz=TZ_UTC),
            target_tz=tz,
        )

        if self.clean:
            with suppress(FileNotFoundError):
                Path(jpg_file + "~").unlink(missing_ok=True)

        return True


# ================================================================================
# ================================================================================
class GGPXMapProcessor:
    """Koordiniert den gesamten Prozess des Ladens von GPX-Daten und der Generierung von."""

    # --------------------------------------------------------------------------------
    def __init__(self, path: Path, params: GoProParameters):
        """Initialisiert den Prozessor und lädt die Konfiguration.
        
        :param path: (Path) Beschreibung
        :param params: (AppParameters) Die injizierte Instanz der App-Konfiguration.
        """
        # Parameter auswerten und in Attribute speichern
        self.clean = params.clean
        self.verbose = params.verbose
        self.map_size = params.mapsize
        self.color_track = params.color_track
        self.color_route = params.color_route
        self.ending_point = params.endingpoint
        self.generate_html = params.generatehtml

        self.diff_time = params.diff_time
        self.diff_dist = params.diff_dist
        self.user = params.user
        self.cache = not params.no_cache

        ggpx = GGPX(path=path, diff_time=self.diff_time, diff_dist=self.diff_dist, verbose=self.verbose)
        self.tracks: dict[Path, list[GPXTrackInfo]] = ggpx.tracks
        self.routes: dict[Path, list[GPXTrackInfo]] = ggpx.routes
        self.track_routes = self.tracks | self.routes

    # --------------------------------------------------------------------------------
    def process_gpx_jpeg(self) -> bool:
        """Führt den gesamten Prozess der Kartengenerierung durch.
        
        :return: (bool) Beschreibung des Rückgabewerts.
        """

        # 1. Generatoren initialisieren
        # Die Erstellung der Generatoren erfolgt hier, um sicherzustellen, dass sie die aktuellen Parameter verwenden.

        # Generierung der Rasterkarte (JPG)
        jpg_generator = GpxMapGeneratorJPG(self.tracks,
                                           self.routes,
                                           ct=self.color_track,
                                           cr=self.color_route,
                                           ending_point=self.ending_point,
                                           map_size=self.map_size,
                                           user=self.user,
                                           cache=self.cache,
                                           clean=self.clean,
                                           verbose=self.verbose)

        # 2. Karten generieren (Gesamtansicht, Einzelansicht)
        # Rasterkarte (JPG)
        if jpg_generator:
            jpg_generator.generate()
            return True

        return False

    # --------------------------------------------------------------------------------
    def process_gpx_html(self) -> bool:
        """Führt den gesamten Prozess der Kartengenerierung durch.
        
        :return: (bool) Beschreibung des Rückgabewerts.
        """

        # 1. Generatoren initialisieren
        # Die Erstellung der Generatoren erfolgt hier, um sicherzustellen, dass sie die aktuellen Parameter verwenden.

        # Generierung der HTML-Karte (Folium)
        html_generator = GpxMapGeneratorHtml(self.tracks,
                                             self.routes,
                                             ct=self.color_track,
                                             cr=self.color_route,
                                             ending_point=self.ending_point,
                                             map_size=self.map_size,
                                             verbose=self.verbose)

        # 2. Karten generieren (Gesamtansicht, Einzelansicht)
        # HTML-Karte (Folium) (Gesamtansicht, Einzelansicht)
        if html_generator:
            html_generator.generate()
            return True

        return False
