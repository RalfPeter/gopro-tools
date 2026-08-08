#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 06-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/tracktraffic.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Program : gui_gopro2file_const.py (main - GoPro Videos and Telemetry Export)
#  Version : 1.0
# ------------------------------------------------------------------------------
#  Klassen:
#     AppConfig
#  Public Methods:
#    keine
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter61@email.de>
# ------------------------------------------------------------------------------

"""
Zentrale Konstanten für die GoPro-GUI.
"""
from pathlib import Path
from typing import Final
from utils_config import BaseConfig


# ================================================================================
# ================================================================================
class AppConfig:
    """
    Allgemeine Anwendungs-Metadaten und -Identifikatoren.
    """
    # -- Konstanten -------------------------------------------------------------
    TITLE: Final[str] = "GoPro Extraction"
    COMPANY: Final[str] = "WalMore"
    VERSION: Final[str] = "1.0"
    WIN_APP_VERSION: Final[str] = "2.1"
    NAME: Final[str] = BaseConfig.get_app_name()

    TITLE_GENERAL_SETTINGS: Final[str] = "Allgemeine Optionen"
    TITLE_GPX_SETTINGS: Final[str] = "GPX-Filter & Optionen"
    TITLE_OUTPUT_FORMATS: Final[str] = "Ausgabeformate & Export"
    TITLE_THUMB_MAP_SETTINGS: Final[str] = "Generierungs- & Karten-Optionen"
    TITLE_VIDEO_RENAMING: Final[str] = "Video Umbenennung"

    # Zentrale Pfade zu Konfigurations-, UI- und Icon-Dateien.
    UI_FILE: Final[Path] = BaseConfig.UI_DIR / f"{NAME}.ui"

    UI_GENERAL_SETTINGS: Final[Path] = BaseConfig.UI_DIR / f"{NAME}_general_settings.ui"
    UI_GPX_SETTINGS: Final[Path] = BaseConfig.UI_DIR / f"{NAME}_gpx_settings.ui"
    UI_OUTPUT_FORMATS: Final[Path] = BaseConfig.UI_DIR / f"{NAME}_output_format_settings.ui"
    UI_THUMB_MAP_SETTINGS: Final[Path] = BaseConfig.UI_DIR / f"{NAME}_thumbnail_map_settings.ui"
    UI_VIDEO_RENAMING: Final[Path] = BaseConfig.UI_DIR / f"{NAME}_video_renaming_settings.ui"

    # Texte und Filter für die QFileDialoge.
    CAPTION_FOLDER: Final[str] = "Ordner auswählen"
