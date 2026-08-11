#!/usr/bin/env python
# ------------------------------------------------------------------------------
# 10-08-2026
# RalfPeter <ralfpeter.bergheim@gmail.com>
# https://github.com/RalfPeter/
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
# ------------------------------------------------------------------------------
#  Programm          : gui_gopro2overlay.py
#  Version           : 3.0
#  Beschreibung      : Logfile initialisieren und Callback einrichten
#  Zeilen            : 667
#  Abhängigkeiten    : PySide6, asyncio, gc, os, pathlib, sys, time, traceback, typing
#  Eigene Frameworks : rpg_gpmf, rpg_gui, rpg_overlay, rpg_utils
#  Klassen           : MainWindow, Worker
# ------------------------------------------------------------------------------
#  Public Methoden:
#    MainWindow                                           → Hauptfenster der Anwendung
#      init_ui()                                          → Verbindet Signale und setzt initiale Widget-Zustände.
#      close_action()                                     → Kurzbeschreibung für close_action.
#      save_settings()                                    → Setzen der Speicherparameter
#      load_settings()                                    → Lädt die gespeicherten Einstellungen beim Start der Anwendung.
#      update_on_checked(item)                            → Kurzbeschreibung für update_on_checked.
#      resize_pixmap()                                    → Kurzbeschreibung für resize_pixmap.
#      on_item_selected()                                 → Wenn ein Item in der Liste ausgewählt wird, diese Funktion aufrufen
#      adjust_pixmap_size()                               → Skaliere das Pixmap proportional zur Größe des QLabel, während das Seitenverhältnis beibehalten wird
#      select_folder()                                    → Öffne den Dialog, um einen Ordner auszuwählen
#      fill_folder(str)                                   → Kurzbeschreibung für fill_folder.
#      select_layout_file()                               → Öffnet einen Dateiauswahl-Dialog
#      execute_action()                                   → Startet die Hintergrundverarbeitung im dedizierten QThread nach Qt-Goldstandard.
#      on_progress_signal_received(ProgressEvent)         → Zentraler Empfänger für Fortschritts-Updates.
#      on_process_finished_received()                     → Aktiviere den Button wieder nach dem Abschluss der Arbeit
#      on_log_signal_received(str)                        → Kurzbeschreibung für on_log_signal_received.
#
#    Worker                                               → finished = Signal()
#      run()                                              → Führt die Erstellung der GoPro-Overlays für alle ausgewählten Videos aus.
# ------------------------------------------------------------------------------
#  Globale Funktionen:
#    main(bool)                                           → Logfile initialisieren und Callback einrichten
# ------------------------------------------------------------------------------
#  Copyright (C) 2026 <ralfpeter.bergheim@gmail.com>
# ------------------------------------------------------------------------------

import sys
import asyncio
import os
import gc
import traceback
from typing import cast
from time import time
from pathlib import Path

from PySide6.QtCore import Qt, Slot, QThread, Signal, QTranslator, QLibraryInfo, QLocale
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QCheckBox, QSplitter, QPushButton, QListWidget,
                               QListWidgetItem, QTextEdit, QFileDialog, QProgressBar)

from rpg_utils import TRENNER, fatal, setup_crash_logger, log_to_callback, AppLogger, CallbackTag as Tag, ProgressEvent, ProgressType, initialize_windows_app_id, PathUtils
from rpg_gpmf import SUFFIX_OVERLAY, VIDEO_EXTENSIONS, IMAGE_EXTENSIONS
from rpg_gpmf import FfmpegConfig, FfmpegTools, GoProFile, NoGoProError, NoVideoError
from rpg_overlay import create_gopro_overlay
from rpg_gui import ErrorHandler, BaseMainWindow, BaseWorker

from prg_gopro2overlay_config import OverlayParameters
from gui_gopro2overlay_const import AppConfig


# ================================================================================
# -- Main-Window -----------------------------------------------------------------
# ================================================================================
class MainWindow(BaseMainWindow):
    """Hauptfenster der Anwendung"""

    # Definition der Signale auf Klassenebene
    log_signal = Signal(str)
    progress_signal = Signal(ProgressEvent)

    # ------------------------------------------------------------------------------------------------------------------------
    def __init__(self, ui_file: Path, logger: AppLogger, appp: OverlayParameters, parent: QWidget | None = None, ffmpeg: FfmpegTools | None = None, clean: bool = False, logfile: bool = False, verbose: bool = False):
        """Kurzbeschreibung für __init__.
        
        :param ui_file: (Path) Beschreibung von ui_file.
        :param logger: (AppLogger) Beschreibung von logger.
        :param appp: (OverlayParameters) Beschreibung von appp.
        :param parent: (QWidget | None) Beschreibung von parent.
        :param ffmpeg: (FfmpegTools | None) Beschreibung von ffmpeg.
        :param clean: (bool) Beschreibung von clean.
        :param logfile: (bool) Beschreibung von logfile.
        :param verbose: (bool) Beschreibung von verbose.
        """

        super().__init__(parent=parent, ui_file=ui_file, appp=appp, logger=logger, title=AppConfig.TITLE, verbose=verbose)

        if self.ui is None:
            fatal(msg="UI konnte nicht geladen werden", exitcode=999)
            sys.exit(999)

        self.clean: bool = clean
        self.ffmpeg: FfmpegTools | None = ffmpeg
        self.logfile: bool = logfile
        self.selected_folder: str = ''
        self.selected_layoutfile: str = ''
        self.worker: Worker | None = None
        self.pixmap: QPixmap = QPixmap()

        # Referenzierung der UI-Elemente
        self.folder_label = cast(QLabel, self.ui.findChild(QLabel, "folder_label"))  # UI-Element referenzieren - folder_label
        self.folderselect_button = cast(QPushButton, self.ui.findChild(QPushButton, "folderselect_button"))  # UI-Element referenzieren - folderselect_button
        self.list_image_splitter = cast(QSplitter, self.ui.findChild(QSplitter, "list_image_splitter"))  # UI-Element referenzieren - list_image_splitter
        self.video_list = cast(QListWidget, self.ui.findChild(QListWidget, "video_list"))  # UI-Element referenzieren - video_list
        self.image_label = cast(QLabel, self.ui.findChild(QLabel, "image_label"))  # UI-Element referenzieren - image_label
        self.layout_label = cast(QLabel, self.ui.findChild(QLabel, "layout_label"))  # UI-Element referenzieren - layout_label
        self.layoutselect_button = cast(QPushButton, self.ui.findChild(QPushButton, "layoutselect_button"))  # UI-Element referenzieren - layoutselect_button
        self.checkbox_clean = cast(QCheckBox, self.ui.findChild(QCheckBox, "checkbox_clean"))  # UI-Element referenzieren - checkbox_clean
        self.checkbox_verbose = cast(QCheckBox, self.ui.findChild(QCheckBox, "checkbox_verbose"))  # UI-Element referenzieren - checkbox_verbose
        self.output_text = cast(QTextEdit, self.ui.findChild(QTextEdit, "output_text"))  # UI-Element referenzieren - output_text
        self.overlay_progressbar = cast(QProgressBar, self.ui.findChild(QProgressBar, "overlay_progressbar"))  # UI-Element referenzieren - overlay_progressbar
        self.quit_button = cast(QPushButton, self.ui.findChild(QPushButton, "quit_button"))  # UI-Element referenzieren - quit_button
        self.execute_button = cast(QPushButton, self.ui.findChild(QPushButton, "execute_button"))  # UI-Element referenzieren - execute_button

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
        # Layout für die Video-Liste und das Bild
        self.video_list.itemChanged.connect(self.update_on_checked)  # Signal bei Item-Änderung
        self.video_list.itemSelectionChanged.connect(self.on_item_selected)  # Signal für Auswahl
        # Verknüpfe das Resizing-Event des Splitters
        self.list_image_splitter.splitterMoved.connect(self.adjust_pixmap_size)
        # Layout für Layout-File und Button
        self.layoutselect_button.clicked.connect(self.select_layout_file)
        # Textfeld für die Ausgabe
        self.output_text.setReadOnly(True)  # Ausgabe soll nur lesbar sein
        # Progressbar einfügen
        self.overlay_progressbar.setValue(0)
        self.overlay_progressbar.setMinimum(0)
        self.overlay_progressbar.setMaximum(100)
        # Buttons für Aktionen
        self.execute_button.setEnabled(False)  # Der Button ist standardmäßig deaktiviert
        self.execute_button.clicked.connect(self.execute_action)
        self.quit_button.clicked.connect(self.on_quit_button_clicked)

    # --------------------------------------------------------------------------------
    def close_action(self):
        """Kurzbeschreibung für close_action."""

        self.worker = None
        super().close_action()

    # --------------------------------------------------------------------------------
    def save_settings(self):
        """Setzen der Speicherparameter"""

        self.appp._verbose = self.checkbox_verbose.isChecked()
        self.appp.clean = self.checkbox_clean.isChecked()
        self.appp.recursive = False

        self.appp.layout_xml = self.selected_layoutfile
        self.appp.selected_folder = self.selected_folder
        self.appp.inputpaths = [self.selected_folder]
        # Speichert die Fensterposition, Fenstergröße und UI-Einstellungen in einer Yaml-Konfigurationsdatei.
        super().save_settings()

    # --------------------------------------------------------------------------------
    def load_settings(self):
        """Lädt die gespeicherten Einstellungen beim Start der Anwendung."""

        super().load_settings()
        # alle Settings einlesen
        self.selected_folder = self.appp.selected_folder
        self.folder_label.setText(self.selected_folder)
        self.selected_layoutfile = self.appp.layout_xml
        self.layout_label.setText(self.selected_layoutfile)

        self.verbose = self.checkbox_verbose.isChecked()
        self.clean = self.checkbox_clean.isChecked()

        if self.selected_folder:
            if Path(self.selected_folder).is_dir():
                self.fill_folder(self.selected_folder)

        if self.selected_layoutfile:
            if not Path(self.selected_layoutfile).is_file():
                self.append_output_text(self.output_text, f'Layout: {self.selected_layoutfile} existiert nicht!')

    # --------------------------------------------------------------------------------
    def update_on_checked(self, item):
        """Kurzbeschreibung für update_on_checked.
        
        :param item: (Any) Beschreibung von item.
        """

        videofile = Path(self.selected_folder + '/' + item.text()).resolve()

        if item.checkState() == Qt.CheckState.Checked:
            # Signale kurz blockieren, um rekursive Trigger-Schleifen zu verhindern
            self.video_list.blockSignals(True)
            try:
                # Selektiert das Item und setzt den Fokus darauf
                item.setSelected(True)
                self.video_list.setCurrentItem(item)
            finally:
                self.video_list.blockSignals(False)

            # Manuell die Bild-Lade-Logik anstoßen
            self.on_item_selected()
            # ----------------------------------------------------------

        if self.checkbox_verbose.isChecked():
            if item.checkState() == Qt.CheckState.Checked:
                self.append_output_text(self.output_text, f"Item '{videofile}' wurde angehakt.")
            else:
                self.append_output_text(self.output_text, f"Item '{videofile}' wurde deaktiviert.")

        # Überprüfe, ob mindestens eine Datei in der Liste ausgewählt ist
        checked_items = any(self.video_list.item(i).checkState() == Qt.CheckState.Checked for i in range(self.video_list.count()))
        self.execute_button.setEnabled(checked_items)

    # --------------------------------------------------------------------------------
    def resize_pixmap(self):
        """Kurzbeschreibung für resize_pixmap."""

        if self.pixmap:
            scaled_pixmap = self.pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.image_label.setPixmap(scaled_pixmap)

    # --------------------------------------------------------------------------------
    def on_item_selected(self):
        """Wenn ein Item in der Liste ausgewählt wird, diese Funktion aufrufen"""

        selected_items = self.video_list.selectedItems()
        if selected_items:
            selected_item = selected_items[0]

            # Saubere, plattformunabhängige Pfadkonstruktion via pathlib
            base_path = Path(self.selected_folder) / selected_item.text()
            base_path = base_path.resolve()

            # Iteration über alle erlaubten Bild-Erweiterungen
            imagefile: Path | None = None
            for ext in IMAGE_EXTENSIONS:
                candidate = base_path.with_suffix(ext)
                if candidate.exists():
                    imagefile = candidate
                    break

            # Log-Ausgabe für das ausgewählte Element (Verwendung des finalen Pfads oder Fallbacks)
            log_path = imagefile or base_path.with_suffix(IMAGE_EXTENSIONS[0])
            if self.checkbox_verbose.isChecked():
                self.append_output_text(self.output_text, f"Item '{log_path}' wurde ausgewählt.")

            # Bild anzeigen, falls eine der Varianten auf der Festplatte existiert
            if imagefile is not None:
                image = QImage(imagefile)
                self.pixmap.convertFromImage(image)
                self.resize_pixmap()
            else:
                self.image_label.clear()
                # Meldung ausgeben, dass keines der unterstützten Formate gefunden wurde
                extensions_str = ", ".join(IMAGE_EXTENSIONS)
                self.append_output_text(self.output_text, f"Bild für '{base_path.name}' existiert mit den Endungen ({extensions_str}) nicht.")

    # --------------------------------------------------------------------------------
    def adjust_pixmap_size(self):
        """Skaliere das Pixmap proportional zur Größe des QLabel, während das Seitenverhältnis beibehalten wird"""

        self.resize_pixmap()

    # --------------------------------------------------------------------------------
    def select_folder(self):
        """Öffne den Dialog, um einen Ordner auszuwählen"""

        folder = QFileDialog.getExistingDirectory(self, caption=AppConfig.CAPTION_FOLDER, dir=self.selected_folder)
        self.fill_folder(folder)

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
                    GoProFile(goprofile=folder + '/' + video, verbose=False, use_geocities=False)
                except NoGoProError as e:
                    if self.verbose:
                        self.append_output_text(self.output_text, f'Datei: {video} - {e.message}')
                    continue
                except NoVideoError as e:
                    if self.verbose:
                        self.append_output_text(self.output_text, f'Datei: {video} - {e.message}')
                    continue
                else:
                    goprovideos.append(video)
            videos = goprovideos

            # fill up the listview
            for video in videos:
                item = QListWidgetItem(video)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.video_list.addItem(item)

        else:
            self.folder_label.setText('')
            self.output_text.clear()

    # --------------------------------------------------------------------------------
    def select_layout_file(self):
        """Öffnet einen Dateiauswahl-Dialog"""

        if self.selected_layoutfile:
            file_dir = str(Path(self.selected_layoutfile).parent)
        else:
            file_dir = str(self.selected_folder)

        file_name, _ = QFileDialog.getOpenFileName(self, AppConfig.CAPTION_LAYOUT, file_dir, AppConfig.FILTER_LAYOUT)

        if file_name:
            self.selected_layoutfile = file_name
            # Zeige den ausgewählten Dateinamen im Label an
            self.layout_label.setText(f"{file_name}")

            # Optional: Zeige den Dateipfad auch in einem QLineEdit oder verarbeite ihn weiter
            self.append_output_text(self.output_text, f"Datei '{file_name}' wurde ausgewählt.")
        else:
            self.append_output_text(self.output_text, "Keine Datei ausgewählt.")
            self.layout_label.setText('')

    # --------------------------------------------------------------------------------
    def execute_action(self) -> None:
        """Startet die Hintergrundverarbeitung im dedizierten QThread nach Qt-Goldstandard.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        selected_videos: list[str] = [
            item.text() for item in self.video_list.findItems("*", Qt.MatchFlag.MatchWildcard)
            if item.checkState() == Qt.CheckState.Checked
        ]

        if not selected_videos:
            return

        self.verbose = self.checkbox_verbose.isChecked()
        self.clean = self.checkbox_clean.isChecked()
        layout_file: str = self.selected_layoutfile if self.selected_layoutfile else 'default.xml'

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
            selected_videos=selected_videos,
            selected_folder=self.selected_folder,
            layout_file=layout_file,
            log_file=self.logfile,
            window=self,
            ffmpeg=self.ffmpeg,
            verbose=self.verbose
        )

        # PyCharm-Typenprüfer absichern
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
    @Slot(int, int)  # Der Callback liefert current und total
    def on_progress_signal_received(self, event: ProgressEvent) -> None:
        """Zentraler Empfänger für Fortschritts-Updates.
        
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
    @Slot()
    def on_process_finished_received(self) -> None:
        # Aktiviere den Button wieder nach dem Abschluss der Arbeit
        """Aktiviere den Button wieder nach dem Abschluss der Arbeit
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.append_output_text(self.output_text, "Alle Overlays wurden erfolgreich erstellt!")
        self.append_output_text(self.output_text, TRENNER)
        self.execute_button.setEnabled(True)
        self.overlay_progressbar.setValue(0)  # Setze den Wert der Progressbar nach der Verarbeitung auf 0

        for item in self.video_list.findItems("*", Qt.MatchFlag.MatchWildcard):
            item.setCheckState(Qt.CheckState.Unchecked)

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
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        self.thread = None
        self.worker = None


# ================================================================================
# -- Worker-Thread ----------------------------------------------------------
# ================================================================================
class Worker(BaseWorker):
    # finished = Signal()

    # --------------------------------------------------------------------------------
    """finished = Signal()"""

    def __init__(self,
                 logger: AppLogger,
                 selected_videos: list[str] | None = None,
                 selected_folder: str | None = None,
                 layout_file: str | None = None,
                 window: MainWindow | None = None,
                 ffmpeg: FfmpegTools | None = None,
                 log_file: bool = False,
                 verbose: bool = False):
        """Initialisiert den Worker-Thread für die Video-Verarbeitung.
        
        :param logger: (AppLogger) Beschreibung von logger.
        :param selected_videos: (list[str] | None) Beschreibung von selected_videos.
        :param selected_folder: (str | None) Beschreibung von selected_folder.
        :param layout_file: (str | None) Beschreibung von layout_file.
        :param window: (MainWindow | None) Beschreibung von window.
        :param ffmpeg: (FfmpegTools | None) Beschreibung von ffmpeg.
        :param log_file: (bool) Beschreibung von log_file.
        :param verbose: (bool) Beschreibung von verbose.
        """

        super().__init__(logger=logger, window=window, verbose=verbose)
        self.folder: str | None = selected_folder
        self.videos: list[str] = selected_videos if selected_videos is not None else []
        self.layout_file: str | None = layout_file
        self.log_file: bool = log_file
        self.ffmpeg: FfmpegTools | None = ffmpeg

    # --------------------------------------------------------------------------------
    def run(self) -> None:
        """Führt die Erstellung der GoPro-Overlays für alle ausgewählten Videos aus.
        
        :return: (None) Beschreibung des Rückgabewerts.
        """

        if self.folder is None:
            self.process_finished.emit()
            return

        # Umleitung aktivieren
        self.setup_environment()

        try:
            for index, video in enumerate(self.videos):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    policy = asyncio.get_event_loop_policy()
                    try:
                        loop = policy.new_event_loop()
                        policy.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.get_event_loop_policy().set_event_loop(loop)

                videofile = (Path(self.folder) / video).resolve()
                overlayfile = videofile.with_suffix(SUFFIX_OVERLAY)

                start_time = time()
                log_to_callback(Tag.STATUS, self.classname, TRENNER)
                log_to_callback(Tag.STATUS, self.classname, f'Erzeuge Overlay aus GoPro Video {videofile.name} ...')
                log_to_callback(Tag.PROGRESS, ProgressEvent.start(100))

                log_file = None
                if self.log_file:
                    log_file = videofile.with_suffix(".overlay.txt")
                    log_to_callback(Tag.LOG, self.classname, f'Logfile: {log_file} ...')

                try:
                    create_gopro_overlay(
                        input_file=videofile,
                        output_file=overlayfile,
                        layout_file=self.layout_file,
                        log_file=log_file,
                        verbose=self.verbose
                    )
                    log_to_callback(Tag.PROGRESS, ProgressEvent.finished())
                except Exception as exc:
                    log_to_callback(Tag.ERR, self.classname, f'Fehler bei Erstellung für {videofile.name}: {exc}')
                    log_to_callback(Tag.ERR, self.classname, traceback.format_exc())
                except SystemExit as se:
                    # se.code liefert den übergebenen Exitcode (z.B. 10 oder 20)
                    exit_code = se.code if se.code is not None else 0
                    log_to_callback(Tag.ERR, self.classname, f"Prozess kontrolliert beendet mit Exit-Code: {exit_code}")
                except BaseException as be:
                    # Fängt absolut alles andere ab, was nicht durch die oberen Blöcke erfasst wurde
                    log_to_callback(Tag.ERR, self.classname, f"Kritischer Systemfehler (BaseException): {be}")

                elapsed_time = time() - start_time
                log_to_callback(Tag.STATUS, self.classname, f'Dauer für Overlay aus GoPro Video {videofile.name} = {elapsed_time:.2f} sec geschätzt ...')

                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except (RuntimeError, asyncio.CancelledError):
                    pass

                gc.collect()

        finally:
            # Speicher und Event-Loops aufräumen
            gc.collect()

            try:
                current_loop = asyncio.get_event_loop()
                if not current_loop.is_closed():
                    current_loop.close()
            except RuntimeError:
                pass

            # Cleanup: Streams zurücksetzen
            self.teardown_environment()


# --------------------------------------------------------------------------------
def main(verbose: bool = False):
    """Logfile initialisieren und Callback einrichten
    
    :param verbose: (bool) Beschreibung von verbose.
    """

    fpath = PathUtils.get_script_dir()
    my_logger = AppLogger.create(logfile_path=fpath, use_console=False)

    # Variablen vorbelegen
    arg_verbose = True if len(sys.argv) > 1 else False
    arg_clean = False
    ffmpeg: FfmpegTools | None = None

    # Verzeichnisse ausgeben
    if arg_verbose:
        log_to_callback(Tag.LOG, f"Start-Verzeichnis:    {PathUtils.get_script_dir()}")
        log_to_callback(Tag.LOG, f"Data-Verzeichnis:     {PathUtils.get_data_dir()}")
        log_to_callback(Tag.LOG, f"Work-Verzeichnis:     {PathUtils.get_work_dir()}")
        log_to_callback(Tag.LOG, f"Temp-Verzeichnis:     {PathUtils.get_temp_dir()}")
        log_to_callback(Tag.LOG, f"UI-Verzeichnis:       {PathUtils.get_ui_dir()}")
        log_to_callback(Tag.LOG, f"Resource-Verzeichnis: {PathUtils.get_resource_dir()}")

    # ffmpeg instantinieren
    try:
        ffmpeg_config = FfmpegConfig()
        ffmpeg = FfmpegTools(config=ffmpeg_config, verbose=arg_verbose)
    except FileNotFoundError as e:
        fatal(msg=f'Modul ffmpeg fehlt: {e}', exitcode=80)

    # Überprüfen, ob ffmpeg erfolgreich instanziiert wurde
    if ffmpeg is None:
        fatal(msg="ffmpeg konnte nicht instanziiert werden", exitcode=82)

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

    # Parameter für Programm ermitteln
    appp: OverlayParameters = OverlayParameters()

    # Hauptprogramm mit allen Abhängigkeiten (inkl. Logger) aufrufen
    window = MainWindow(ui_file=ui_file, logger=my_logger, appp=appp, ffmpeg=ffmpeg, clean=arg_clean, verbose=arg_verbose or verbose, logfile=arg_verbose)

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


# ===================================================================================================
if __name__ == "__main__":
    setup_crash_logger()
    main()
