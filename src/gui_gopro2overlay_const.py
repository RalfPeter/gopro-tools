#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : gui_gopro2overlay_const.py
#  Version           : 2.0
#  Beschreibung      : Zentrale Konstanten für die GoPro-GUI.
#  Zeilen            : 28
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
    TITLE: Final[str] = "GoPro Overlay"
    COMPANY: Final[str] = "WalMore"
    VERSION: Final[str] = "1.0"
    WIN_APP_VERSION: Final[str] = "2.1"
    NAME: Final[str] = BaseConfig.get_app_name()

    # Zentrale Pfade zu Konfigurations-, UI- und Icon-Dateien.
    UI_FILE: Final[Path] = BaseConfig.UI_DIR / f"{NAME}.ui"

    # Texte und Filter für die QFileDialoge.
    CAPTION_FOLDER: Final[str] = "Ordner auswählen"
    CAPTION_LAYOUT: Final[str] = "Layout auswählen"
    FILTER_LAYOUT: Final[str] = "XML Dateien (*.xml)"
