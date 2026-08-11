#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : gui_gopro2file_const.py
#  Version           : 2.0
#  Beschreibung      : Zentrale Konstanten für die GoPro-GUI.
#  Zeilen            : 38
#  Abhängigkeiten    : pathlib, typing
#  Klassen           : AppConfig
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

"""
Zentrale Konstanten für die GoPro-GUI.
"""
from pathlib import Path
from typing import Final
from rpg_utils.utils_config import BaseConfig


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
