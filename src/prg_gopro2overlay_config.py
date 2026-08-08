#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 04-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/tracktraffic.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Program : prg_gopro2overlay_config.py (main - GoPro Videos and Telemetry Export)
#  Version : 1.0
# ------------------------------------------------------------------------------
#  Klassen:
#     OverlayParameters
#  Public Methods:
#     OverlayParameters.parse_args()      → Parst die Kommandozeilenparameter speziell für das Overlay-Tool.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter61@email.de>
# ------------------------------------------------------------------------------

from __future__ import annotations
from typing import final, Any, ClassVar
from argparse import ArgumentParser
from dataclasses import dataclass, fields, field
from pathlib import Path

from utils_config import BaseParameters


# ================================================================================
# ================================================================================
@final
@dataclass
class OverlayParameters(BaseParameters):
    """Zentrales Datenobjekt für alle Laufzeitparameter des MP4-Overlay-Gadgets.

    Bietet ein maßgeschneidertes Subset an Parametern, das exakt auf das
    Rendern von GPS-Metadaten-Overlays auf Videos via FFmpeg abgestimmt ist.
    """
    # inputfiles usw. werden von der Persistierung ausgeschlossen
    EXCLUDED_PERSISTENCE_FIELDS: ClassVar[set[str]] = {
        "inputfiles",
    }

    # ==========================================================================
    # Allgemeine Parameter (verbose und log kommen aus BaseParameters)
    # ==========================================================================
    recursive: bool = False
    clean: bool = True

    # ==========================================================================
    # Render (FFmpeg / Font) Parameter
    # ==========================================================================
    font: str = "Roboto-Regular.ttf"
    profile: str | None = None
    ffmpeg_dir: str | None = None
    show_ffmpeg: bool = False

    # ==========================================================================
    # GPS Daten-Validierungs Parameter
    # ==========================================================================
    gps_dop_max: float = 10.0
    gps_speed_max: float = 250.0
    gps_speed_max_units: str = "kph"

    # ==========================================================================
    # Anzeige-Einheiten (Units) Parameter
    # ==========================================================================
    units_speed: str = "kph"
    units_altitude: str = "meter"
    units_distance: str = "meter"
    units_temperature: str = "degC"

    # ==========================================================================
    # Layout Parameter
    # ==========================================================================
    layout: str = "xml"
    layout_xml: str = "default.xml"
    exclude: list[str] | None = None
    include: list[str] | None = None

    # ==========================================================================
    # Datei, Pfad & GUI-Zustands-Parameter
    # ==========================================================================
    inputpaths: list[str] | None = None
    inputfiles: list[str] | None = None
    selected_folder: str = field(default='', init=False)

    # --------------------------------------------------------------------------------
    def __post_init__(self) -> None:
        """Initialisiert Listen-Defaults sicher nach der Dataclass-Instanziierung."""
        # nutzen wir standardmäßig das aktuelle Verzeichnis
        if not self.inputpaths:
            self.inputpaths = ['./']

    # --------------------------------------------------------------------------------
    def parse_args(self) -> OverlayParameters:
        """Parst die Kommandozeilenparameter speziell für das Overlay-Tool.

        Aktualisiert die Instanz direkt und gibt sie für Method-Chaining zurück.

        :return: Das aktualisierte Instanzobjekt (Self).
        :rtype: OverlayParameters
        """
        # F stellt alle Feldnamen als Attribute bereit (z. B. F.clean -> "clean")
        F = self.Fields
        class_defaults: dict[str, Any] = {f.name: f.default for f in fields(self)}
        parser = ArgumentParser(description="Overlay gadgets on MP4")

        # 1. Argumente der geerbten Basisklasse BaseParameters
        parser.add_argument("-v", f"--{F.verbose}", action="store_true", default=class_defaults[F.verbose], help="Erhöht die Detailstufe der Log-Ausgabe")
        parser.add_argument("-l", f"--{F.log}", action="store_true", default=class_defaults[F.log], help="Aktiviert das Logging in eine Datei")

        # 2. Allgemeine Argumente der Subklasse
        parser.add_argument("-r", f"--{F.recursive}", help="Recursive find all files by pattern in inputfiles", action="store_true", default=class_defaults[F.recursive])
        parser.add_argument("-c", f"--{F.clean}", help="Clean directory and delete all temp files", action="store_true", default=class_defaults[F.clean])

        # 3. Gruppe: Rendering Performance
        render = parser.add_argument_group("Render", "Controlling rendering performance")
        render.add_argument(f"--{F.font}", help="Selects a font", default=class_defaults[F.font])
        render.add_argument(f"--{F.profile}", help="Use ffmpeg options profile <name> from ~/gopro-graphics/ffmpeg-profiles.json", default=class_defaults[F.profile])
        render.add_argument(f"--{F.ffmpeg_dir}", type=Path, help="Directory where ffmpeg/ffprobe located, default=Look in PATH", default=class_defaults[F.ffmpeg_dir])
        render.add_argument(f"--{F.show_ffmpeg}", action="store_true", help="Show FFMPEG output (not usually useful)", default=class_defaults[F.show_ffmpeg])

        # 4. Gruppe: GPS Parsing
        gps = parser.add_argument_group("GPS", "Controlling GPS Parsing (from GoPro Only)")
        gps.add_argument(f"--{F.gps_dop_max}", type=float, default=class_defaults[F.gps_dop_max], help="Max DOP - Points with greater DOP will be considered 'Not Locked'")
        gps.add_argument(f"--{F.gps_speed_max}", type=float, default=class_defaults[F.gps_speed_max], help="Max GPS Speed - Points with greater speed will be considered 'Not Locked'")
        gps.add_argument(f"--{F.gps_speed_max_units}", default=class_defaults[F.gps_speed_max_units], help="Units for --gps-speed-max")

        # 5. Gruppe: Einheiten (Units)
        units = parser.add_argument_group("Units", "Controlling Units")
        units.add_argument(f"--{F.units_speed}", default=class_defaults[F.units_speed], help="Default unit for speed. Many units supported: mph, mps, kph, knot, ...")
        units.add_argument(f"--{F.units_altitude}", default=class_defaults[F.units_altitude], help="Default unit for altitude. Many units supported: foot, mile, metre, meter, parsec, angstrom, ...")
        units.add_argument(f"--{F.units_distance}", default=class_defaults[F.units_distance], help="Default unit for distance. Many units supported: mile, km, foot, nmi, meter, metre, parsec, ...")
        units.add_argument(f"--{F.units_temperature}", default=class_defaults[F.units_temperature], choices=["kelvin", "degC", "degF"], help="Default unit for temperature")

        # 6. Gruppe: Layout
        layout = parser.add_argument_group("Layout", "Controlling layout")
        layout.add_argument(f"--{F.layout}", choices=["default", "speed-awareness", "xml"], default=class_defaults[F.layout], help="Choose graphics layout")
        layout.add_argument(f"--{F.layout_xml}", type=Path, help="Use XML File for layout", default=class_defaults[F.layout_xml])
        layout.add_argument(f"--{F.exclude}", nargs="+", help="exclude named component (will include all others)", default=class_defaults[F.exclude])
        layout.add_argument(f"--{F.include}", nargs="+", help="include named component (will exclude all others)", default=class_defaults[F.include])

        # 7. Positions-Argument für Eingabepfade
        fn_raw = F.inputpaths
        parser.add_argument(fn_raw, help="Path with video files or binary metadata dumps", nargs='*')

        # Parsen der CLI-Argumente
        l_args, _ = parser.parse_known_args()

        # Korrektur des Typs/Namens des Positions-Arguments im Namespace
        if hasattr(l_args, fn_raw):
            setattr(l_args, F.inputpaths, getattr(l_args, fn_raw))

        # Übergabe an das dynamische Mapping der Basisklasse
        self.update_from_namespace(l_args)
        return self
