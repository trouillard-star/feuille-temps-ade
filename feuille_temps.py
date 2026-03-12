"""
╔══════════════════════════════════════════════════════════════╗
║         Feuille de Temps — Le Groupe ADE                     ║
║         © 2026 Thierry Rouillard — Tous droits réservés      ║
║         Développé par Thierry Rouillard pour Groupe ADE      ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys, os, json, zipfile, threading, tempfile, subprocess, urllib.parse
from datetime import datetime, timedelta
from urllib.request import urlopen, urlretrieve

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar,
    QFileDialog, QMessageBox, QDialog, QSizePolicy, QGraphicsDropShadowEffect,
    QTextEdit, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor

# ── Chemins ───────────────────────────────────────────────────────────────────
SAVE_PATH     = os.path.join(os.path.expanduser("~"), "Documents", "FeuilleTemps")
SETTINGS_FILE = os.path.join(SAVE_PATH, "settings.json")
os.makedirs(SAVE_PATH, exist_ok=True)

APP_NAME    = "Groupe ADE"
APP_SUB     = "Feuille de Temps"
APP_VERSION = "v3.7"
COPYRIGHT   = "© 2026 Thierry Rouillard"
DEV_CREDIT  = "Développé par Thierry Rouillard"

# ── Auto-update ───────────────────────────────────────────────────────────────
GITHUB_USER        = "trouillard-star"
GITHUB_REPO        = "feuille-temps-ade"
GITHUB_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest/download/FeuilleTemps_ADE.exe"
EXE_NAME           = "FeuilleTemps_ADE.exe"

def _version_tuple(v: str):
    v = v.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        try: parts.append(int(p))
        except: parts.append(0)
    while len(parts) < 3: parts.append(0)
    return tuple(parts)

def _newer(remote: str, local: str) -> bool:
    return _version_tuple(remote) > _version_tuple(local)

class UpdateSignals(QObject):
    update_available = pyqtSignal(str, str)
    check_failed     = pyqtSignal()

class UpdateChecker(threading.Thread):
    def __init__(self, signals):
        super().__init__(daemon=True); self.signals = signals
    def run(self):
        try:
            with urlopen(GITHUB_VERSION_URL, timeout=6) as r:
                data = json.loads(r.read().decode())
            remote = data.get("version",""); notes = data.get("notes","")
            if remote and _newer(remote, APP_VERSION):
                self.signals.update_available.emit(remote, notes)
        except Exception:
            self.signals.check_failed.emit()

class UpdateDownloader(threading.Thread):
    def __init__(self, signals, progress_cb, done_cb, error_cb):
        super().__init__(daemon=True)
        self.signals = signals; self.progress_cb = progress_cb
        self.done_cb = done_cb; self.error_cb = error_cb

    @staticmethod
    def get_current_exe():
        if getattr(sys, "frozen", False):
            exe = os.path.abspath(sys.argv[0])
            if not exe.lower().endswith(".exe") or not os.path.exists(exe):
                exe = os.path.abspath(sys.executable)
            return exe
        return ""

    def run(self):
        try:
            current_exe = self.get_current_exe()
            if not current_exe:
                self.error_cb("Fonctionne uniquement depuis le .exe compilé."); return
            current_dir  = os.path.dirname(current_exe)
            current_name = os.path.basename(current_exe)
            tmp_dir = tempfile.mkdtemp(prefix="ade_update_")
            tmp_exe = os.path.join(tmp_dir, EXE_NAME)
            def reporthook(block, block_size, total):
                dl = block * block_size
                self.progress_cb(min(dl, total) if total > 0 else dl, total)
            urlretrieve(GITHUB_RELEASE_URL, tmp_exe, reporthook)
            if os.path.getsize(tmp_exe) < 100_000:
                self.error_cb("Fichier téléchargé trop petit — corrompu."); return
            old_exe  = os.path.join(current_dir, current_name + ".old")
            bat_path = os.path.join(tmp_dir, "ade_update.bat")
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(f"""@echo off
timeout /t 3 /nobreak >nul
if exist "{old_exe}" del /f /q "{old_exe}"
if exist "{current_exe}" ren "{current_exe}" "{current_name}.old"
copy /y "{tmp_exe}" "{current_exe}"
if errorlevel 1 (
    if exist "{old_exe}" ren "{old_exe}" "{current_name}"
    exit /b 1
)
if exist "{old_exe}" del /f /q "{old_exe}"
start "" "{current_exe}"
timeout /t 2 /nobreak >nul
rmdir /s /q "{tmp_dir}" 2>nul
""")
            subprocess.Popen(["cmd.exe", "/c", bat_path],
                             creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                             close_fds=True, cwd=current_dir)
            self.done_cb()
        except Exception as ex:
            self.error_cb(str(ex))

# ╔══════════════════════════════════════════════════════════════╗
# ║                    SYSTÈME DE THÈMES                        ║
# ╚══════════════════════════════════════════════════════════════╝

THEMES = {
    "Dark Navy": {
        "BG":"#080C14","BG2":"#0D1220","BG3":"#111827",
        "CARD":"#141C2E","CARD2":"#1A2340",
        "ACC":"#4F8EF7","ACC2":"#7EAAFF","ACC3":"#2A5FD4","ACCD":"#1A3A8A",
        "GREEN":"#34D399","GREEN2":"#059669",
        "RED":"#F87171","AMBER":"#FBBF24",
        "TXT":"#EEF2FF","TXT2":"#6B7FAA","TXT3":"#3D4F72",
        "MUTED":"#2D3A55","BORDER":"#1E2C47","BORDER2":"#263351","ROW":"#0F1629",
        "PALETTE":["#4F8EF7","#34D399","#FBBF24","#A78BFA","#F472B6",
                   "#22D3EE","#FB923C","#A3E635","#F87171","#2DD4BF"],
    },

    "Midnight": {
        "BG":"#05050A","BG2":"#09090F","BG3":"#0E0E16",
        "CARD":"#101018","CARD2":"#17171F",
        "ACC":"#818CF8","ACC2":"#A5B4FC","ACC3":"#4F46E5","ACCD":"#1E1B4B",
        "GREEN":"#4ADE80","GREEN2":"#16A34A",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#F1F5F9","TXT2":"#64748B","TXT3":"#2E3A52",
        "MUTED":"#1E293B","BORDER":"#16162A","BORDER2":"#22223B","ROW":"#080810",
        "PALETTE":["#818CF8","#4ADE80","#FCD34D","#C084FC","#F472B6",
                   "#38BDF8","#FB923C","#A3E635","#F87171","#2DD4BF"],
    },

    "Silver": {
        "BG":"#0B1220",
        "BG2":"#111827",
        "BG3":"#1F2937",
        "CARD":"#1F2937",
        "CARD2":"#273449",
        "ACC":"#38BDF8",
        "ACC2":"#7DD3FC",
        "ACC3":"#0284C7",
        "ACCD":"#075985",
        "GREEN":"#34D399",
        "GREEN2":"#059669",
        "RED":"#FB7185",
        "AMBER":"#FBBF24",
        "TXT":"#F9FAFB",
        "TXT2":"#94A3B8",
        "TXT3":"#475569",
        "MUTED":"#334155",
        "BORDER":"#1F2A44",
        "BORDER2":"#334155",
        "ROW":"#0F172A",
        "PALETTE":[
            "#38BDF8","#34D399","#FBBF24","#A78BFA","#F472B6",
            "#818CF8","#FB923C","#A3E635","#FB7185","#2DD4BF"
        ],
    },

    "Hacker man": {
        "BG":"#0C0606",
        "BG2":"#150A0A",
        "BG3":"#1F1111",
        "CARD":"#1A0E0E",
        "CARD2":"#241414",
        "ACC":"#EF4444",
        "ACC2":"#FCA5A5",
        "ACC3":"#B91C1C",
        "ACCD":"#7F1D1D",
        "GREEN":"#4ADE80",
        "GREEN2":"#15803D",
        "RED":"#F87171",
        "AMBER":"#FCD34D",
        "TXT":"#FFF1F1",
        "TXT2":"#FDA4AF",
        "TXT3":"#7F3040",
        "MUTED":"#3B1C1C",
        "BORDER":"#2E1515",
        "BORDER2":"#7F1D1D",
        "ROW":"#0E0808",
        "PALETTE":[
            "#EF4444","#FCA5A5","#FCD34D","#C084FC","#F472B6",
            "#FB923C","#A3E635","#38BDF8","#4ADE80","#2DD4BF"
        ],
    },
    "Hackeur de Pentagone": {
        "BG":"#040B07",
        "BG2":"#07140D",
        "BG3":"#0C1F15",

        "CARD":"#0F2A1C",
        "CARD2":"#143625",

        "ACC":"#1FD16C",
        "ACC2":"#4ADE80",
        "ACC3":"#0F9F57",
        "ACCD":"#064E36",

        "GREEN":"#34D399",
        "GREEN2":"#059669",

        "RED":"#F87171",
        "AMBER":"#FBBF24",

        "TXT":"#F0FFF7",
        "TXT2":"#8EE6C2",
        "TXT3":"#3C7A63",

        "MUTED":"#17392A",

        "BORDER":"#1F4636",
        "BORDER2":"#295A46",

        "ROW":"#06130D",

        "PALETTE":[
            "#1FD16C",  # vert primaire
            "#4ADE80",  # vert clair
            "#2DD4BF",  # teal
            "#38BDF8",  # bleu data
            "#A78BFA",  # violet
            "#FBBF24",  # amber
            "#FB923C",  # orange
            "#34D399",  # emerald
            "#F87171",  # rouge
            "#A3E635",  # lime
            "#22D3EE",  # cyan
            "#C084FC"   # violet clair
        ],
    },

    "Blanc qui fait mal aux yeux (Light)": {
        "BG":"#F4F7FB",
        "BG2":"#E8EEF6",
        "BG3":"#DCE5F0",
        "CARD":"#FFFFFF",
        "CARD2":"#F1F5F9",
        "ACC":"#3B82F6",
        "ACC2":"#60A5FA",
        "ACC3":"#2563EB",
        "ACCD":"#1E40AF",
        "GREEN":"#10B981",
        "GREEN2":"#059669",
        "RED":"#EF4444",
        "AMBER":"#F59E0B",
        "TXT":"#0F172A",
        "TXT2":"#475569",
        "TXT3":"#94A3B8",
        "MUTED":"#CBD5E1",
        "BORDER":"#D1D9E6",
        "BORDER2":"#E2E8F0",
        "ROW":"#F8FAFC",
        "PALETTE":[
            "#3B82F6","#10B981","#F59E0B","#8B5CF6","#EC4899",
            "#06B6D4","#F97316","#84CC16","#EF4444","#14B8A6"
        ],
    },
}

# ── Variables globales du thème actif ─────────────────────────────────────────
BG=BG2=BG3=CARD=CARD2=ACC=ACC2=ACC3=ACCD=GREEN=GREEN2=RED=AMBER=""
TXT=TXT2=TXT3=MUTED=BORDER=BORDER2=ROW=""
PALETTE: list = []

def apply_theme(name: str):
    """Applique les variables de thème globalement."""
    global BG,BG2,BG3,CARD,CARD2,ACC,ACC2,ACC3,ACCD,GREEN,GREEN2,RED,AMBER
    global TXT,TXT2,TXT3,MUTED,BORDER,BORDER2,ROW,PALETTE
    t = THEMES.get(name, THEMES["Dark Navy"])
    BG=t["BG"]; BG2=t["BG2"]; BG3=t["BG3"]
    CARD=t["CARD"]; CARD2=t["CARD2"]
    ACC=t["ACC"]; ACC2=t["ACC2"]; ACC3=t["ACC3"]; ACCD=t["ACCD"]
    GREEN=t["GREEN"]; GREEN2=t["GREEN2"]
    RED=t["RED"]; AMBER=t["AMBER"]
    TXT=t["TXT"]; TXT2=t["TXT2"]; TXT3=t["TXT3"]
    MUTED=t["MUTED"]; BORDER=t["BORDER"]; BORDER2=t["BORDER2"]; ROW=t["ROW"]
    PALETTE=list(t["PALETTE"])

apply_theme("Dark Navy")  # thème par défaut

# ── Constantes UI ─────────────────────────────────────────────────────────────
JOURS   = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
MOIS_FR = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
           7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}

def ss_base():
    return f"""
    QWidget {{ background:{BG}; color:{TXT}; font-family:'Segoe UI'; font-size:13px; }}
    QScrollBar:vertical {{ background:{BG2}; width:5px; border-radius:3px; }}
    QScrollBar::handle:vertical {{ background:{BORDER2}; border-radius:3px; min-height:24px; }}
    QScrollBar::handle:vertical:hover {{ background:{ACC3}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar:horizontal {{ height:0; }}
    QToolTip {{ background:{CARD2}; color:{TXT}; border:1px solid {ACC3}; padding:5px 8px; border-radius:6px; font-size:12px; }}
    QComboBox {{ background:{CARD}; color:{TXT}; border:1px solid {BORDER}; border-radius:7px; padding:0 10px; font-size:12px; min-height:32px; }}
    QComboBox:hover {{ border-color:{BORDER2}; }}
    QComboBox:focus {{ border-color:{ACC}; }}
    QComboBox::drop-down {{ border:none; width:20px; }}
    QComboBox QAbstractItemView {{ background:{CARD2}; color:{TXT}; border:1px solid {BORDER2}; selection-background-color:{ACC3}; }}
"""

# ── Helpers data ──────────────────────────────────────────────────────────────
def get_monday(d):  return d - timedelta(days=d.weekday())
def week_key(m):    return m.strftime("%Y-%m-%d")
def fr_date(d):     return f"{d.day} {MOIS_FR[d.month]}"

def week_label(monday):
    fri = monday + timedelta(days=4)
    if monday.month == fri.month:
        return f"{monday.day} – {fri.day} {MOIS_FR[fri.month]} {fri.year}"
    return f"{monday.day} {MOIS_FR[monday.month]} – {fri.day} {MOIS_FR[fri.month]} {fri.year}"

def parse_heure(s):
    s = s.strip().replace("h",":")
    for fmt in ("%H:%M","%H%M"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def calc_h(a, b):
    s, e = parse_heure(a), parse_heure(b)
    return (e - s).seconds / 3600 if s and e and e > s else 0.0

def fmt_h(h):
    if h <= 0: return "–"
    m = int(round(h % 1 * 60))
    return f"{int(h)}h{m:02d}" if m else f"{int(h)}h"

def save_file(m):  return os.path.join(SAVE_PATH, f"{week_key(m)}.json")

def saved_weeks():
    out = []
    for f in os.listdir(SAVE_PATH):
        if f.endswith(".json") and f != "settings.json":
            try: out.append(datetime.strptime(f[:-5], "%Y-%m-%d"))
            except: pass
    return sorted(out, reverse=True)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"employer":"", "email_dest":"", "email_cc":"", "theme":"Dark Navy"}

def write_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def glow(widget, color, radius=16):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(radius); fx.setColor(QColor(color)); fx.setOffset(0,0)
    widget.setGraphicsEffect(fx)

# ── Widget helpers ────────────────────────────────────────────────────────────
def lbl(text, size=12, bold=False, color=None):
    c = color if color else TXT
    l = QLabel(text); f = QFont("Segoe UI", size); f.setBold(bold)
    l.setFont(f); l.setStyleSheet(f"color:{c}; background:transparent;")
    return l

def styled_entry(placeholder="", width=None, height=32):
    e = QLineEdit(); e.setPlaceholderText(placeholder); e.setFixedHeight(height)
    if width: e.setFixedWidth(width)
    e.setStyleSheet(f"""
        QLineEdit {{ background:{BG}; color:{TXT}; border:1px solid {BORDER}; border-radius:7px;
                    padding:0 10px; font-family:'Segoe UI'; font-size:13px; }}
        QLineEdit:focus {{ border-color:{ACC}; background:{BG3}; }}
        QLineEdit:hover {{ border-color:{BORDER2}; }}
    """)
    return e

def h_sep():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{BORDER}; background:{BORDER};"); f.setFixedHeight(1); return f

def section_lbl(text):
    l = QLabel(text)
    l.setStyleSheet(f"color:{TXT3}; font-size:9px; font-weight:700; letter-spacing:1.5px; background:transparent; padding-bottom:2px;")
    return l

def sidebar_btn(text):
    b = QPushButton(text); b.setFixedHeight(32); b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{ background:{CARD}; color:{TXT2}; border:1px solid {BORDER}; border-radius:8px;
                      padding:0 10px; font-size:11px; font-weight:500; }}
        QPushButton:hover {{ background:{CARD2}; color:{TXT}; border-color:{ACC3}; }}
        QPushButton:pressed {{ background:{ACCD}; }}
    """)
    return b

def card_frame(radius=12):
    f = QFrame()
    f.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:{radius}px;")
    return f

# ── LogoWidget ────────────────────────────────────────────────────────────────
class LogoWidget(QFrame):
    def __init__(self):
        super().__init__(); self.setFixedHeight(66)
        self.setStyleSheet(f"background:{BG2}; border:none;")
        lay = QHBoxLayout(self); lay.setContentsMargins(14,0,14,0); lay.setSpacing(10)
        badge = QLabel("ADE"); badge.setFixedSize(40,40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {ACC},stop:1 {ACC3});
            color:white; border-radius:10px; font-family:'Segoe UI'; font-size:13px; font-weight:800; letter-spacing:1px;
        """)
        glow(badge, ACC, 16); lay.addWidget(badge)
        tc = QVBoxLayout(); tc.setSpacing(0)
        name = QLabel("Groupe ADE")
        name.setStyleSheet(f"color:{TXT}; font-family:'Segoe UI'; font-size:14px; font-weight:700; background:transparent;")
        sub = QLabel("Feuille de Temps")
        sub.setStyleSheet(f"color:{TXT2}; font-family:'Segoe UI'; font-size:10px; background:transparent;")
        tc.addWidget(name); tc.addWidget(sub); lay.addLayout(tc); lay.addStretch()
        ver = QLabel(APP_VERSION)
        ver.setStyleSheet(f"background:{ACCD}; color:{ACC2}; border-radius:5px; padding:2px 7px; font-size:9px; font-weight:600;")
        lay.addWidget(ver)

# ── AutoCompleteRegistry ──────────────────────────────────────────────────────
class AutoCompleteRegistry:
    _projets: set = set(); _taches: set = set(); _descs: set = set()

    @classmethod
    def load_all(cls):
        for monday in saved_weeks():
            try:
                with open(save_file(monday), "r", encoding="utf-8") as f: d = json.load(f)
                for j in JOURS:
                    for r in d.get("jours",{}).get(j,[]):
                        if r.get("projet","").strip(): cls._projets.add(r["projet"].strip())
                        if r.get("tache","").strip():  cls._taches.add(r["tache"].strip())
                        if r.get("desc","").strip():   cls._descs.add(r["desc"].strip())
            except: pass

    @classmethod
    def add(cls, projet, tache, desc):
        if projet.strip(): cls._projets.add(projet.strip())
        if tache.strip():  cls._taches.add(tache.strip())
        if desc.strip():   cls._descs.add(desc.strip())

    @classmethod
    def suggest(cls, text, kind):
        if not text: return ""
        pool = {"projet":cls._projets, "tache":cls._taches, "desc":cls._descs}.get(kind, set())
        tl = text.lower()
        for item in sorted(pool):
            if item.lower().startswith(tl) and item != text: return item
        return ""

# ── AutoEntry ─────────────────────────────────────────────────────────────────
class AutoEntry(QLineEdit):
    def __init__(self, kind, placeholder="", width=None, height=32):
        super().__init__(); self._kind = kind; self._suggestion = ""; self._accepting = False
        self.setPlaceholderText(placeholder); self.setFixedHeight(height)
        if width: self.setFixedWidth(width)
        self.setStyleSheet(f"""
            QLineEdit {{ background:{BG}; color:{TXT}; border:1px solid {BORDER}; border-radius:7px;
                        padding:0 10px; font-family:'Segoe UI'; font-size:13px; }}
            QLineEdit:focus {{ border-color:{ACC}; background:{BG3}; }}
            QLineEdit:hover {{ border-color:{BORDER2}; }}
        """)
        self.textEdited.connect(self._on_edited)

    def _on_edited(self, text):
        if self._accepting: return
        sug = AutoCompleteRegistry.suggest(text, self._kind)
        if sug:
            self._suggestion = sug
            self.blockSignals(True)
            self.setText(sug); self.setSelection(len(text), len(sug)-len(text))
            self.blockSignals(False)
        else: self._suggestion = ""

    def keyPressEvent(self, event):
        if self._suggestion and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Return):
            self._accepting = True
            self.setText(self._suggestion); self.setCursorPosition(len(self._suggestion))
            self._suggestion = ""; self._accepting = False; event.accept(); return
        if self._suggestion and event.key() == Qt.Key.Key_Escape:
            typed = self.text()[:self.selectionStart()]
            self.blockSignals(True); self.setText(typed); self.blockSignals(False)
            self._suggestion = ""; event.accept(); return
        super().keyPressEvent(event)

_COL_HDR = [("Date",100),("Début",72),("Fin",72),("Tâche",140),("Projet",150),("Client / Description",0),("Durée",64),("",28)]

# ── RowWidget ─────────────────────────────────────────────────────────────────
class RowWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, jour, row_idx, parent_day):
        super().__init__()
        self.jour = jour; self.row_idx = row_idx; self.parent_day = parent_day
        self.setFixedHeight(44)
        self.setStyleSheet(f"background:{ROW if row_idx%2==0 else CARD}; border:none;")
        lay = QHBoxLayout(self); lay.setContentsMargins(10,0,8,0); lay.setSpacing(5)
        self.date_lbl = lbl("", 10, color=TXT3); self.date_lbl.setFixedWidth(100); lay.addWidget(self.date_lbl)
        self.start  = styled_entry("08:00", 72)
        self.end    = styled_entry("16:30", 72)
        self.tache  = AutoEntry("tache",  "Tâche...",  140)
        self.projet = AutoEntry("projet", "Projet...", 150)
        self.desc   = AutoEntry("desc",   "Client lié au projet...")
        self.desc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.dur_lbl = QLabel("–"); self.dur_lbl.setFixedWidth(64)
        self.dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dur_lbl.setStyleSheet(f"color:{MUTED}; background:transparent; font-weight:600; font-size:12px;")
        self.del_btn = QPushButton("✕"); self.del_btn.setFixedSize(26,26)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet(f"""
            QPushButton {{ background:{CARD2}; color:{TXT3}; border:1px solid {BORDER}; border-radius:6px; font-size:10px; font-weight:600; }}
            QPushButton:hover {{ background:{RED}; color:white; border-color:{RED}; }}
        """)
        for w in (self.start, self.end, self.tache, self.projet, self.desc, self.dur_lbl, self.del_btn):
            lay.addWidget(w)
        self.start.textChanged.connect(self._on_time)
        self.end.textChanged.connect(self._on_time)
        self.tache.textChanged.connect(self.changed)
        self.projet.textChanged.connect(self.changed)
        self.desc.textChanged.connect(self.changed)
        self.tache.editingFinished.connect(self._reg)
        self.projet.editingFinished.connect(self._reg)
        self.desc.editingFinished.connect(self._reg)
        self.del_btn.clicked.connect(lambda: parent_day.remove_row(self))

    def _on_time(self):
        h = calc_h(self.start.text(), self.end.text())
        if h:
            self.dur_lbl.setText(fmt_h(h))
            self.dur_lbl.setStyleSheet(f"color:{ACC2}; background:transparent; font-weight:700; font-size:12px;")
        else:
            self.dur_lbl.setText("–")
            self.dur_lbl.setStyleSheet(f"color:{MUTED}; background:transparent; font-weight:600; font-size:12px;")
        self.changed.emit()

    def _reg(self): AutoCompleteRegistry.add(self.projet.text(), self.tache.text(), self.desc.text())
    def set_date(self, d): self.date_lbl.setText(d.strftime("%Y-%m-%d"))

    def get_data(self):
        return {"debut":self.start.text(),"fin":self.end.text(),
                "tache":self.tache.text(),"projet":self.projet.text(),"desc":self.desc.text()}

    def total_h(self): return calc_h(self.start.text(), self.end.text())

    def has_data(self):
        return any(f.text().strip() for f in (self.start, self.end, self.tache, self.projet, self.desc))

    def set_data(self, data):
        for field, key in ((self.start,"debut"),(self.end,"fin")):
            field.blockSignals(True); field.setText(data.get(key,"")); field.blockSignals(False)
        self.tache.setText(data.get("tache",""))
        self.projet.setText(data.get("projet",""))
        self.desc.setText(data.get("desc",""))
        self._on_time()

    def clear(self):
        for field in (self.start, self.end):
            field.blockSignals(True); field.clear(); field.blockSignals(False)
        self.tache.clear(); self.projet.clear(); self.desc.clear()
        self.dur_lbl.setText("–")
        self.dur_lbl.setStyleSheet(f"color:{MUTED}; background:transparent; font-weight:600; font-size:12px;")

# ── DayCard ───────────────────────────────────────────────────────────────────
class DayCard(QFrame):
    data_changed = pyqtSignal()

    def __init__(self, jour, idx):
        super().__init__()
        self.jour = jour; self.idx = idx; self.rows = []; self.monday = None
        self.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;")
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        hdr = QFrame(); hdr.setFixedHeight(50)
        hdr.setStyleSheet(f"""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {BG2},stop:1 {CARD});
            border-radius:13px 13px 0 0; border-bottom:1px solid {BORDER};
        """)
        hl = QHBoxLayout(hdr); hl.setContentsMargins(16,0,12,0)
        dot = QFrame(); dot.setFixedSize(8,8); dot.setStyleSheet(f"background:{ACC}; border-radius:4px;")
        hl.addWidget(dot); hl.addSpacing(8)
        self.day_name = QLabel(jour.upper())
        self.day_name.setStyleSheet(f"color:{TXT}; font-family:'Segoe UI'; font-size:12px; font-weight:700; letter-spacing:1.5px; background:transparent;")
        self.date_lbl = QLabel(""); self.date_lbl.setStyleSheet(f"color:{TXT2}; font-size:11px; background:transparent;")
        hl.addWidget(self.day_name); hl.addWidget(self.date_lbl); hl.addStretch()
        self.tot_badge = QFrame(); self.tot_badge.setFixedHeight(26)
        self.tot_badge.setStyleSheet(f"background:{ACCD}; border-radius:8px; border:1px solid {ACC3};")
        tbl = QHBoxLayout(self.tot_badge); tbl.setContentsMargins(10,0,10,0)
        self.tot_lbl = QLabel("–"); self.tot_lbl.setStyleSheet(f"color:{ACC2}; font-size:12px; font-weight:700; background:transparent;")
        tbl.addWidget(self.tot_lbl); hl.addWidget(self.tot_badge); hl.addSpacing(6)
        add_btn = QPushButton("＋ Ligne"); add_btn.setFixedHeight(28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{ background:{ACC3}; color:{TXT}; border:none; border-radius:7px; padding:0 12px; font-size:11px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC}; }}
            QPushButton:pressed {{ background:{ACCD}; }}
        """)
        add_btn.clicked.connect(self.add_row); hl.addWidget(add_btn)
        outer.addWidget(hdr)
        ch = QFrame(); ch.setStyleSheet(f"background:{CARD2}; border:none;"); ch.setFixedHeight(26)
        cl = QHBoxLayout(ch); cl.setContentsMargins(10,0,8,0); cl.setSpacing(5)
        for txt, w in _COL_HDR:
            l = QLabel(txt); l.setStyleSheet(f"color:{TXT3}; font-size:9px; font-weight:700; letter-spacing:1px; background:transparent;")
            if w: l.setFixedWidth(w)
            else: l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cl.addWidget(l)
        outer.addWidget(ch)
        self.rows_container = QWidget(); self.rows_container.setStyleSheet("background:transparent; border:none;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0,0,0,0); self.rows_layout.setSpacing(0)
        outer.addWidget(self.rows_container)

    def _day_date(self): return self.monday + timedelta(days=self.idx) if self.monday else None

    def set_date(self, monday):
        self.monday = monday; d = self._day_date()
        self.date_lbl.setText(f"  ·  {fr_date(d)}")
        for row in self.rows: row.set_date(d)

    def _make_row(self):
        row = RowWidget(self.jour, len(self.rows), self)
        d = self._day_date()
        if d: row.set_date(d)
        row.changed.connect(self._on_change)
        self.rows_layout.addWidget(row); self.rows.append(row)
        return row

    def add_row(self, data=None):
        row = self._make_row()
        if data: row.set_data(data)
        elif len(self.rows) > 1:
            prev = self.rows[-2].end.text().strip()
            if prev: row.start.setText(prev)
        self._on_change(); return row

    def add_blank_row(self): return self._make_row()

    def remove_row(self, row):
        if len(self.rows) <= 1 or row not in self.rows: return
        try: row.changed.disconnect()
        except: pass
        self.rows_layout.removeWidget(row); row.setParent(None); self.rows.remove(row)
        self._on_change(); self.data_changed.emit()

    def clear_all(self):
        for row in self.rows:
            try: row.changed.disconnect()
            except: pass
            self.rows_layout.removeWidget(row); row.setParent(None)
        self.rows.clear()

    def get_total(self): return sum(r.total_h() for r in self.rows)

    def _on_change(self):
        total = self.get_total()
        if total >= 7:   color, bg, brd = GREEN, "#0A2218", GREEN2
        elif total > 0:  color, bg, brd = AMBER, "#211A08", "#92700A"
        else:            color, bg, brd = TXT2,  ACCD,      ACC3
        self.tot_lbl.setText(fmt_h(total) if total else "–")
        self.tot_lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:700; background:transparent;")
        self.tot_badge.setStyleSheet(f"background:{bg}; border-radius:8px; border:1px solid {brd};")
        self.data_changed.emit()

    def get_data(self):
        return [r.get_data() for r in self.rows if r.has_data()]

    def load_data(self, rows_data):
        for d in rows_data:
            if any(d.get(k,"").strip() for k in ("debut","fin","tache","projet","desc")):
                self.add_row(data=d)

# ── HistoriqueDialog ──────────────────────────────────────────────────────────
class HistoriqueDialog(QDialog):
    week_selected = pyqtSignal(datetime)

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Historique — Groupe ADE"); self.setFixedSize(480,560)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        hdr = QFrame(); hdr.setFixedHeight(60)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        hl.addWidget(QLabel("📅")); hl.addSpacing(8)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(lbl("Historique",14,bold=True))
        tc.addWidget(lbl(f"Toutes les semaines enregistrées  ·  {COPYRIGHT}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch(); lay.addWidget(hdr)
        sf = QFrame()
        sf.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:9px; margin:10px 14px 4px 14px;")
        sl = QHBoxLayout(sf); sl.setContentsMargins(10,4,10,4)
        sl.addWidget(QLabel("🔍"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Rechercher une semaine...")
        self.search.setStyleSheet(f"background:transparent; border:none; color:{TXT}; font-size:12px;")
        self.search.textChanged.connect(self._refresh); sl.addWidget(self.search); lay.addWidget(sf)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{BG}; }} QWidget {{ background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget = QWidget(); self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(14,6,14,14); self.list_layout.setSpacing(5)
        self.list_layout.addStretch(); scroll.setWidget(self.list_widget); lay.addWidget(scroll)
        foot = QFrame(); foot.setFixedHeight(28)
        foot.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fl = QHBoxLayout(foot); fl.setContentsMargins(14,0,14,0); fl.addStretch()
        fl.addWidget(lbl(f"{DEV_CREDIT}  ·  Groupe ADE",9,color=TXT3)); lay.addWidget(foot)
        self._refresh()

    def _week_total(self, monday):
        tot = 0.0
        try:
            with open(save_file(monday),"r",encoding="utf-8") as f: d = json.load(f)
            for j in JOURS:
                for r in d.get("jours",{}).get(j,[]):
                    tot += calc_h(r.get("debut",""), r.get("fin",""))
        except: pass
        return tot

    def _refresh(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        q = self.search.text().lower()
        weeks = [m for m in saved_weeks() if not q or q in week_label(m).lower()]
        if not weeks:
            self.list_layout.insertWidget(0, lbl("Aucune semaine enregistrée",12,color=MUTED)); return
        for monday in weeks:
            tot = self._week_total(monday)
            bar_c, bg_c = (GREEN,"#091A10") if tot>=35 else (AMBER,"#1A1408") if tot>0 else (MUTED,CARD)
            card = QFrame()
            card.setStyleSheet(f"background:{bg_c}; border:1px solid {BORDER}; border-radius:10px;"); card.setFixedHeight(58)
            cl = QHBoxLayout(card); cl.setContentsMargins(0,0,12,0); cl.setSpacing(0)
            bar = QFrame(); bar.setFixedWidth(4); bar.setStyleSheet(f"background:{bar_c}; border-radius:2px; margin:8px 0;"); cl.addWidget(bar)
            inf = QWidget(); inf.setStyleSheet("background:transparent;")
            il = QVBoxLayout(inf); il.setContentsMargins(12,8,0,8); il.setSpacing(1)
            il.addWidget(lbl(week_label(monday),11,bold=True))
            il.addWidget(lbl(f"{fmt_h(tot)} travaillées" if tot>0 else "Vide",10,color=TXT2)); cl.addWidget(inf,1)
            btn = QPushButton("Ouvrir →"); btn.setFixedSize(80,26); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ background:{ACCD}; color:{ACC2}; border:1px solid {ACC3}; border-radius:6px; font-size:11px; font-weight:600; }}
                QPushButton:hover {{ background:{ACC3}; color:white; }}
            """)
            btn.clicked.connect(lambda _,m=monday: self._pick(m)); cl.addWidget(btn)
            self.list_layout.insertWidget(self.list_layout.count()-1, card)

    def _pick(self, monday): self.week_selected.emit(monday); self.accept()

# ╔══════════════════════════════════════════════════════════════╗
# ║              ParamDialog — VERSION CORRIGÉE                  ║
# ╚══════════════════════════════════════════════════════════════╝
class ParamDialog(QDialog):
    saved        = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.s = dict(settings)
        self.setWindowTitle("Paramètres — Groupe ADE")
        self.setFixedSize(520, 580)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")

        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QFrame(); hdr.setFixedHeight(64)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0); hl.setSpacing(12)
        ico_lbl = QLabel("⚙️"); ico_lbl.setStyleSheet("font-size:22px; background:transparent;")
        hl.addWidget(ico_lbl)
        tc = QVBoxLayout(); tc.setSpacing(2)
        tc.addWidget(lbl("Paramètres",14,bold=True))
        tc.addWidget(lbl(f"Groupe ADE  ·  {APP_VERSION}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch()
        root.addWidget(hdr)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,16,20,16); bl.setSpacing(14)
        scroll.setWidget(body); root.addWidget(scroll, 1)

        # ── Section 1 : Employé ───────────────────────────────────────────────
        bl.addWidget(self._section_header("👤", "Identité de l'employé"))
        frm1 = card_frame()
        f1l = QVBoxLayout(frm1); f1l.setContentsMargins(16,14,16,16); f1l.setSpacing(6)
        f1l.addWidget(lbl("Nom complet",9,color=TXT3))
        self.emp = styled_entry("Votre nom complet", height=36)
        self.emp.setText(self.s.get("employer",""))
        f1l.addWidget(self.emp)
        f1l.addWidget(lbl("Ce nom apparaîtra sur les feuilles exportées en PDF.",9,color=TXT3))
        bl.addWidget(frm1)

        # ── Section 2 : Courriel ──────────────────────────────────────────────
        bl.addWidget(self._section_header("✉️", "Envoi par courriel"))
        frm2 = card_frame()
        f2l = QVBoxLayout(frm2); f2l.setContentsMargins(16,14,16,16); f2l.setSpacing(10)

        f2l.addWidget(lbl("Destinataire — champ « À : »",9,color=TXT3))
        self.email_dest = styled_entry("superviseur@groupeade.com", height=36)
        self.email_dest.setText(self.s.get("email_dest","")); f2l.addWidget(self.email_dest)

        f2l.addWidget(lbl("Copie conforme — champ « CC : »  (optionnel)",9,color=TXT3))
        self.email_cc = styled_entry("rh@groupeade.com  ou  laisser vide", height=36)
        self.email_cc.setText(self.s.get("email_cc","")); f2l.addWidget(self.email_cc)

        hint = lbl("💡 Ces adresses sont pré-remplies dans la fenêtre d'envoi et modifiables à chaque fois.",9,color=TXT3)
        hint.setWordWrap(True); f2l.addWidget(hint)
        bl.addWidget(frm2)

        # ── Section 3 : Thème ────────────────────────────────────────────────
        bl.addWidget(self._section_header("🎨", "Thème d'affichage"))
        frm3 = card_frame()
        f3l = QVBoxLayout(frm3); f3l.setContentsMargins(16,14,16,16); f3l.setSpacing(10)

        f3l.addWidget(lbl("Choisir un thème  (appliqué immédiatement, sans redémarrage)",9,color=TXT3))

        # Combo thème
        self.theme_combo = QComboBox()
        for name in THEMES:
            self.theme_combo.addItem(name)
        cur = self.s.get("theme","Dark Navy")
        idx = self.theme_combo.findText(cur)
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentTextChanged.connect(self._preview_theme)
        f3l.addWidget(self.theme_combo)

        # Swatches visuels
        self.swatch_row = QHBoxLayout(); self.swatch_row.setSpacing(6)
        self._build_swatches()
        f3l.addLayout(self.swatch_row)

        note = lbl("⚠️ Le thème n'affecte pas le rendu PDF — celui-ci est toujours en mode Dark Navy ADE.",9,color=AMBER)
        note.setWordWrap(True); f3l.addWidget(note)
        bl.addWidget(frm3)
        bl.addStretch()

        # ── Bouton Enregistrer ────────────────────────────────────────────────
        foot_widget = QWidget(); foot_widget.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fw = QHBoxLayout(foot_widget); fw.setContentsMargins(20,10,20,10); fw.setSpacing(10)
        fw.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); fw.addStretch()

        cancel_btn = QPushButton("Annuler"); cancel_btn.setFixedHeight(38); cancel_btn.setFixedWidth(100)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background:{CARD2}; color:{TXT2}; border:1px solid {BORDER}; border-radius:9px; font-size:12px; }}
            QPushButton:hover {{ background:{CARD}; color:{TXT}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("💾  Enregistrer"); save_btn.setFixedHeight(38); save_btn.setFixedWidth(140)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                          color:white; border:none; border-radius:9px; font-size:13px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC}; }}
        """)
        save_btn.clicked.connect(self._save)
        fw.addWidget(cancel_btn); fw.addWidget(save_btn)
        root.addWidget(foot_widget)

    def _section_header(self, icon, title):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w); hl.setContentsMargins(0,4,0,0); hl.setSpacing(6)
        hl.addWidget(QLabel(icon))
        hl.addWidget(lbl(title, 11, bold=True))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; background:{BORDER};"); sep.setFixedHeight(1)
        hl.addWidget(sep, 1); return w

    def _build_swatches(self):
        # Vider les swatches existants
        while self.swatch_row.count():
            item = self.swatch_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        cur = self.theme_combo.currentText()
        for name, tdata in THEMES.items():
            btn = QPushButton()
            btn.setFixedSize(36, 28)
            btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            acc = tdata["ACC"]; bg = tdata["BG2"]; card = tdata["CARD"]
            border = "2px solid white" if name == cur else f"1px solid {tdata['BORDER2']}"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {bg},stop:0.5 {card},stop:1 {acc});
                    border:{border}; border-radius:6px;
                }}
                QPushButton:hover {{ border:2px solid {acc}; }}
            """)
            btn.clicked.connect(lambda _, n=name: self._select_theme(n))
            self.swatch_row.addWidget(btn)
        self.swatch_row.addStretch()

    def _select_theme(self, name):
        idx = self.theme_combo.findText(name)
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)

    def _preview_theme(self, name):
        apply_theme(name)
        self.s["theme"] = name
        self.theme_changed.emit(name)
        self._build_swatches()

    def _save(self):
        self.s["employer"]   = self.emp.text().strip()
        self.s["email_dest"] = self.email_dest.text().strip()
        self.s["email_cc"]   = self.email_cc.text().strip()
        self.s["theme"]      = self.theme_combo.currentText()
        self.saved.emit(self.s); self.accept()

# ── EnvoiDialog ───────────────────────────────────────────────────────────────
class EnvoiDialog(QDialog):
    def __init__(self, parent, employer, week_lbl, total_h, pdf_path, settings):
        super().__init__(parent)
        self.pdf_path = pdf_path; self.settings = settings
        self.setWindowTitle("Envoyer la feuille de temps — Groupe ADE")
        self.setFixedSize(560, 630)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        hdr = QFrame(); hdr.setFixedHeight(62)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        ico = QLabel("✉️"); ico.setStyleSheet("font-size:22px; background:transparent;")
        hl.addWidget(ico); hl.addSpacing(8)
        tc = QVBoxLayout(); tc.setSpacing(1)
        tc.addWidget(lbl("Envoyer la feuille de temps",14,bold=True))
        tc.addWidget(lbl(f"Semaine du {week_lbl}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch(); lay.addWidget(hdr)
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,16,20,16); bl.setSpacing(10)
        ff = QFrame(); ff.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:12px;")
        ffl = QVBoxLayout(ff); ffl.setContentsMargins(14,12,14,14); ffl.setSpacing(8)

        def addr_row(label_txt, placeholder, value):
            row = QHBoxLayout()
            lbl_w = lbl(label_txt,11,bold=True,color=TXT2); lbl_w.setFixedWidth(44); row.addWidget(lbl_w)
            e = styled_entry(placeholder, height=32); e.setText(value); row.addWidget(e)
            ffl.addLayout(row); return e

        self.to_entry   = addr_row("À :",    "superviseur@groupeade.com", settings.get("email_dest",""))
        self.cc_entry   = addr_row("CC :",   "optionnel",                  settings.get("email_cc",""))
        self.subj_entry = addr_row("Objet :", "",                          f"Feuille de temps — {employer} — Semaine du {week_lbl}")
        bl.addWidget(ff)
        bl.addWidget(lbl("Message :",10,bold=True,color=TXT2))
        self.msg_edit = QTextEdit(); self.msg_edit.setFixedHeight(175)
        self.msg_edit.setStyleSheet(f"""
            QTextEdit {{ background:{CARD}; color:{TXT}; border:1px solid {BORDER}; border-radius:10px;
                        padding:10px; font-family:'Segoe UI'; font-size:13px; }}
            QTextEdit:focus {{ border-color:{ACC}; }}
        """)
        self.msg_edit.setPlainText(
            f"Bonjour,\n\nVeuillez trouver ci-joint ma feuille de temps pour la semaine du {week_lbl}.\n\n"
            f"Total des heures : {total_h}\n\nCordialement,\n{employer}"
        )
        bl.addWidget(self.msg_edit)
        att_row = QHBoxLayout(); att_row.setSpacing(8)
        att_row.addWidget(QLabel("📎"))
        fname = os.path.basename(pdf_path) if pdf_path and os.path.exists(pdf_path) else None
        att_lbl = lbl(fname, 10, color=TXT2) if fname else lbl("PDF non encore généré — sera créé automatiquement", 10, color=AMBER)
        att_row.addWidget(att_lbl); att_row.addStretch(); bl.addLayout(att_row)
        hint = lbl("💡 Votre client de messagerie s'ouvrira avec le courriel prêt.\n    Glissez-déposez le PDF dans le courriel avant d'envoyer.", 9, color=TXT3)
        hint.setWordWrap(True); bl.addWidget(hint)
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel_btn = QPushButton("Annuler"); cancel_btn.setFixedHeight(40)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background:{CARD2}; color:{TXT2}; border:1px solid {BORDER}; border-radius:9px; font-size:12px; }}
            QPushButton:hover {{ background:{CARD}; color:{TXT}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        self.send_btn = QPushButton("✉️  Ouvrir dans mon client mail")
        self.send_btn.setFixedHeight(40); self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                          color:white; border:none; border-radius:9px; font-size:13px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC}; }}
        """)
        self.send_btn.clicked.connect(self._open_mail)
        btn_row.addWidget(cancel_btn); btn_row.addWidget(self.send_btn, 1); bl.addLayout(btn_row)
        lay.addWidget(body)
        foot = QFrame(); foot.setFixedHeight(28)
        foot.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fl = QHBoxLayout(foot); fl.setContentsMargins(14,0,14,0); fl.addStretch()
        fl.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); lay.addWidget(foot)

    def _open_mail(self):
        to = self.to_entry.text().strip(); cc = self.cc_entry.text().strip()
        subj = self.subj_entry.text().strip(); body = self.msg_edit.toPlainText().strip()
        if not to:
            QMessageBox.warning(self, "Destinataire manquant", "Veuillez entrer une adresse dans le champ « À ».")
            self.to_entry.setFocus(); return
        self.settings["email_dest"] = to; self.settings["email_cc"] = cc
        write_settings(self.settings)
        params = {"subject": subj, "body": body}
        if cc: params["cc"] = cc
        query      = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        mailto_uri = f"mailto:{urllib.parse.quote(to)}?{query}"
        try:
            if sys.platform == "win32":
                os.startfile(mailto_uri)
                if self.pdf_path and os.path.exists(self.pdf_path):
                    subprocess.Popen(["explorer", "/select,", self.pdf_path], creationflags=subprocess.CREATE_NO_WINDOW)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", mailto_uri])
                if self.pdf_path and os.path.exists(self.pdf_path):
                    subprocess.Popen(["open", "-R", self.pdf_path])
            else:
                subprocess.Popen(["xdg-open", mailto_uri])
            msg = ("✓ Votre client de messagerie s'est ouvert avec le courriel prêt.\n\n"
                   f"📎 Le dossier contenant le PDF s'est aussi ouvert :\n   {os.path.basename(self.pdf_path)}\n\n"
                   "Glissez-déposez le PDF dans le courriel, puis cliquez Envoyer."
                   if self.pdf_path and os.path.exists(self.pdf_path)
                   else "✓ Votre client de messagerie s'est ouvert avec le courriel prêt à envoyer.")
            QMessageBox.information(self, "Courriel préparé — Groupe ADE", msg)
            self.accept()
        except Exception as ex:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le client mail :\n{ex}")

# ╔══════════════════════════════════════════════════════════════╗
# ║              StatsDialog — VERSION ENRICHIE                 ║
# ╚══════════════════════════════════════════════════════════════╝
class StatsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Statistiques — Groupe ADE"); self.resize(980, 820)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        self._load(); self._build()

    def _load(self):
        self.weeks = []
        self.proj_totals  = {}
        self.tache_totals = {}
        self.all_day_hours: list[float] = []   # toutes les journées avec heures > 0
        self.matin_h  = 0.0   # heures avant 12h
        self.aprem_h  = 0.0   # heures après 12h

        weeks_sorted = sorted(saved_weeks())   # croissant pour le streak
        for monday in weeks_sorted:
            try:
                with open(save_file(monday),"r",encoding="utf-8") as f: d = json.load(f)
                total = 0.0; jour_h = {}
                for j in JOURS:
                    jt = 0.0
                    for r in d.get("jours",{}).get(j,[]):
                        h = calc_h(r.get("debut",""), r.get("fin",""))
                        jt += h
                        # Par projet
                        p = r.get("projet","").strip()
                        if p and h > 0: self.proj_totals[p] = self.proj_totals.get(p,0.0)+h
                        # Par tâche
                        t = r.get("tache","").strip()
                        if t and h > 0: self.tache_totals[t] = self.tache_totals.get(t,0.0)+h
                        # Distribution matin/après-midi
                        s = parse_heure(r.get("debut",""))
                        e = parse_heure(r.get("fin",""))
                        if s and e and e > s:
                            noon = s.replace(hour=12, minute=0, second=0)
                            if e <= noon:
                                self.matin_h += h
                            elif s >= noon:
                                self.aprem_h += h
                            else:
                                # chevauchement midi
                                mat = (noon - s).seconds/3600
                                apr = (e - noon).seconds/3600
                                self.matin_h += mat; self.aprem_h += apr
                    jour_h[j] = jt; total += jt
                    if jt > 0: self.all_day_hours.append(jt)
                self.weeks.append({"monday":monday,"label":week_label(monday),"total":total,"jours":jour_h})
            except: pass

        # Streak (semaines complètes consécutives jusqu'à aujourd'hui)
        self.streak = 0
        today_monday = get_monday(datetime.today())
        check = today_monday
        week_map = {w["monday"].date(): w for w in self.weeks}
        while True:
            wk = week_map.get(check.date())
            if wk and wk["total"] >= 35:
                self.streak += 1
                check -= timedelta(weeks=1)
            else:
                break

        # Meilleure journée (heure max en une seule journée)
        self.best_day_h = max(self.all_day_hours) if self.all_day_hours else 0.0

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        # Header
        hdr = QFrame(); hdr.setFixedHeight(60)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(22,0,22,0)
        hl.addWidget(QLabel("📊")); hl.addSpacing(8)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(lbl("Statistiques",14,bold=True))
        tc.addWidget(lbl(f"Rapport de {len(self.weeks)} semaine(s)  ·  {COPYRIGHT}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch(); lay.addWidget(hdr)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; }} QWidget {{ background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(); cl = QVBoxLayout(content)
        cl.setContentsMargins(16,16,16,16); cl.setSpacing(14)
        scroll.setWidget(content); lay.addWidget(scroll)

        if not self.weeks:
            cl.addWidget(lbl("Aucune donnée disponible.",14,color=MUTED)); cl.addStretch()
            self._footer(lay); return

        totals   = [w["total"] for w in self.weeks]
        non_zero = [t for t in totals if t>0]
        best_wk  = max(self.weeks, key=lambda w: w["total"]) if self.weeks else None

        # ── Rangée 1 : 4 KPI principaux ──────────────────────────────────────
        cl.addWidget(self._sec_title("Vue d'ensemble"))
        cr = QHBoxLayout(); cr.setSpacing(10)
        for title, val, color, sub, icon in [
            ("Total cumulé",   fmt_h(sum(totals)),   ACC,   f"{len(non_zero)} sem. actives","⏱"),
            ("Moyenne / sem.", fmt_h(sum(non_zero)/len(non_zero)) if non_zero else "–", GREEN, f"sur {len(non_zero)} sem.","📈"),
            ("Meilleure sem.", fmt_h(max(totals)) if totals else "–", AMBER, best_wk["label"] if best_wk and best_wk["total"]>0 else "–","🏆"),
            ("Sem. actives",   str(len(non_zero)), ACC2, f"sur {len(self.weeks)} total","📅"),
        ]:
            cr.addWidget(self._kpi_card(title, val, color, sub, icon))
        cl.addLayout(cr)

        # ── Rangée 2 : KPI supplémentaires ───────────────────────────────────
        cr2 = QHBoxLayout(); cr2.setSpacing(10)
        # Streak
        streak_col = GREEN if self.streak >= 4 else AMBER if self.streak >= 1 else MUTED
        cr2.addWidget(self._kpi_card("Série en cours",
            f"{self.streak} sem." if self.streak else "–",
            streak_col,
            "semaines complètes (≥35h) consécutives","🔥"))
        # Meilleure journée
        cr2.addWidget(self._kpi_card("Record journalier",
            fmt_h(self.best_day_h) if self.best_day_h else "–",
            ACC2, "meilleure journée toutes semaines","⚡"))
        # Distribution matin/après-midi
        total_dist = self.matin_h + self.aprem_h
        if total_dist > 0:
            mat_pct = int(self.matin_h / total_dist * 100)
            apr_pct = 100 - mat_pct
            dist_txt = f"{mat_pct}% matin"
            dist_sub = f"{apr_pct}% après-midi"
        else:
            dist_txt = "–"; dist_sub = "données insuffisantes"
        cr2.addWidget(self._kpi_card("Distribution horaire", dist_txt, "#A78BFA", dist_sub,"🌅"))
        # Nb projets distincts
        cr2.addWidget(self._kpi_card("Projets distincts",
            str(len(self.proj_totals)) if self.proj_totals else "0",
            PALETTE[1], f"{len(self.tache_totals)} tâche(s) différente(s)","📂"))
        cl.addLayout(cr2)

        # ── Section : Heures par projet ───────────────────────────────────────
        if self.proj_totals:
            cl.addWidget(self._sec_title("Répartition par projet"))
            pc = card_frame()
            pl = QVBoxLayout(pc); pl.setContentsMargins(16,14,16,14); pl.setSpacing(7)
            all_h = sum(self.proj_totals.values()); max_h = max(self.proj_totals.values())
            for idx,(proj,h) in enumerate(sorted(self.proj_totals.items(),key=lambda x:x[1],reverse=True)):
                color = PALETTE[idx%len(PALETTE)]
                pl.addWidget(self._bar_row(proj, h, all_h, max_h, color))
            cl.addWidget(pc)

        # ── Section : Heures par tâche ────────────────────────────────────────
        if self.tache_totals:
            cl.addWidget(self._sec_title("Répartition par tâche"))
            tc2 = card_frame()
            tl = QVBoxLayout(tc2); tl.setContentsMargins(16,14,16,14); tl.setSpacing(7)
            all_h2 = sum(self.tache_totals.values()); max_h2 = max(self.tache_totals.values())
            for idx,(tache,h) in enumerate(sorted(self.tache_totals.items(),key=lambda x:x[1],reverse=True)):
                color = PALETTE[(idx+3)%len(PALETTE)]
                tl.addWidget(self._bar_row(tache, h, all_h2, max_h2, color))
            cl.addWidget(tc2)

        # ── Section : Moy par jour ────────────────────────────────────────────
        cl.addWidget(self._sec_title("Moyenne par jour de la semaine"))
        dc = card_frame()
        dl = QVBoxLayout(dc); dl.setContentsMargins(16,14,16,14); dl.setSpacing(8)
        sums={j:0.0 for j in JOURS}; cnts={j:0 for j in JOURS}
        best_jour_h = 0.0; best_jour_name = ""
        for wk in self.weeks:
            for j in JOURS:
                v = wk["jours"].get(j,0)
                if v > 0: sums[j]+=v; cnts[j]+=1
        avgs = {j:(sums[j]/cnts[j] if cnts[j] else 0) for j in JOURS}
        max_avg = max(avgs.values()) or 1
        for j, avg in avgs.items():
            if avg > best_jour_h: best_jour_h = avg; best_jour_name = j
        for j in JOURS:
            avg = avgs[j]
            r = QHBoxLayout(); r.setSpacing(10)
            jl = lbl(j,11,color=TXT2); jl.setFixedWidth(80); r.addWidget(jl)
            is_best = (j == best_jour_name and avg > 0)
            prog_color = GREEN if is_best else f"qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC})"
            prog = QProgressBar(); prog.setValue(int(avg/max_avg*100) if avg else 0)
            prog.setFixedHeight(10); prog.setTextVisible(False)
            prog.setStyleSheet(f"""
                QProgressBar {{ background:{BG2}; border-radius:5px; border:none; }}
                QProgressBar::chunk {{ background:{prog_color}; border-radius:5px; }}
            """)
            r.addWidget(prog,1)
            val_lbl = lbl(fmt_h(avg) if avg else "–", 11, bold=True, color=GREEN if is_best else (ACC2 if avg else MUTED))
            r.addWidget(val_lbl)
            if is_best:
                r.addWidget(lbl("★ meilleur",9,color=GREEN))
            dl.addLayout(r)
        cl.addWidget(dc)

        # ── Section : Distribution hebdo ──────────────────────────────────────
        cl.addWidget(self._sec_title("Distribution des semaines"))
        distr = card_frame()
        drl = QHBoxLayout(distr); drl.setContentsMargins(16,14,16,14); drl.setSpacing(16)
        buckets = {"< 20h":0,"20–35h":0,"35–40h":0,"≥ 40h":0}
        for t in totals:
            if t < 20:   buckets["< 20h"] += 1
            elif t < 35: buckets["20–35h"] += 1
            elif t < 40: buckets["35–40h"] += 1
            else:         buckets["≥ 40h"] += 1
        b_colors = [RED, AMBER, ACC, GREEN]
        for (label, cnt), color in zip(buckets.items(), b_colors):
            bw = QWidget(); bw.setStyleSheet("background:transparent;")
            bwl = QVBoxLayout(bw); bwl.setContentsMargins(0,0,0,0); bwl.setSpacing(4); bwl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            val_l = lbl(str(cnt),20,bold=True,color=color)
            val_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            name_l = lbl(label,10,color=TXT2)
            name_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            pct_l = lbl(f"{cnt/len(totals)*100:.0f}%" if totals else "–",9,color=TXT3)
            pct_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            bwl.addWidget(val_l); bwl.addWidget(name_l); bwl.addWidget(pct_l)
            drl.addWidget(bw,1)
        cl.addWidget(distr)

        # ── Section : Tableau détail semaines ─────────────────────────────────
        cl.addWidget(self._sec_title("Détail par semaine"))
        tc3 = card_frame()
        tl3 = QVBoxLayout(tc3); tl3.setContentsMargins(16,14,16,14); tl3.setSpacing(0)
        hd = QFrame(); hd.setStyleSheet(f"background:{CARD2}; border-radius:7px;")
        hdl = QHBoxLayout(hd); hdl.setContentsMargins(12,6,10,6); hdl.setSpacing(4)
        for txt,w in [("Semaine",0),("Lun",60),("Mar",60),("Mer",60),("Jeu",60),("Ven",60),("Total",80)]:
            lh = QLabel(txt); lh.setStyleSheet(f"color:{TXT3}; font-size:9px; font-weight:700; letter-spacing:1px; background:transparent;")
            if w: lh.setFixedWidth(w)
            else: lh.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hdl.addWidget(lh)
        tl3.addWidget(hd)
        for i,wk in enumerate(reversed(self.weeks)):
            row = QFrame(); row.setStyleSheet(f"background:{ROW if i%2==0 else CARD}; border-radius:0;"); row.setFixedHeight(34)
            rl2 = QHBoxLayout(row); rl2.setContentsMargins(12,0,10,0); rl2.setSpacing(4)
            rl2.addWidget(lbl(wk["label"],10))
            for j in JOURS:
                v=wk["jours"].get(j,0); col = GREEN if v>=7 else TXT2 if v>0 else MUTED
                l2 = lbl(fmt_h(v) if v else "–",10,color=col); l2.setFixedWidth(60); rl2.addWidget(l2)
            tc_col = GREEN if wk["total"]>=35 else AMBER if wk["total"]>0 else MUTED
            tl_r = lbl(fmt_h(wk["total"]) if wk["total"] else "–",10,bold=True,color=tc_col)
            tl_r.setFixedWidth(80); rl2.addWidget(tl_r); tl3.addWidget(row)
        cl.addWidget(tc3); cl.addStretch()
        self._footer(lay)

    def _sec_title(self, text):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w); hl.setContentsMargins(2,4,0,0); hl.setSpacing(8)
        dot = QFrame(); dot.setFixedSize(6,6); dot.setStyleSheet(f"background:{ACC}; border-radius:3px;")
        hl.addWidget(dot); hl.addWidget(lbl(text,11,bold=True)); hl.addStretch(); return w

    def _kpi_card(self, title, val, color, sub, icon):
        c = QFrame(); c.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-top:2px solid {color}; border-radius:12px;")
        cv = QVBoxLayout(c); cv.setContentsMargins(14,12,14,12); cv.setSpacing(3)
        th = QHBoxLayout(); th.addWidget(lbl(title,10,bold=True,color=TXT2)); th.addStretch(); th.addWidget(QLabel(icon))
        cv.addLayout(th); cv.addWidget(lbl(val,20,bold=True,color=color)); cv.addWidget(lbl(sub,9,color=TXT3))
        return c

    def _bar_row(self, name, h, all_h, max_h, color):
        row = QFrame(); row.setStyleSheet(f"background:{CARD2}; border-radius:9px; border:none;")
        rl = QHBoxLayout(row); rl.setContentsMargins(0,7,12,7); rl.setSpacing(0)
        bl2 = QFrame(); bl2.setFixedWidth(4); bl2.setStyleSheet(f"background:{color}; border-radius:2px; margin:4px 0;"); rl.addWidget(bl2)
        info = QWidget(); info.setStyleSheet("background:transparent;")
        il = QVBoxLayout(info); il.setContentsMargins(12,0,0,0); il.setSpacing(4)
        tr = QHBoxLayout(); tr.addWidget(lbl(name,11,bold=True)); tr.addStretch()
        tr.addWidget(lbl(f"{fmt_h(h)}  ·  {h/all_h*100:.1f}%",11,color=color)); il.addLayout(tr)
        prog = QProgressBar(); prog.setValue(int(h/max_h*100)); prog.setFixedHeight(5); prog.setTextVisible(False)
        prog.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:2px; border:none; }} QProgressBar::chunk {{ background:{color}; border-radius:2px; }}")
        il.addWidget(prog); rl.addWidget(info); return row

    def _footer(self, lay):
        foot = QFrame(); foot.setFixedHeight(30)
        foot.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fl = QHBoxLayout(foot); fl.setContentsMargins(20,0,20,0)
        fl.addWidget(lbl(f"Groupe ADE  ·  {APP_VERSION}",9,color=TXT3)); fl.addStretch()
        fl.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); lay.addWidget(foot)

# ── StatusBar ─────────────────────────────────────────────────────────────────
class StatusBar(QFrame):
    def __init__(self):
        super().__init__(); self.setFixedHeight(34)
        self.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        lay = QHBoxLayout(self); lay.setContentsMargins(16,0,16,0)
        self.dot = QLabel("●"); self.dot.setStyleSheet(f"color:{GREEN}; font-size:9px; background:transparent;")
        self.msg = lbl("✓ Prêt",10,color=GREEN)
        lay.addWidget(self.dot); lay.addSpacing(4); lay.addWidget(self.msg); lay.addStretch()
        for t in (DEV_CREDIT,"  ·  ",COPYRIGHT,"  ·  ",f"Groupe ADE  {APP_VERSION}"):
            lay.addWidget(lbl(t,9,bold=t.startswith("Groupe"),color=TXT3))

    def set(self, text, color):
        self.dot.setStyleSheet(f"color:{color}; font-size:9px; background:transparent;")
        self.msg.setText(text); self.msg.setStyleSheet(f"color:{color}; background:transparent; font-size:10px;")

def _save_ss():
    return f"""
    QPushButton {{
        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
        color:white; border:none; border-radius:9px; font-family:'Segoe UI'; font-size:12px; font-weight:600;
    }}
    QPushButton:hover {{ background:{ACC}; }}
    QPushButton:pressed {{ background:{ACCD}; }}
"""

# ── MainWindow ────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Groupe ADE — Feuille de Temps  {APP_VERSION}")
        self.resize(1540, 840); self.setMinimumSize(1160, 660)

        self.today    = datetime.today()
        self.monday   = get_monday(self.today)
        self.settings = load_settings()
        # Appliquer le thème sauvegardé
        apply_theme(self.settings.get("theme","Dark Navy"))
        self.setStyleSheet(ss_base())

        self.day_cards = {}
        self._dirty    = False
        self._last_pdf = ""

        AutoCompleteRegistry.load_all()
        self._build()
        self._load_week(self.monday)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start(30_000)
        QTimer.singleShot(2000, self._start_update_check)

    def closeEvent(self, event): self._save(silent=True); event.accept()

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        ml = QHBoxLayout(central); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        ml.addWidget(self._build_sidebar())
        sep = QFrame(); sep.setFixedWidth(1); sep.setStyleSheet(f"background:{BORDER}"); ml.addWidget(sep)
        right = QWidget(); right.setStyleSheet(f"background:{BG};")
        rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        rl.addWidget(self._build_topbar())
        rl.addWidget(self._build_scroll(), 1)
        self.status_bar = StatusBar(); rl.addWidget(self.status_bar)
        ml.addWidget(right, 1)

    def _build_sidebar(self):
        sb = QFrame(); sb.setFixedWidth(220)
        sb.setStyleSheet(f"background:{BG2}; border:none;")
        lay = QVBoxLayout(sb); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        lay.addWidget(LogoWidget()); lay.addWidget(h_sep())

        # Semaine nav
        nav = QWidget(); nav.setStyleSheet("background:transparent;")
        nl = QVBoxLayout(nav); nl.setContentsMargins(10,10,10,8); nl.setSpacing(6)
        nl.addWidget(section_lbl("SEMAINE"))
        nb = QWidget(); nb.setStyleSheet("background:transparent;")
        nbl = QHBoxLayout(nb); nbl.setContentsMargins(0,0,0,0); nbl.setSpacing(4)
        self.btn_prev = self._nav_btn("◀"); self.btn_next = self._nav_btn("▶")
        self.week_lbl = QLabel("")
        self.week_lbl.setWordWrap(True); self.week_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.week_lbl.setStyleSheet(f"color:{TXT}; font-size:10px; font-weight:600; background:transparent;")
        nbl.addWidget(self.btn_prev); nbl.addWidget(self.week_lbl,1); nbl.addWidget(self.btn_next)
        self.btn_prev.clicked.connect(self._prev); self.btn_next.clicked.connect(self._next)
        nl.addWidget(nb)
        today_btn = QPushButton("● Aujourd'hui"); today_btn.setFixedHeight(30)
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setStyleSheet(f"""
            QPushButton {{ background:{ACCD}; color:{ACC2}; border:1px solid {ACC3}; border-radius:8px; font-size:11px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC3}; color:white; }}
        """)
        today_btn.clicked.connect(self._today); nl.addWidget(today_btn)
        lay.addWidget(nav); lay.addWidget(h_sep())

        # Résumé
        res = QWidget(); res.setStyleSheet("background:transparent;")
        rl2 = QVBoxLayout(res); rl2.setContentsMargins(12,10,12,10); rl2.setSpacing(6)
        rl2.addWidget(section_lbl("RÉSUMÉ"))
        tot_frame = QFrame()
        tot_frame.setStyleSheet(f"""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {ACCD},stop:1 {BG3});
            border:1px solid {ACC3}; border-radius:12px;
        """)
        tfl = QVBoxLayout(tot_frame); tfl.setContentsMargins(14,10,14,10); tfl.setSpacing(2)
        self.total_big = QLabel("0h")
        self.total_big.setStyleSheet(f"color:{ACC2}; font-family:'Segoe UI'; font-size:28px; font-weight:800; background:transparent;")
        tfl.addWidget(self.total_big); tfl.addWidget(lbl("heures cette semaine",10,color=TXT2))
        self.prog = QProgressBar(); self.prog.setFixedHeight(5); self.prog.setTextVisible(False)
        self.prog.setStyleSheet(f"""
            QProgressBar {{ background:{BG}; border-radius:2px; border:none; margin-top:4px; }}
            QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC}); border-radius:2px; }}
        """)
        tfl.addWidget(self.prog); rl2.addWidget(tot_frame)
        lay.addWidget(res); lay.addWidget(h_sep())

        # Actions
        act = QWidget(); act.setStyleSheet("background:transparent;")
        al = QVBoxLayout(act); al.setContentsMargins(10,8,10,6); al.setSpacing(3)
        al.addWidget(section_lbl("ACTIONS"))
        for text, cmd in [("📅  Historique",self._historique),("📊  Statistiques",self._stats),
                          ("📄  Exporter PDF",self._pdf),("⚙️   Paramètres",self._parametres)]:
            b = sidebar_btn(text); b.clicked.connect(cmd); al.addWidget(b)
        self.send_mail_btn = QPushButton("✉️  Envoyer par courriel")
        self.send_mail_btn.setFixedHeight(34)
        self.send_mail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_mail_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCD},stop:1 #1E2E60);
                color:{ACC2}; border:1px solid {ACC3}; border-radius:8px;
                padding:0 10px; font-size:11px; font-weight:700;
            }}
            QPushButton:hover {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                color:white; border-color:{ACC};
            }}
            QPushButton:pressed {{ background:{ACCD}; }}
        """)
        self.send_mail_btn.clicked.connect(self._envoyer_courriel)
        al.addWidget(self.send_mail_btn)
        lay.addWidget(act); lay.addWidget(h_sep())

        # Transfert
        tr = QWidget(); tr.setStyleSheet("background:transparent;")
        tl2 = QVBoxLayout(tr); tl2.setContentsMargins(10,8,10,6); tl2.setSpacing(3)
        tl2.addWidget(section_lbl("TRANSFERT"))
        for text, cmd in [("📤  Exporter .zip",self._export_zip),("📥  Importer .zip",self._import_zip),
                          ("📁  Ouvrir le dossier",self._open_folder)]:
            b = sidebar_btn(text); b.clicked.connect(cmd); tl2.addWidget(b)
        lay.addWidget(tr); lay.addStretch()

        # Update frame
        self.update_frame = QFrame()
        self.update_frame.setStyleSheet(f"""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1A2E10,stop:1 #0F1E0A);
            border:1px solid {GREEN2}; border-radius:10px; margin:0 10px;
        """)
        ufl = QVBoxLayout(self.update_frame); ufl.setContentsMargins(10,8,10,8); ufl.setSpacing(4)
        ul1 = QHBoxLayout(); ul1.addWidget(QLabel("🟢")); ul1.addSpacing(4)
        self.update_ver_lbl = lbl("Mise à jour disponible",10,bold=True,color=GREEN)
        ul1.addWidget(self.update_ver_lbl); ul1.addStretch(); ufl.addLayout(ul1)
        self.update_notes_lbl = lbl("",9,color=TXT2); self.update_notes_lbl.setWordWrap(True); ufl.addWidget(self.update_notes_lbl)
        self.update_btn = QPushButton("⬇  Installer la mise à jour"); self.update_btn.setFixedHeight(30)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {GREEN2},stop:1 {GREEN});
                          color:#0A1A0A; border:none; border-radius:7px; font-size:11px; font-weight:700; }}
            QPushButton:hover {{ background:{GREEN}; }}
            QPushButton:disabled {{ background:{MUTED}; color:{TXT3}; }}
        """)
        self.update_btn.clicked.connect(self._do_update); ufl.addWidget(self.update_btn)
        self.update_prog = QProgressBar(); self.update_prog.setFixedHeight(5); self.update_prog.setTextVisible(False)
        self.update_prog.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:2px; border:none; }} QProgressBar::chunk {{ background:{GREEN}; border-radius:2px; }}")
        self.update_prog.hide(); ufl.addWidget(self.update_prog)
        self.update_frame.hide(); lay.addWidget(self.update_frame); lay.addSpacing(4)

        foot = QFrame(); foot.setFixedHeight(46)
        foot.setStyleSheet(f"background:{BG}; border-top:1px solid {BORDER};")
        fl = QVBoxLayout(foot); fl.setContentsMargins(12,5,12,5); fl.setSpacing(1)
        fl.addWidget(lbl(f"Groupe ADE  ·  {APP_VERSION}",9,bold=True,color=TXT2))
        fl.addWidget(lbl(COPYRIGHT,8,color=TXT3)); lay.addWidget(foot)
        return sb

    def _nav_btn(self, text):
        b = QPushButton(text); b.setFixedSize(28,28); b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{ background:{CARD}; color:{TXT2}; border:1px solid {BORDER}; border-radius:7px; font-size:11px; }}
            QPushButton:hover {{ background:{CARD2}; color:{TXT}; border-color:{ACC3}; }}
        """)
        return b

    def _build_topbar(self):
        top = QFrame(); top.setFixedHeight(54)
        top.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        tl = QHBoxLayout(top); tl.setContentsMargins(18,0,18,0); tl.setSpacing(12)
        tl.addWidget(lbl("Employé",10,bold=True,color=TXT3))
        self.emp_entry = styled_entry("Votre nom",230,34)
        self.emp_entry.setText(self.settings.get("employer",""))
        self.emp_entry.textChanged.connect(self._mark_dirty); tl.addWidget(self.emp_entry)
        self.week_info_lbl = lbl("",11,color=TXT2); tl.addWidget(self.week_info_lbl); tl.addStretch()
        self.week_total_lbl = QLabel("Total : 0h")
        self.week_total_lbl.setStyleSheet(f"color:{ACC2}; font-size:14px; font-weight:700; background:{ACCD}; border:1px solid {ACC3}; border-radius:9px; padding:3px 14px;")
        tl.addWidget(self.week_total_lbl)
        self.save_btn = QPushButton("💾  Sauvegarder"); self.save_btn.setFixedSize(148,36)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor); self.save_btn.setStyleSheet(_save_ss())
        self.save_btn.clicked.connect(self._save); tl.addWidget(self.save_btn)
        return top

    def _build_scroll(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(); content.setStyleSheet(f"background:{BG};")
        cl = QVBoxLayout(content); cl.setContentsMargins(14,12,14,12); cl.setSpacing(10)
        for i, j in enumerate(JOURS):
            card = DayCard(j, i); card.data_changed.connect(self._recalc_week)
            self.day_cards[j] = card; cl.addWidget(card)
        cl.addStretch(); scroll.setWidget(content); return scroll

    # ── Nav ───────────────────────────────────────────────────────────────────
    def _prev(self):
        self._save(silent=True); self.monday -= timedelta(weeks=1); self._last_pdf=""; self._switch()
    def _next(self):
        self._save(silent=True); self.monday += timedelta(weeks=1); self._last_pdf=""; self._switch()
    def _today(self):
        self._save(silent=True); self.monday=get_monday(self.today); self._last_pdf=""; self._switch()
    def _switch(self):
        for j in JOURS: self.day_cards[j].clear_all()
        self._load_week(self.monday)

    def _load_week(self, monday):
        lbl_txt = week_label(monday)
        self.week_lbl.setText(lbl_txt); self.week_info_lbl.setText(f"Semaine du {lbl_txt}")
        for j in JOURS: self.day_cards[j].set_date(monday)
        sf = save_file(monday); loaded = False
        if os.path.exists(sf):
            try:
                with open(sf,"r",encoding="utf-8") as f: d = json.load(f)
                emp = d.get("employer","")
                if emp: self.emp_entry.setText(emp)
                for j in JOURS:
                    rows = [r for r in d.get("jours",{}).get(j,[])
                            if any(r.get(k,"").strip() for k in ("debut","fin","tache","projet","desc"))]
                    self.day_cards[j].load_data(rows)
                    for r in rows: AutoCompleteRegistry.add(r.get("projet",""), r.get("tache",""), r.get("desc",""))
                loaded = True
            except: pass
        for j in JOURS:
            while len(self.day_cards[j].rows) < 5: self.day_cards[j].add_blank_row()
        self._recalc_week(); self._dirty = False
        self.status_bar.set(f"✓ {'Chargé' if loaded else 'Nouvelle semaine'}", GREEN)

    def _recalc_week(self):
        total = sum(self.day_cards[j].get_total() for j in JOURS)
        txt = fmt_h(total) if total else "0h"
        self.week_total_lbl.setText(f"Total : {txt}"); self.total_big.setText(txt)
        col = GREEN if total>=35 else ACC if total>=15 else AMBER if total>0 else ACC2
        self.total_big.setStyleSheet(f"color:{col}; font-family:'Segoe UI'; font-size:28px; font-weight:800; background:transparent;")
        self.prog.setValue(min(int(total/40*100),100))

    def _mark_dirty(self, _=None): self._dirty=True; self.status_bar.set("● Non sauvegardé", AMBER)
    def _autosave(self):
        if self._dirty: self._save(silent=True)

    def _save(self, silent=False):
        data = {"employer":self.emp_entry.text(),"semaine":week_key(self.monday),
                "jours":{},"credit":f"{DEV_CREDIT} — {COPYRIGHT}"}
        for j in JOURS: data["jours"][j] = self.day_cards[j].get_data()
        self.settings["employer"] = self.emp_entry.text()
        write_settings(self.settings)
        with open(save_file(self.monday),"w",encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._dirty = False
        self.status_bar.set(f"✓ Sauvegardé à {datetime.now().strftime('%H:%M')}", GREEN)
        if not silent:
            ss = _save_ss()
            self.save_btn.setText("✓  Sauvegardé !")
            self.save_btn.setStyleSheet(ss.replace(ACC3,GREEN2).replace(ACC,GREEN))
            QTimer.singleShot(1800, lambda: (self.save_btn.setText("💾  Sauvegarder"), self.save_btn.setStyleSheet(_save_ss())))

    # ── Actions ───────────────────────────────────────────────────────────────
    def _historique(self):
        dlg = HistoriqueDialog(self); dlg.week_selected.connect(self._load_from_hist); dlg.exec()
    def _load_from_hist(self, monday):
        self._save(silent=True); self.monday=monday; self._last_pdf=""
        for j in JOURS: self.day_cards[j].clear_all()
        self._load_week(monday)
    def _stats(self): self._save(silent=True); StatsDialog(self).exec()

    def _parametres(self):
        dlg = ParamDialog(self, self.settings)
        dlg.theme_changed.connect(self._apply_theme_live)
        dlg.saved.connect(self._apply_settings)
        old_theme = self.settings.get("theme","Dark Navy")
        result = dlg.exec()
        if result != QDialog.DialogCode.Accepted:
            # Annulé : restaurer l'ancien thème
            self._apply_theme_live(old_theme)

    def _apply_theme_live(self, theme_name):
        apply_theme(theme_name)
        self.setStyleSheet(ss_base())
        QApplication.instance().processEvents()

    def _apply_settings(self, s):
        self.settings = s
        self.emp_entry.setText(s.get("employer",""))
        apply_theme(s.get("theme","Dark Navy"))
        self.setStyleSheet(ss_base())
        write_settings(self.settings)

    def _open_folder(self): os.startfile(SAVE_PATH)

    def _export_zip(self):
        self._save(silent=True)
        dest, _ = QFileDialog.getSaveFileName(self,"Exporter — Groupe ADE",
            os.path.join(os.path.expanduser("~"),"Desktop",f"GroupeADE_FeuilleTemps_{datetime.now().strftime('%Y-%m-%d')}.zip"),"ZIP (*.zip)")
        if not dest: return
        try:
            count = 0
            with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as zf:
                for f in os.listdir(SAVE_PATH):
                    if f.endswith(".json"): zf.write(os.path.join(SAVE_PATH,f),arcname=f); count+=1
            QMessageBox.information(self,"Export réussi",f"✓ {count} fichier(s) exporté(s)\n\n{dest}")
        except Exception as ex: QMessageBox.critical(self,"Erreur",str(ex))

    def _import_zip(self):
        src, _ = QFileDialog.getOpenFileName(self,"Importer — Groupe ADE","","ZIP (*.zip)")
        if not src: return
        try:
            with zipfile.ZipFile(src,"r") as zf:
                jsons = [n for n in zf.namelist() if n.endswith(".json")]
                if not jsons: QMessageBox.warning(self,"Erreur","Aucune donnée."); return
                new = sum(1 for n in jsons if not os.path.exists(os.path.join(SAVE_PATH,n)))
                rep = QMessageBox.question(self,"Confirmer",f"{len(jsons)} semaine(s)\n• {new} nouvelle(s)\n• {len(jsons)-new} à écraser\n\nContinuer ?")
                if rep != QMessageBox.StandardButton.Yes: return
                zf.extractall(SAVE_PATH)
            for j in JOURS: self.day_cards[j].clear_all()
            self._load_week(self.monday)
            QMessageBox.information(self,"Import réussi",f"✓ {len(jsons)} semaine(s) importée(s)")
        except zipfile.BadZipFile: QMessageBox.critical(self,"Erreur","Fichier ZIP invalide.")
        except Exception as ex:    QMessageBox.critical(self,"Erreur",str(ex))

    # ── Envoi courriel ────────────────────────────────────────────────────────
    def _envoyer_courriel(self):
        self._save(silent=True)
        if not self.settings.get("email_dest","").strip():
            rep = QMessageBox.question(self, "Aucun destinataire configuré",
                "Aucune adresse courriel n'est encore configurée.\n\nVoulez-vous ouvrir les Paramètres pour en ajouter une ?")
            if rep == QMessageBox.StandardButton.Yes: self._parametres()
            return
        if not self._last_pdf or not os.path.exists(self._last_pdf):
            self.status_bar.set("Génération du PDF…", AMBER)
            QApplication.processEvents()
            self._last_pdf = self._generate_pdf_silent() or ""
        total = sum(self.day_cards[j].get_total() for j in JOURS)
        dlg = EnvoiDialog(self, employer=self.emp_entry.text() or "Employé",
                          week_lbl=week_label(self.monday),
                          total_h=fmt_h(total) if total else "0h",
                          pdf_path=self._last_pdf, settings=self.settings)
        dlg.exec()
        self.status_bar.set("✓ Prêt", GREEN)

    # ── Auto-update ───────────────────────────────────────────────────────────
    def _start_update_check(self):
        self._upd_signals = UpdateSignals()
        self._upd_signals.update_available.connect(self._on_update_found)
        UpdateChecker(self._upd_signals).start()

    def _on_update_found(self, remote_version, notes):
        self.update_ver_lbl.setText(f"Version {remote_version} disponible")
        self.update_notes_lbl.setText(notes[:120] if notes else "Nouvelle version disponible.")
        self.update_frame.show(); self.status_bar.set(f"🟢 Mise à jour {remote_version} disponible", GREEN)

    def _do_update(self):
        self.update_btn.setEnabled(False); self.update_btn.setText("Téléchargement…")
        self.update_prog.setValue(0); self.update_prog.show(); self._save(silent=True)
        def on_progress(dl, total):
            if total > 0: QTimer.singleShot(0, lambda: self.update_prog.setValue(int(dl/total*100)))
        def on_done():  QTimer.singleShot(0, self._update_ready)
        def on_error(msg): QTimer.singleShot(0, lambda: self._update_error(msg))
        UpdateDownloader(self._upd_signals, on_progress, on_done, on_error).start()

    def _update_ready(self):
        self.update_btn.setText("✓ Redémarrage…"); self.update_prog.setValue(100)
        QMessageBox.information(self,"Mise à jour","✓ Mise à jour téléchargée !\n\nL'application va se fermer et redémarrer automatiquement.")
        self._save(silent=True); QApplication.quit()

    def _update_error(self, msg):
        self.update_btn.setEnabled(True); self.update_btn.setText("⬇  Réessayer"); self.update_prog.hide()
        QMessageBox.warning(self,"Erreur de mise à jour",f"Impossible de télécharger :\n{msg}\n\nVérifie ta connexion réseau.")

    # ── PDF — INCHANGÉ (toujours Dark Navy ADE) ───────────────────────────────
    def _generate_pdf_silent(self):
        try:
            from reportlab.pdfgen import canvas as rl  # noqa
        except ImportError: return ""
        dest = os.path.join(SAVE_PATH, f"GroupeADE_FeuilleTemps_{week_key(self.monday)}.pdf")
        try: self._build_pdf(dest); return dest
        except: return ""

    def _pdf(self):
        try:
            from reportlab.pdfgen import canvas as rl  # noqa
        except ImportError:
            QMessageBox.critical(self,"Erreur","reportlab n'est pas installé.\npip install reportlab"); return
        self._save(silent=True)
        dest, _ = QFileDialog.getSaveFileName(self,"Exporter PDF — Groupe ADE",
            os.path.join(SAVE_PATH, f"GroupeADE_FeuilleTemps_{week_key(self.monday)}.pdf"),"PDF (*.pdf)")
        if not dest: return
        self._build_pdf(dest); self._last_pdf = dest
        rep = QMessageBox.question(self,"PDF créé",f"✓ PDF exporté !\n\n{dest}\n\nOuvrir le fichier ?")
        if rep == QMessageBox.StandardButton.Yes: os.startfile(dest)

    def _build_pdf(self, dest):
        # PDF toujours en Dark Navy ADE — indépendant du thème UI
        from reportlab.pdfgen import canvas as rl
        from reportlab.lib.pagesizes import letter
        c = rl.Canvas(dest, pagesize=letter); PW, PH = letter

        def bg(): c.setFillColorRGB(0.031,0.047,0.078); c.rect(0,0,PW,PH,fill=1,stroke=0)

        bg()
        c.setFillColorRGB(0.165,0.369,0.969); c.rect(0,PH-72,PW,72,fill=1,stroke=0)
        c.setFillColorRGB(0.102,0.247,0.698); c.rect(0,PH-72,6,72,fill=1,stroke=0)
        c.setFillColorRGB(0.941,0.957,1.0); c.setFont("Helvetica-Bold",22)
        c.drawString(24,PH-40,"Groupe ADE")
        c.setFillColorRGB(0.8,0.87,1.0); c.setFont("Helvetica",11)
        c.drawString(24,PH-58,f"Feuille de Temps  ·  {APP_VERSION}")
        c.setFillColorRGB(0.941,0.957,1.0)
        c.drawRightString(PW-24,PH-36,f"Semaine : {week_label(self.monday)}")
        c.drawRightString(PW-24,PH-54,f"Employé : {self.emp_entry.text()}")
        c.setFillColorRGB(0.051,0.078,0.129); c.rect(0,PH-92,PW,20,fill=1,stroke=0)
        c.setFillColorRGB(0.42,0.50,0.67); c.setFont("Helvetica",8)
        c.drawString(24,PH-85,f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        c.drawRightString(PW-24,PH-85,f"{DEV_CREDIT}  ·  {COPYRIGHT}")

        y = PH-108; week_tot = 0.0
        for jour in JOURS:
            card = self.day_cards[jour]
            rows = [r for r in card.rows if r.start.text() or r.end.text()]
            if y < 130: c.showPage(); bg(); y = PH-30
            c.setFillColorRGB(0.082,0.110,0.180); c.rect(20,y-20,PW-40,22,fill=1,stroke=0)
            c.setFillColorRGB(0.165,0.369,0.969); c.rect(20,y-20,5,22,fill=1,stroke=0)
            c.setFillColorRGB(0.941,0.957,1.0); c.setFont("Helvetica-Bold",10)
            c.drawString(32,y-12,jour.upper())
            day_tot = card.get_total(); week_tot += day_tot
            c.setFillColorRGB(0.165,0.369,0.969)
            c.drawRightString(PW-24,y-12,f"Total : {fmt_h(day_tot)}")
            y -= 26
            if not rows:
                c.setFillColorRGB(0.42,0.50,0.67); c.setFont("Helvetica-Oblique",9)
                c.drawString(36,y-8,"Aucune entrée"); y -= 18; continue
            c.setFillColorRGB(0.063,0.086,0.141); c.rect(20,y-15,PW-40,17,fill=1,stroke=0)
            c.setFillColorRGB(0.42,0.50,0.67); c.setFont("Helvetica-Bold",8)
            for txt, x in [("DATE",28),("DÉBUT",118),("FIN",166),("TÂCHE",214),("PROJET",310),("CLIENT / DESC",400),("DURÉE",PW-56)]:
                c.drawString(x,y-8,txt)
            y -= 17
            for i,r in enumerate(rows):
                if y < 40: c.showPage(); bg(); y = PH-30
                rb = 0.075 if i%2==0 else 0.094
                c.setFillColorRGB(rb,rb+0.016,rb+0.038); c.rect(20,y-13,PW-40,15,fill=1,stroke=0)
                c.setFillColorRGB(0.878,0.906,1.0); c.setFont("Helvetica",9)
                c.drawString(28,  y-7, r.date_lbl.text())
                c.drawString(118, y-7, r.start.text())
                c.drawString(166, y-7, r.end.text())
                c.drawString(214, y-7, r.tache.text()[:18])
                c.drawString(310, y-7, r.projet.text()[:16])
                c.drawString(400, y-7, r.desc.text()[:22])
                c.setFillColorRGB(0.165,0.369,0.969)
                c.drawRightString(PW-24,y-7,fmt_h(calc_h(r.start.text(),r.end.text())))
                y -= 15
            y -= 6
        y -= 4
        c.setFillColorRGB(0.165,0.369,0.969); c.rect(20,y-26,PW-40,30,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1); c.setFont("Helvetica-Bold",12)
        c.drawString(28,y-15,"TOTAL DE LA SEMAINE"); c.drawRightString(PW-24,y-15,fmt_h(week_tot))
        c.setFillColorRGB(0.031,0.047,0.078); c.rect(0,0,PW,26,fill=1,stroke=0)
        c.setFillColorRGB(0.263,0.322,0.451); c.setFont("Helvetica",7.5)
        c.drawString(24,8,f"Groupe ADE  ·  {APP_VERSION}  ·  {DEV_CREDIT}")
        c.drawRightString(PW-24,8,COPYRIGHT)
        c.save()

# ── Lancement ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Charger le thème sauvegardé avant de construire la palette
    _s = load_settings()
    apply_theme(_s.get("theme","Dark Navy"))

    pal = app.palette()
    pal.setColor(pal.ColorRole.Window,          QColor(BG))
    pal.setColor(pal.ColorRole.WindowText,      QColor(TXT))
    pal.setColor(pal.ColorRole.Base,            QColor(BG))
    pal.setColor(pal.ColorRole.AlternateBase,   QColor(BG2))
    pal.setColor(pal.ColorRole.Text,            QColor(TXT))
    pal.setColor(pal.ColorRole.Button,          QColor(CARD))
    pal.setColor(pal.ColorRole.ButtonText,      QColor(TXT))
    pal.setColor(pal.ColorRole.Highlight,       QColor(ACC))
    pal.setColor(pal.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())