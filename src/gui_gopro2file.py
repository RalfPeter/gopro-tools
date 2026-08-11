#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : gui_gopro2file.py
#  Version           : 3.0
#  Beschreibung      : Logfile initialisieren und Callback einrichten
#  Zeilen            : 573
#  Abhängigkeiten    : PySide6, asyncio, datetime, gc, nest_asyncio, os, pathlib, sys, traceback, typing
#  Eigene Frameworks : rpg_geo, rpg_gpmf, rpg_gpx, rpg_gui, rpg_utils
#  Klassen           : MainWindow, Worker
# ------------------------------------------------------------------------------
#  Public Methoden:
#    MainWindow                                           → Hauptfenster der Anwendung
#      init_ui()                                          → Verbindet Signale und setzt initiale Widget-Zustände.
#      close_action()                                     → Kurzbeschreibung für close_action.
#      on_action_general_settings_triggered()             → Wird automatisch aufgerufen, wenn 'action_general_settings' ausgelöst wird.
#      on_action_gpx_settings_triggered()                 → Wird automatisch aufgerufen, wenn 'action_gpx_settings' ausgelöst wird.
#      on_action_outputformat_settings_triggered()        → Wird automatisch aufgerufen, wenn 'action_output_formats' ausgelöst wird.
#      on_action_thumbnailmaps_settings_triggered()       → Wird automatisch aufgerufen, wenn 'action_thumbnail_map_settings' ausgelöst wird.
#      on_action_videorenaming_settings_triggered()       → Wird automatisch aufgerufen, wenn 'action_video_renaming' ausgelöst wird.
#      save_settings()                                    → Speichert die Fensterposition, Fenstergröße und UI-Einstellungen im zentralen YAML-Objekt.
#      load_settings()                                    → Lädt die GUI-Einstellungen aus dem zentralen YAML-Objekt und stellt sie wieder her.
#      select_folder()                                    → Öffnet einen angepassten Ordnerdialog mit Dateivorschau.
#      fill_folder(str)                                   → Kurzbeschreibung für fill_folder.
#      execute_action()                                   → Deaktiviere den Button, solange der Thread läuft
#      on_progress_signal_received(ProgressEvent)         → Zugriff ist jetzt direkt und intuitiv
#      on_process_finished_received()                     → Gebe den Beendigungstext aus
#      on_log_signal_received(str)                        → Kurzbeschreibung für on_log_signal_received.
#
#    Worker                                               → process_finished = Signal()       # Signal, wenn alle Prozesse abgeschlossen sind
#      run()                                              → Extrahiert alle Metadaten der GoPro-Videos alle Videos des Ordner.
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    main(bool)                                           → Logfile initialisieren und Callback einrichten
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

import sys
import asyncio
import nest_asyncio
import os
import gc
import traceback
from typing import cast, Any
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, Slot, QThread, Signal, QMetaObject, QTranslator, QLibraryInfo, QLocale
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QTextEdit, QFileDialog, QProgressBar, QDialog,
                               QTreeWidget, QTreeWidgetItem, QHeaderView)

from rpg_utils import setup_crash_logger, log_to_callback, AppLogger, CallbackTag as Tag, ProgressEvent, ProgressType, TRENNER, fatal, initialize_windows_app_id
from rpg_utils import PathUtils
from rpg_gpmf import VIDEO_EXTENSIONS, NoVideoError, GoProFile, NoGoProError
from rpg_gui import ErrorHandler, BaseMainWindow, BaseWorker

from gui_gopro2file_const import AppConfig
from prg_gopro2file_config import GoProParameters
from gui_gopro2file_dialogs import GeneralSettingsDialog, GpxSettingsDialog, OutputFormatsDialog, ThumbnailMapSettingsDialog, VideoRenamingDialog
from prg_gopro2file import main as gopro2file_main

# Erlaubt verschachtelte asyncio-Event-Loops (verhindert RuntimeError bei Bibliotheken mit eigenen Loops)
nest_asyncio.apply()


# ================================================================================
# -- Main-Window -----------------------------------------------------------------
# ================================================================================
class MainWindow(BaseMainWindow):
    """Hauptfenster der Anwendung"""

    # Definition der Signale auf Klassenebene
    log_signal = Signal(str)
    progress_signal = Signal(ProgressEvent)

    # --------------------------------------------------------------------------------
    def __init__(self, ui_file: Path, logger: AppLogger, appp: GoProParameters, verbose: bool = False, parent: QWidget | None = None):
        """Kurzbeschreibung für __init__.
        
        :param ui_file: (Path) Beschreibung von ui_file.
        :param logger: (AppLogger) Beschreibung von logger.
        :param appp: (GoProParameters) Beschreibung von appp.
        :param verbose: (bool) Beschreibung von verbose.
        :param parent: (QWidget | None) Beschreibung von parent.
        """

        super().__init__(parent=parent, ui_file=ui_file, appp=appp, logger=logger, title=AppConfig.TITLE, verbose=verbose)

        if self.ui is None:
            fatal(msg="UI konnte nicht geladen werden", exitcode=999)
            raise

        self.selected_folder: str = ''
        self.worker: Worker | None = None

        # Referenzierung der UI-Elemente
        self.folderlabel_label = cast(QLabel, self.ui.findChild(QLabel, "folderlabel_label"))  # UI-Element referenzieren - folderlabel_label
        self.folder_label = cast(QLabel, self.ui.findChild(QLabel, "folder_label"))  # UI-Element referenzieren - folder_label
        self.folderselect_button = cast(QPushButton, self.ui.findChild(QPushButton, "folderselect_button"))  # UI-Element referenzieren - folderselect_button
        self.video_list = cast(QTreeWidget, self.ui.findChild(QTreeWidget, "video_list"))  # UI-Element referenzieren - video_list
        self.output_text = cast(QTextEdit, self.ui.findChild(QTextEdit, "output_text"))  # UI-Element referenzieren - output_text
        self.overlay_progressbar = cast(QProgressBar, self.ui.findChild(QProgressBar, "overlay_progressbar"))  # UI-Element referenzieren - overlay_progressbar
        self.quit_button = cast(QPushButton, self.ui.findChild(QPushButton, "quit_button"))  # UI-Element referenzieren - quit_button
        self.execute_button = cast(QPushButton, self.ui.findChild(QPushButton, "execute_button"))  # UI-Element referenzieren - execute_button

        # NEU: Erstellung des Optionen-Dialogs als eigenständiges Objekt
        self.options_general: GeneralSettingsDialog = GeneralSettingsDialog(self, verbose=self.verbose)
        self.options_gpx: GpxSettingsDialog = GpxSettingsDialog(self, verbose=self.verbose)
        self.options_output: OutputFormatsDialog = OutputFormatsDialog(self, verbose=self.verbose)
        self.options_thumbnail_map: ThumbnailMapSettingsDialog = ThumbnailMapSettingsDialog(self, verbose=self.verbose)
        self.options_videorenaiming: VideoRenamingDialog = VideoRenamingDialog(self, verbose=self.verbose)

        self.init_ui()
        self.load_settings()

    # --------------------------------------------------------------------------------
    def init_ui(self):
        """Verbindet Signale und setzt initiale Widget-Zustände."""
        # 1. Verbinde die Signale mit den Methoden
        self.log_signal.connect(self.on_log_signal_received)
        self.progress_signal.connect(self.on_progress_signal_received)

        # 2. ÜBERGEBE DAS EMIT-METHODEN-OBJEKT
        # Das ist sicher, weil .emit() eine von Qt verwaltete Callable ist,
        # die keine direkte Referenz auf das Objekt-Lebenszyklus-Problem hält.
        self.logger.gui_callback = self.log_signal.emit
        self.logger.progress_callback = self.progress_signal.emit

        # Ordner-Auswahl-Button
        self.folderselect_button.clicked.connect(self.select_folder)
        # Layout für die Video-Liste
        self.video_list.setHeaderLabels(["Name", "Größe", "Änderungsdatum"])
        self.video_list.setRootIsDecorated(False)  # Keine Einrückung/Pfeile wie bei Baumstrukturen
        # Spaltenbreiten automatisch anpassen
        header = self.video_list.header()
        if header is not None:
            # 1. Spalte 1 (Größe) und Spalte 2 (Datum) auf Inhaltsbreite festlegen
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            # 2. Spalte 0 (Name) nimmt den gesamten restlichen Platz dynamisch ein
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            # Optional: Verhindert, dass der Anwender die Inhaltsspalten manuell verschiebt/verzerrt
            header.setStretchLastSection(False)
        # Textfeld für die Ausgabe
        self.output_text.setReadOnly(True)  # Ausgabe soll nur lesbar sein
        # Progressbar einfügen
        self.overlay_progressbar.setValue(0)
        self.overlay_progressbar.setMinimum(0)
        self.overlay_progressbar.setMaximum(100)
        # Buttons für Aktionen
        self.execute_button.setEnabled(True)  # Der Button ist standardmäßig deaktiviert
        self.execute_button.clicked.connect(self.execute_action)
        self.quit_button.clicked.connect(self.on_quit_button_clicked)

        # Menü verbinden, am Ende der UI-Initialisierung den Qt-Automatismus starten:
        QMetaObject.connectSlotsByName(self)

    # --------------------------------------------------------------------------------
    def close_action(self):
        """Kurzbeschreibung für close_action."""

        self.worker = None
        super().close_action()

    # --------------------------------------------------------------------------------
    @Slot()
    def on_action_general_settings_triggered(self) -> None:
        """Wird automatisch aufgerufen, wenn 'action_general_settings' ausgelöst wird.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self._show_generic_dialog(self.options_general, "Allgemeine Optionen übernommen.")

    # --------------------------------------------------------------------------------
    @Slot()
    def on_action_gpx_settings_triggered(self) -> None:
        """Wird automatisch aufgerufen, wenn 'action_gpx_settings' ausgelöst wird.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self._show_generic_dialog(self.options_gpx, "GPX-Filter-Optionen übernommen.")

    # --------------------------------------------------------------------------------
    @Slot()
    def on_action_outputformat_settings_triggered(self) -> None:
        """Wird automatisch aufgerufen, wenn 'action_output_formats' ausgelöst wird.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self._show_generic_dialog(self.options_output, "Ausgabeformate übernommen.")

    # --------------------------------------------------------------------------------
    @Slot()
    def on_action_thumbnailmaps_settings_triggered(self) -> None:
        """Wird automatisch aufgerufen, wenn 'action_thumbnail_map_settings' ausgelöst wird.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self._show_generic_dialog(self.options_thumbnail_map, "Karten- & Thumbnail-Optionen übernommen.")

    # --------------------------------------------------------------------------------
    @Slot()
    def on_action_videorenaming_settings_triggered(self) -> None:
        """Wird automatisch aufgerufen, wenn 'action_video_renaming' ausgelöst wird.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self._show_generic_dialog(self.options_videorenaiming, "Videoumbenennungs-Optionen übernommen.")

    # --------------------------------------------------------------------------------
    def _show_generic_dialog(self, dialog: Any, success_message: str) -> None:
        """Öffnet den übergebenen Dialog modal, befüllt ihn und speichert bei 'OK'.

        Nutzt die gemeinsamen Methoden der abstrakten Basisklasse.

        :param dialog: (AbstractBaseOptionsDialog) Die Instanz des anzuzeigenden Dialogs.
        :param success_message: (str) Die Nachricht, die nach erfolgreichem Speichern geloggt wird.
        """
        # 1. Daten an den Dialog übergeben (Spezifische Implementierung von set_options)
        dialog.set_options(self.appp)

        # 2. Dialog modal anzeigen und auf 'OK' (Accepted) prüfen
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 3. Geänderte Daten abholen
            dialog.update_options(self.appp)

            # 4. Rückmeldung im Log-Fenster und dauerhaftes Speichern
            self.append_output_text(self.output_text, success_message)

            self.save_settings()

    # --------------------------------------------------------------------------------
    def save_settings(self):
        """Speichert die Fensterposition, Fenstergröße und UI-Einstellungen im zentralen YAML-Objekt."""
        self.appp.selected_folder = self.selected_folder
        self.appp.inputpaths = [self.selected_folder]
        # Speichert die Fensterposition, Fenstergröße und UI-Einstellungen in einer Yaml-Konfigurationsdatei.
        super().save_settings()

    # --------------------------------------------------------------------------------
    def load_settings(self):
        """Lädt die GUI-Einstellungen aus dem zentralen YAML-Objekt und stellt sie wieder her."""
        super().load_settings()

        self.selected_folder = self.appp.selected_folder
        self.folder_label.setText(self.selected_folder)
        if self.selected_folder:
            if Path(self.selected_folder).is_dir():
                self.fill_folder(self.selected_folder)

    # --------------------------------------------------------------------------------
    def select_folder(self):
        """Öffnet einen angepassten Ordnerdialog mit Dateivorschau."""
        dialog = QFileDialog(self, AppConfig.CAPTION_FOLDER, self.selected_folder)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        # Optional: Nur Ordner und Videodateien anzeigen lassen
        ext_pattern = " ".join(f"*{ext}" for ext in VIDEO_EXTENSIONS)
        dialog.setNameFilter(f"Videodateien ({ext_pattern})")

        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self.fill_folder(selected_dirs[0])

    # --------------------------------------------------------------------------------
    def fill_folder(self, folder: str | None = None):
        """Kurzbeschreibung für fill_folder.
        
        :param folder: (str | None) Beschreibung von folder.
        """

        if folder:
            # Leere die Liste, bevor sie neu befüllt wird
            self.video_list.clear()
            self.selected_folder = folder
            self.folder_label.setText(f"{folder}")
            self.append_output_text(self.output_text, TRENNER)
            self.append_output_text(self.output_text, f"Ordner ausgewählt: {folder}")
            self.append_output_text(self.output_text, TRENNER)

            # Filtere nur Videodateien (hier als Beispiel .mp4 und .avi)
            videos = [f for f in os.listdir(folder) if f.casefold().endswith(VIDEO_EXTENSIONS)]

            # check if GoPro Video
            i = 0
            goprovideos = []

            for video in videos:
                i += 1
                # - Metadaten aus Video ------------------------------------------------------------------
                try:
                    GoProFile(folder + '/' + video, verbose=self.verbose, use_geocities=False)
                except NoGoProError as e:
                    if self.verbose:
                        self.append_output_text(self.output_text, f'Datei: {e.message}')
                    continue
                except NoVideoError as e:
                    if self.verbose:
                        self.append_output_text(self.output_text, f'Datei: {e.message}')
                    continue
                else:
                    goprovideos.append(video)
            videos = goprovideos

            # fill up the listview
            for video in videos:
                file_path = Path(folder) / video

                # Dateieigenschaften ermitteln
                stat = file_path.stat()

                # Größe formatieren (z. B. in MB)
                size_mb = f"{stat.st_size / (1024 * 1024):.2f} MB"

                # Datum formatieren
                mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                # QTreeWidgetItem mit allen 3 Spalten erzeugen
                item = QTreeWidgetItem([video, size_mb, mod_time])

                # Optional: Rechtsbündige Ausrichtung für Größe und Datum für sauberen Look
                item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                self.video_list.addTopLevelItem(item)

            self.appp.inputpaths = [folder]
            self.appp.inputfiles = videos
            self.execute_button.setEnabled(len(videos) > 0)
        else:
            self.appp.inputpaths = []
            self.appp.inputpaths.clear()
            self.appp.inputfiles = []
            self.appp.inputfiles.clear()

            self.folder_label.setText('')
            self.output_text.clear()

    # --------------------------------------------------------------------------------
    def execute_action(self):
        # Deaktiviere den Button, solange der Thread läuft
        """Deaktiviere den Button, solange der Thread läuft"""

        self.execute_button.setEnabled(False)
        self.output_text.clear()

        # Stelle sicher, dass vorheriger Thread gestoppt ist
        if self.thread is not None:
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()  # Warten, bis der Thread sicher gestoppt ist
            self.thread.deleteLater()
            self.thread = None

        # Erstelle den neuen Thread und Worker
        self.thread = QThread()
        self.worker = Worker(
            logger=self.logger,
            appp=self.appp,
            selected_folder=self.selected_folder,
            window=self,
            verbose=self.verbose
        )
        # Ein einziges assert sagt PyCharm: Für den Rest dieser Methode sind sie NICHT None.
        assert self.thread is not None
        assert self.worker is not None

        # Worker in den Kontext des Threads verschieben
        self.worker.moveToThread(self.thread)

        # ---------------------------------------------------------------------
        # 2. Die STANDARD-Signal-Kette (Genau diese 5 Zeilen, nicht mehr, nicht weniger)
        # ---------------------------------------------------------------------
        # A) Start: Wenn Thread startet -> führe worker.run aus
        self.thread.started.connect(self.worker.run)

        # B) GUI-Updates: Wenn der Worker fertig ist -> GUI informieren
        self.worker.process_finished.connect(self.on_process_finished_received)

        # C) Beenden-Kaskade: Wenn Worker fertig ist -> beende den Thread
        self.worker.process_finished.connect(self.thread.quit)

        # D) Speicher aufräumen: Wenn Thread beendet ist -> lösche Worker und Thread aus dem C++-Speicher
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._cleanup_thread_references)

        # ---------------------------------------------------------------------
        # 3. Thread starten
        # ---------------------------------------------------------------------
        self.thread.start()

    # --------------------------------------------------------------------------------
    @Slot(ProgressEvent)
    def on_progress_signal_received(self, event: ProgressEvent) -> None:
        # Zugriff ist jetzt direkt und intuitiv
        """Zugriff ist jetzt direkt und intuitiv
        
        :param event: (ProgressEvent) Beschreibung von event.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        match event.type:
            case ProgressType.START:
                self.overlay_progressbar.setRange(0, event.total)
                self.overlay_progressbar.setValue(0)

            case ProgressType.UPDATE:
                self.overlay_progressbar.setValue(event.current)

            case ProgressType.FINISHED:
                self.overlay_progressbar.setValue(event.total)

    # --------------------------------------------------------------------------------
    @Slot(str)
    def on_process_finished_received(self):
        """Gebe den Beendigungstext aus"""

        # Gebe den Beendigungstext aus
        self.append_output_text(self.output_text, TRENNER)
        self.append_output_text(self.output_text, "Alle Videos wurden erfolgreich bearbeitet!")
        # Aktiviere den Button wieder nach dem Abschluss der Arbeit
        self.execute_button.setEnabled(True)
        self.overlay_progressbar.setValue(0)  # Setze den Wert der Progressbar nach der Verarbeitung auf 0

        # Stoppe den Thread, wenn die Verarbeitung abgeschlossen ist ???
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
            self.thread = None

    # --------------------------------------------------------------------------------
    @Slot(str)
    def on_log_signal_received(self, message: str) -> None:
        """Kurzbeschreibung für on_log_signal_received.
        
        :param message: (str) Beschreibung von message.
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.append_output_text(self.output_text, message)

    # --------------------------------------------------------------------------------
    def _cleanup_thread_references(self) -> None:
        """Setzt die Thread- und Worker-Referenzen nach der Zerstörung auf None.

        :param self: (MainWindow) Instanz des Hauptfensters.
        :return: None
        """
        self.thread = None
        self.worker = None


# ================================================================================
# -- Worker-Thread ---------------------------------------------------------------
# ================================================================================
class Worker(BaseWorker):
    # process_finished = Signal()       # Signal, wenn alle Prozesse abgeschlossen sind
    # finished = Signal()

    # --------------------------------------------------------------------------------
    """process_finished = Signal()       # Signal, wenn alle Prozesse abgeschlossen sind"""

    def __init__(self,
                 logger: AppLogger,
                 appp: GoProParameters,
                 selected_folder: str | None = None,
                 window: MainWindow | None = None,
                 verbose: bool = False):
        """Initialisiert den Worker-Thread für die Video-Verarbeitung.

        :param logger: (AppLogger) Instanz, die für Pfad-Konfigurationen während der Laufzeit injiziert wird.
        :param selected_folder: (str | None) Der Basisordner der Videos.
        :param window: (MainWindow | None) Instanz des Hauptfensters für UI-Interaktionen.
        :param verbose: (bool) Aktiviert erweiterte Konsolenausgaben.
        """
        super().__init__(logger=logger, window=window, verbose=verbose)
        self.appp: GoProParameters = appp
        self.folder: str | None = selected_folder

    # --------------------------------------------------------------------------------
    def run(self):
        """Extrahiert alle Metadaten der GoPro-Videos alle Videos des Ordner."""

        if self.folder is None:
            self.process_finished.emit()
            return

        # Umleitung aktivieren
        self.setup_environment()

        try:
            # 1. Wir erstellen eine saubere Loop für den QThread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 2. Wir führen die CLI-Main direkt in der Loop aus.
                # Dank nest_asyncio darf GeoTiler nun intern seine eigene Loop starten,
                # OHNE dass "This event loop is already running" geworfen wird.
                # Gleichzeitig ist eine Loop da, damit 'render_map_async' nicht verhungert!
                loop.run_until_complete(
                    asyncio.to_thread(
                        gopro2file_main,
                        params=self.appp,
                        profiler=None
                    )
                )
            finally:
                loop.close()

        except SystemExit as se:
            # se.code liefert den übergebenen Exitcode (z.B. 10 oder 20)
            exit_code = se.code if se.code is not None else 0
            log_to_callback(Tag.ERR, self.classname, f"Prozess kontrolliert beendet mit Exit-Code: {exit_code}")
        except Exception as e:
            # Fängt klassische Laufzeitfehler (z.B. KeyError, TypeError, FileNotFoundError)
            log_to_callback(Tag.ERR, self.classname, f"Unerwarteter Fehler im Ablauf: {e}")
            log_to_callback(Tag.ERR, self.classname, traceback.format_exc())
        except BaseException as be:
            # Fängt absolut alles andere ab, was nicht durch die oberen Blöcke erfasst wurde
            log_to_callback(Tag.ERR, self.classname, f"Kritischer Systemfehler (BaseException): {be}")
        finally:
            # Speicher und Event-Loops aufräumen
            gc.collect()

            # Cleanup: Streams zurücksetzen
            self.teardown_environment()


# --------------------------------------------------------------------------------
def main(verbose: bool = False):
    # Logfile initialisieren und Callback einrichten
    """Logfile initialisieren und Callback einrichten
    
    :param verbose: (bool) Beschreibung von verbose.
    """

    fpath = PathUtils.get_script_dir()
    my_logger = AppLogger.create(logfile_path=fpath, use_console=False)

    # Variablen vorbelegen
    arg_verbose = True if len(sys.argv) > 1 else False

    # Verzeichnisse ausgeben
    if arg_verbose:
        log_to_callback(Tag.LOG, f"Start-Verzeichnis:    {PathUtils.get_script_dir()}")
        log_to_callback(Tag.LOG, f"Data-Verzeichnis:     {PathUtils.get_data_dir()}")
        log_to_callback(Tag.LOG, f"Work-Verzeichnis:     {PathUtils.get_work_dir()}")
        log_to_callback(Tag.LOG, f"Temp-Verzeichnis:     {PathUtils.get_temp_dir()}")
        log_to_callback(Tag.LOG, f"UI-Verzeichnis:       {PathUtils.get_ui_dir()}")
        log_to_callback(Tag.LOG, f"Resource-Verzeichnis: {PathUtils.get_resource_dir()}")

    # # Gui vorbereiten und laden
    ui_file = AppConfig.UI_FILE
    if not ui_file.exists():
        fatal(msg=f"Cannot find {ui_file.name}", exitcode=-1)

    # um das Taskbar-Icon anzuzeigen muss unter Windows die UID erzeugt werden
    initialize_windows_app_id(company=AppConfig.COMPANY, program=AppConfig.NAME, version='2.1')

    # App erzeugen und ggfls aus RAM wieder verwenden
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    else:
        app = cast(QApplication, app)

    if arg_verbose:
        log_to_callback(Tag.STATUS, f"app = QApplication(sys.argv)...")
    # Wichtig: Den Handler einmalig beim App-Start instanziieren
    _handler = ErrorHandler()

    # Lädt die Übersetzungen für Standard-Dialog-Buttons wie "Abbrechen"
    qt_translator = QTranslator()
    translation_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(QLocale.system(), "qtbase", "_", translation_path):
        app.installTranslator(qt_translator)

    # Wichtig: Den Handler einmalig beim App-Start instanziieren
    _handler = ErrorHandler()

    # Parameter-Klasse erstellen
    appp: GoProParameters = GoProParameters()
    window = MainWindow(ui_file=ui_file, logger=my_logger, appp=appp, verbose=arg_verbose or verbose)
    if not window:
        fatal(msg=f"No window generated...", exitcode=-1)
    else:
        # 1. Erst das Fenster auf dem Bildschirm zentrieren
        window.center_window()
        # 2. App-Icon setzen
        window.load_icon(app=app)
        # 3. Jetzt das eigentliche UI-Fenster anzeigen, das vom Loader gebaut wurde
        window.show()
        # 4. Event-Loop starten
        exit_code = app.exec()
        sys.exit(exit_code)


# --------------------------------------------------------------------------------
if __name__ == "__main__":
    setup_crash_logger()
    main()
