#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 06-08-2026
# Ralf Peter <ralfpeter61@email.de>
# https://github.com/RalfPeter/tracktraffic.git
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Program : gui_gopro2overlay_const.py (main - GoPro Videos and Telemetry Export)
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
