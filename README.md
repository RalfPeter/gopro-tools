# gopro-tools

Eine Sammlung von Grafischen Benutzeroberflächen (PySide6) und CLI-Pipelines zur Verarbeitung von **GoPro-Videos**, **Telemetrie-Overlays** und **Geodaten**.

Diese Suite baut auf dem Kern-Framework **[gpmf-tools](https://github.com/RalfPeter/gpmf-tools)** auf.

---

## 🖥️ Enthaltene Anwendungen

### 1. `gui_gopro2file`
Desktop-Anwendung zur Analyse, Verwaltung und Anreicherung von GoPro-Medien:
* **Batch-Verarbeitung:** Automatisches Umbenennen und Organisieren von MP4/GPMF-Dateien.
* **Geokodierung:** Ermittlung von Ortsnamen und Adressen via GeoNames & Geocoding-Services.
* **GPX-Export:** Extraktion von GPS-Trajektorien direkt aus den GPMF-Metadaten.

### 2. `gui_gopro2overlay`
Desktop-Anwendung zum Rendern von professionellen Telemetrie-Overlays in Videos:
* **Visualisierungen:** Tacho, Höhenprofil, G-Kraft-Messer, Kompass und interaktive Karten-Overlays.
* **FFmpeg-Integration:** Hardwarebeschleunigtes Rendering und Zusammenführen von Video und Overlay.
* **Layout-Editor:** Anpassbare Overlay-Elemente und Templates.

### 3. CLI-Pipelines (`prg_*.py`)
Skripte für die Stapelverarbeitung auf der Kommandozeile ohne Benutzeroberfläche.

---

## 🛠️ Installation

### Voraussetzungen
* Python `>= 3.10`
* **FFmpeg / FFprobe:** Muss im Systempfad (`PATH`) verfügbar sein.

### Installation aus Quellcode (Entwicklungsmodus)
```cmd
git clone [https://github.com/RalfPeter/gopro-tools.git](https://github.com/RalfPeter/gopro-tools.git)
cd gopro-tools
pip install -e .

```

---

## 🚀 Starten der Anwendungen

Nach der Installation stehen die Starter direkt in der Konsole zur Verfügung:

```cmd
# Startet die Dateiverwaltung & Geokodierung
gopro2file

# Startet den Telemetrie-Overlay-Generator
gopro2overlay

```

Alternativ können die Skripte direkt per Python ausgeführt werden:

```cmd
python gui_gopro2file.py
python gui_gopro2overlay.py

```

---

## 📄 Lizenz

Dieses Projekt ist unter der **GNU General Public License v3 (GPLv3)** lizenziert.

```
