#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : gui_gopro2file_dialogs.py
#  Version           : 2.0
#  Beschreibung      : Keine Beschreibung verfügbar.
#  Zeilen            : 420
#  Abhängigkeiten    : pathlib
#  Klassen           : GeneralSettingsDialog, GpxSettingsDialog, OutputFormatsDialog, ThumbnailMapSettingsDialog
#                     VideoRenamingDialog
# ------------------------------------------------------------------------------
#  Public Methoden:
#    GeneralSettingsDialog                                → Dialog für allgemeine System-, Anwendungs- und Geokodierungs-Optionen.
#      get_ui_file_path()                                 → Keine Beschreibung.
#      get_ui_data()                                      → Keine Beschreibung.
#      set_ui_data(bytes)                                 → Keine Beschreibung.
#      get_window_title()                                 → Keine Beschreibung.
#      set_options(GoProParameters)                       → Keine Beschreibung.
#      update_options(GoProParameters)                    → Keine Beschreibung.
#
#    GpxSettingsDialog                                    → Dialog für GPS-Schwellenwerte, Filter und GPX-Zusatzdaten.
#      get_ui_file_path()                                 → Keine Beschreibung.
#      get_ui_data()                                      → Keine Beschreibung.
#      set_ui_data(bytes)                                 → Keine Beschreibung.
#      get_window_title()                                 → Keine Beschreibung.
#      set_options(GoProParameters)                       → Keine Beschreibung.
#      update_options(GoProParameters)                    → Keine Beschreibung.
#
#    OutputFormatsDialog                                  → Dialog für Daten-Exporte, Ausgabeformate und Archivierungseinstellungen.
#      get_ui_file_path()                                 → Keine Beschreibung.
#      get_ui_data()                                      → Keine Beschreibung.
#      set_ui_data(bytes)                                 → Keine Beschreibung.
#      get_window_title()                                 → Keine Beschreibung.
#      set_options(GoProParameters)                       → Keine Beschreibung.
#      update_options(GoProParameters)                    → Keine Beschreibung.
#
#    ThumbnailMapSettingsDialog                           → Dialog für Vorschaubilder, Kartengenerierung, Abmessungen und Styling.
#      get_ui_file_path()                                 → Keine Beschreibung.
#      get_ui_data()                                      → Keine Beschreibung.
#      set_ui_data(bytes)                                 → Keine Beschreibung.
#      get_window_title()                                 → Keine Beschreibung.
#      set_options(GoProParameters)                       → Keine Beschreibung.
#      update_options(GoProParameters)                    → Keine Beschreibung.
#
#    VideoRenamingDialog                                  → Dialog für Konfigurationen zur automatischen GoPro-Videoumbenennung.
#      get_ui_file_path()                                 → Keine Beschreibung.
#      get_ui_data()                                      → Keine Beschreibung.
#      set_ui_data(bytes)                                 → Keine Beschreibung.
#      get_window_title()                                 → Keine Beschreibung.
#      set_options(GoProParameters)                       → Keine Beschreibung.
#      update_options(GoProParameters)                    → Keine Beschreibung.
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

from pathlib import Path

from rpg_gui import ColorButton, AbstractBaseOptionsDialog
from gui_gopro2file_const import AppConfig
from prg_gopro2file_config import GoProParameters


# ================================================================================
# ================================================================================
class GeneralSettingsDialog(AbstractBaseOptionsDialog):
    """Dialog für allgemeine System-, Anwendungs- und Geokodierungs-Optionen."""

    _ui_data: bytes | None = None

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_file_path(cls) -> Path:
        """Kurzbeschreibung für get_ui_file_path.
        
        :return: (Path) Beschreibung des Rückgabewerts.
        """

        return AppConfig.UI_GENERAL_SETTINGS

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_data(cls) -> bytes | None:
        """Kurzbeschreibung für get_ui_data.
        
        :return: (bytes | None) Beschreibung des Rückgabewerts.
        """

        return cls._ui_data

    # --------------------------------------------------------------------------------
    @classmethod
    def set_ui_data(cls, data: bytes) -> None:
        """Kurzbeschreibung für set_ui_data.
        
        :param data: (bytes) Beschreibung von data.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        cls._ui_data = data

    # --------------------------------------------------------------------------------
    def get_window_title(self) -> str:
        """Kurzbeschreibung für get_window_title.
        
        :return: (str) Beschreibung des Rückgabewerts.
        """

        return AppConfig.TITLE_GENERAL_SETTINGS

    # --------------------------------------------------------------------------------
    def set_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für set_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.ui.chkbx_recursive.setChecked(params.recursive)
        self.ui.chkbx_clean.setChecked(params.clean)
        self.ui.chkbx_nocache.setChecked(params.no_cache)
        self.ui.chkbx_verbose.setChecked(params.verbose)
        self.ui.chkbx_log.setChecked(params.log)
        self.ui.chkbx_goproonly.setChecked(params.goproonly)
        self.ui.chkbx_binary.setChecked(params.binary)
        self.ui.chkbx_geo.setChecked(params.geo)
        self.ui.chkbx_geoonly.setChecked(params.geoonly)
        self.ui.chkbx_geonamesupdate.setChecked(params.geonamesupdate)
        self.ui.spin_keyintervall.setValue(params.geonamesintervall)

    # --------------------------------------------------------------------------------
    def update_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für update_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        params.recursive = self.ui.chkbx_recursive.isChecked()
        params.clean = self.ui.chkbx_clean.isChecked()
        params.no_cache = self.ui.chkbx_nocache.isChecked()
        params.verbose = self.ui.chkbx_verbose.isChecked()
        params.log = self.ui.chkbx_log.isChecked()
        params.goproonly = self.ui.chkbx_goproonly.isChecked()
        params.binary = self.ui.chkbx_binary.isChecked()
        params.geo = self.ui.chkbx_geo.isChecked()
        params.geoonly = self.ui.chkbx_geoonly.isChecked()
        params.geonamesupdate = self.ui.chkbx_geonamesupdate.isChecked()
        params.geonamesintervall = self.ui.spin_keyintervall.value()


# ================================================================================
# ================================================================================
class GpxSettingsDialog(AbstractBaseOptionsDialog):
    """Dialog für GPS-Schwellenwerte, Filter und GPX-Zusatzdaten."""

    _ui_data: bytes | None = None

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_file_path(cls) -> Path:
        """Kurzbeschreibung für get_ui_file_path.
        
        :return: (Path) Beschreibung des Rückgabewerts.
        """

        return AppConfig.UI_GPX_SETTINGS

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_data(cls) -> bytes | None:
        """Kurzbeschreibung für get_ui_data.
        
        :return: (bytes | None) Beschreibung des Rückgabewerts.
        """

        return cls._ui_data

    # --------------------------------------------------------------------------------
    @classmethod
    def set_ui_data(cls, data: bytes) -> None:
        """Kurzbeschreibung für set_ui_data.
        
        :param data: (bytes) Beschreibung von data.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        cls._ui_data = data

    # --------------------------------------------------------------------------------
    def get_window_title(self) -> str:
        """Kurzbeschreibung für get_window_title.
        
        :return: (str) Beschreibung des Rückgabewerts.
        """

        return AppConfig.TITLE_GPX_SETTINGS

    # --------------------------------------------------------------------------------
    def set_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für set_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.ui.spin_diff_time.setValue(params.diff_time)
        self.ui.spin_diff_dist.setValue(params.diff_dist)
        self.ui.chkbx_locked.setChecked(params.locked)
        self.ui.chkbx_gpsdescription.setChecked(params.gpsdescription)

    # --------------------------------------------------------------------------------
    def update_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für update_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        params.diff_time = self.ui.spin_diff_time.value()
        params.diff_dist = self.ui.spin_diff_dist.value()
        params.locked = self.ui.chkbx_locked.isChecked()
        params.gpsdescription = self.ui.chkbx_gpsdescription.isChecked()


# ================================================================================
# ================================================================================
class OutputFormatsDialog(AbstractBaseOptionsDialog):
    """Dialog für Daten-Exporte, Ausgabeformate und Archivierungseinstellungen."""

    _ui_data: bytes | None = None

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_file_path(cls) -> Path:
        """Kurzbeschreibung für get_ui_file_path.
        
        :return: (Path) Beschreibung des Rückgabewerts.
        """

        return AppConfig.UI_OUTPUT_FORMATS

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_data(cls) -> bytes | None:
        """Kurzbeschreibung für get_ui_data.
        
        :return: (bytes | None) Beschreibung des Rückgabewerts.
        """

        return cls._ui_data

    # --------------------------------------------------------------------------------
    @classmethod
    def set_ui_data(cls, data: bytes) -> None:
        """Kurzbeschreibung für set_ui_data.
        
        :param data: (bytes) Beschreibung von data.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        cls._ui_data = data

    # --------------------------------------------------------------------------------
    def get_window_title(self) -> str:
        """Kurzbeschreibung für get_window_title.
        
        :return: (str) Beschreibung des Rückgabewerts.
        """

        return AppConfig.TITLE_OUTPUT_FORMATS

    # --------------------------------------------------------------------------------
    def set_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für set_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.ui.chkbx_file_all.setChecked(params.file_all)
        self.ui.chkbx_file_virb.setChecked(params.file_virb)
        self.ui.chkbx_file_bin.setChecked(params.file_bin)
        self.ui.chkbx_file_json.setChecked(params.file_json)
        self.ui.chkbx_file_kml.setChecked(params.file_kml)
        self.ui.chkbx_file_csv_hex.setChecked(params.file_csv_hex)
        self.ui.chkbx_file_gpx.setChecked(params.file_gpx)
        self.ui.chkbx_file_csv_gyr.setChecked(params.file_csv_gyr)
        self.ui.chkbx_file_csv_acc.setChecked(params.file_csv_acc)
        self.ui.chkbx_file_csv_gps.setChecked(params.file_csv_gps)
        self.ui.chkbx_zip.setChecked(params.zip)
        self.ui.chkbx_zip_delete.setChecked(params.zip_delete)

    # --------------------------------------------------------------------------------
    def update_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für update_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        params.file_all = self.ui.chkbx_file_all.isChecked()
        params.file_virb = self.ui.chkbx_file_virb.isChecked()
        params.file_bin = self.ui.chkbx_file_bin.isChecked()
        params.file_json = self.ui.chkbx_file_json.isChecked()
        params.file_kml = self.ui.chkbx_file_kml.isChecked()
        params.file_csv_hex = self.ui.chkbx_file_csv_hex.isChecked()
        params.file_gpx = self.ui.chkbx_file_gpx.isChecked()
        params.file_csv_gyr = self.ui.chkbx_file_csv_gyr.isChecked()
        params.file_csv_acc = self.ui.chkbx_file_csv_acc.isChecked()
        params.file_csv_gps = self.ui.chkbx_file_csv_gps.isChecked()
        params.zip = self.ui.chkbx_zip.isChecked()
        params.zip_delete = self.ui.chkbx_zip_delete.isChecked()


# ================================================================================
# ================================================================================
class ThumbnailMapSettingsDialog(AbstractBaseOptionsDialog):
    """Dialog für Vorschaubilder, Kartengenerierung, Abmessungen und Styling."""

    _ui_data: bytes | None = None
    # Registrierung der dynamischen Custom-Widgets für die IDE
    colorbtn_track: ColorButton
    colorbtn_route: ColorButton

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_file_path(cls) -> Path:
        """Kurzbeschreibung für get_ui_file_path.
        
        :return: (Path) Beschreibung des Rückgabewerts.
        """

        return AppConfig.UI_THUMB_MAP_SETTINGS

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_data(cls) -> bytes | None:
        """Kurzbeschreibung für get_ui_data.
        
        :return: (bytes | None) Beschreibung des Rückgabewerts.
        """

        return cls._ui_data

    # --------------------------------------------------------------------------------
    @classmethod
    def set_ui_data(cls, data: bytes) -> None:
        """Kurzbeschreibung für set_ui_data.
        
        :param data: (bytes) Beschreibung von data.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        cls._ui_data = data

    # --------------------------------------------------------------------------------
    def get_window_title(self) -> str:
        """Kurzbeschreibung für get_window_title.
        
        :return: (str) Beschreibung des Rückgabewerts.
        """

        return AppConfig.TITLE_THUMB_MAP_SETTINGS

    # --------------------------------------------------------------------------------
    def set_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für set_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.ui.chkbx_thumb.setChecked(params.thumb)
        self.ui.chkbx_overwrite_thumb.setChecked(params.overwrite_thumb)
        self.ui.txt_delta.setText(str(params.delta))
        self.ui.chkbx_generatemap.setChecked(params.generatemap)
        self.ui.chkbx_generatehtml.setChecked(params.generatehtml)
        self.ui.spin_mapwidth.setValue(params.mapwidth)
        self.ui.spin_mapheight.setValue(params.mapheight)
        self.ui.chkbx_endingpoint.setChecked(params.endingpoint)
        # Colorbuttons haben eine eigene property
        self.ui.colorbtn_track.color = str(params.color_track)
        self.ui.colorbtn_route.color = str(params.color_route)

    # --------------------------------------------------------------------------------
    def update_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für update_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        params.thumb = self.ui.chkbx_thumb.isChecked()
        params.overwrite_thumb = self.ui.chkbx_overwrite_thumb.isChecked()
        params.delta = self.ui.txt_delta.text()
        params.generatemap = self.ui.chkbx_generatemap.isChecked()
        params.generatehtml = self.ui.chkbx_generatehtml.isChecked()
        params.mapwidth = self.ui.spin_mapwidth.value()
        params.mapheight = self.ui.spin_mapheight.value()
        params.endingpoint = self.ui.chkbx_endingpoint.isChecked()
        # Colorbuttons haben eine eigene property
        params.color_track = self.ui.colorbtn_track.color
        params.color_route = self.ui.colorbtn_route.color


# ================================================================================
# ================================================================================
class VideoRenamingDialog(AbstractBaseOptionsDialog):
    """Dialog für Konfigurationen zur automatischen GoPro-Videoumbenennung."""

    _ui_data: bytes | None = None

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_file_path(cls) -> Path:
        """Kurzbeschreibung für get_ui_file_path.
        
        :return: (Path) Beschreibung des Rückgabewerts.
        """

        return AppConfig.UI_VIDEO_RENAMING

    # --------------------------------------------------------------------------------
    @classmethod
    def get_ui_data(cls) -> bytes | None:
        """Kurzbeschreibung für get_ui_data.
        
        :return: (bytes | None) Beschreibung des Rückgabewerts.
        """

        return cls._ui_data

    # --------------------------------------------------------------------------------
    @classmethod
    def set_ui_data(cls, data: bytes) -> None:
        """Kurzbeschreibung für set_ui_data.
        
        :param data: (bytes) Beschreibung von data.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        cls._ui_data = data

    # --------------------------------------------------------------------------------
    def get_window_title(self) -> str:
        """Kurzbeschreibung für get_window_title.
        
        :return: (str) Beschreibung des Rückgabewerts.
        """

        return AppConfig.TITLE_VIDEO_RENAMING

    # --------------------------------------------------------------------------------
    def set_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für set_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.ui.txt_pattern.setText(params.pattern)
        self.ui.txt_user.setText(str(params.user))
        self.ui.chkbx_namesequence.setChecked(params.namesequence)

    # --------------------------------------------------------------------------------
    def update_options(self, params: GoProParameters) -> None:
        """Kurzbeschreibung für update_options.
        
        :param params: (GoProParameters) Beschreibung von params.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        params.pattern = self.ui.txt_pattern.text()
        params.user = self.ui.txt_user.text()
        params.namesequence = self.ui.chkbx_namesequence.isChecked()
