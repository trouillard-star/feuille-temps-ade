"""
╔══════════════════════════════════════════════════════════════╗
║         Feuille de Temps — Le Groupe ADE  v3.9              ║
║         © 2026 Thierry Rouillard — Tous droits réservés      ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys, os, json, zipfile, threading, tempfile, subprocess, urllib.parse
from datetime import datetime, timedelta
from urllib.request import urlopen, urlretrieve
from functools import lru_cache

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar,
    QFileDialog, QMessageBox, QDialog, QSizePolicy, QGraphicsDropShadowEffect,
    QTextEdit, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QColor

# ── Chemins ───────────────────────────────────────────────────────────────────
SAVE_PATH     = os.path.join(os.path.expanduser("~"), "Documents", "FeuilleTemps")
SETTINGS_FILE = os.path.join(SAVE_PATH, "settings.json")
ACHIEVEMENTS_FILE = os.path.join(SAVE_PATH, "achievements.json")
os.makedirs(SAVE_PATH, exist_ok=True)

APP_NAME    = "Groupe ADE"
APP_SUB     = "Feuille de Temps"
APP_VERSION = "v3.9"
COPYRIGHT   = "© 2026 Thierry Rouillard"
DEV_CREDIT  = "Développé par Thierry Rouillard"

# ── Auto-update ───────────────────────────────────────────────────────────────
GITHUB_USER        = "trouillard-star"
GITHUB_REPO        = "feuille-temps-ade"
GITHUB_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest/download/FeuilleTemps_ADE.exe"
EXE_NAME           = "FeuilleTemps_ADE.exe"

def _version_tuple(v):
    parts = []
    for p in v.strip().lstrip("vV").split("."):
        try: parts.append(int(p))
        except: parts.append(0)
    while len(parts) < 3: parts.append(0)
    return tuple(parts)

def _newer(remote, local): return _version_tuple(remote) > _version_tuple(local)

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
        except: self.signals.check_failed.emit()

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
        except Exception as ex: self.error_cb(str(ex))

# ╔══════════════════════════════════════════════════════════════╗
# ║                    SYSTÈME DE THÈMES                         ║
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
        "LIGHT": False,
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
        "LIGHT": False,
    },
    "Slate": {
        "BG":"#0F172A","BG2":"#1E293B","BG3":"#1E293B",
        "CARD":"#1E293B","CARD2":"#334155",
        "ACC":"#38BDF8","ACC2":"#7DD3FC","ACC3":"#0284C7","ACCD":"#0C4A6E",
        "GREEN":"#34D399","GREEN2":"#059669",
        "RED":"#FB7185","AMBER":"#FBBF24",
        "TXT":"#F1F5F9","TXT2":"#94A3B8","TXT3":"#475569",
        "MUTED":"#334155","BORDER":"#334155","BORDER2":"#475569","ROW":"#0F172A",
        "PALETTE":["#38BDF8","#34D399","#FBBF24","#A78BFA","#F472B6",
                   "#818CF8","#FB923C","#A3E635","#FB7185","#2DD4BF"],
        "LIGHT": False,
    },
    "Forest": {
        "BG":"#071209","BG2":"#0C1A0D","BG3":"#112214",
        "CARD":"#122114","CARD2":"#1A2E1C",
        "ACC":"#4ADE80","ACC2":"#86EFAC","ACC3":"#16A34A","ACCD":"#14532D",
        "GREEN":"#4ADE80","GREEN2":"#15803D",
        "RED":"#F87171","AMBER":"#FDE047",
        "TXT":"#ECFDF5","TXT2":"#6EE7B7","TXT3":"#2D6A45",
        "MUTED":"#1A3320","BORDER":"#1A3320","BORDER2":"#14532D","ROW":"#08120A",
        "PALETTE":["#4ADE80","#FDE047","#34D399","#A3E635","#86EFAC",
                   "#22D3EE","#FB923C","#6EE7B7","#F87171","#2DD4BF"],
        "LIGHT": False,
    },
    "Crimson": {
        "BG":"#0E0808","BG2":"#160C0C","BG3":"#1C1010",
        "CARD":"#1A0E0E","CARD2":"#241414",
        "ACC":"#F87171","ACC2":"#FCA5A5","ACC3":"#DC2626","ACCD":"#7F1D1D",
        "GREEN":"#4ADE80","GREEN2":"#15803D",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#FFF1F1","TXT2":"#FDA4AF","TXT3":"#7F3040",
        "MUTED":"#3B1C1C","BORDER":"#2E1515","BORDER2":"#7F1D1D","ROW":"#0E0808",
        "PALETTE":["#F87171","#FCA5A5","#FCD34D","#C084FC","#F472B6",
                   "#FB923C","#A3E635","#38BDF8","#4ADE80","#2DD4BF"],
        "LIGHT": False,
    },
    "Arctic Light": {
        "BG":"#F0F4FA","BG2":"#E4EAF5","BG3":"#EBF0FA",
        "CARD":"#FFFFFF","CARD2":"#F5F8FF",
        "ACC":"#2563EB","ACC2":"#1D4ED8","ACC3":"#3B82F6","ACCD":"#DBEAFE",
        "GREEN":"#059669","GREEN2":"#047857",
        "RED":"#DC2626","AMBER":"#D97706",
        "TXT":"#111827","TXT2":"#374151","TXT3":"#9CA3AF",
        "MUTED":"#D1D5DB","BORDER":"#DDE3EF","BORDER2":"#C7D2E8","ROW":"#F9FAFB",
        "PALETTE":["#2563EB","#059669","#D97706","#7C3AED","#DB2777",
                   "#0891B2","#EA580C","#65A30D","#DC2626","#0D9488"],
        "LIGHT": True,
    },
    "Warm Paper": {
        "BG":"#FAF7F2","BG2":"#F0EBE0","BG3":"#F5F0E8",
        "CARD":"#FFFFFF","CARD2":"#FAF5EC",
        "ACC":"#92400E","ACC2":"#78350F","ACC3":"#B45309","ACCD":"#FEF3C7",
        "GREEN":"#065F46","GREEN2":"#047857",
        "RED":"#991B1B","AMBER":"#92400E",
        "TXT":"#1C1917","TXT2":"#44403C","TXT3":"#A8A29E",
        "MUTED":"#D6D3D1","BORDER":"#E7E5E0","BORDER2":"#D6D3D1","ROW":"#FDFCF9",
        "PALETTE":["#92400E","#065F46","#B45309","#5B21B6","#BE185D",
                   "#0369A1","#C2410C","#4D7C0F","#991B1B","#0F766E"],
        "LIGHT": True,
    },
}

BG=BG2=BG3=CARD=CARD2=ACC=ACC2=ACC3=ACCD=GREEN=GREEN2=RED=AMBER=""
TXT=TXT2=TXT3=MUTED=BORDER=BORDER2=ROW=""
PALETTE: list = []
IS_LIGHT: bool = False

def apply_theme(name: str):
    global BG,BG2,BG3,CARD,CARD2,ACC,ACC2,ACC3,ACCD,GREEN,GREEN2,RED,AMBER
    global TXT,TXT2,TXT3,MUTED,BORDER,BORDER2,ROW,PALETTE,IS_LIGHT
    t = THEMES.get(name, THEMES["Dark Navy"])
    (BG,BG2,BG3,CARD,CARD2,ACC,ACC2,ACC3,ACCD,GREEN,GREEN2,RED,AMBER,
     TXT,TXT2,TXT3,MUTED,BORDER,BORDER2,ROW) = (
        t["BG"],t["BG2"],t["BG3"],t["CARD"],t["CARD2"],t["ACC"],t["ACC2"],t["ACC3"],t["ACCD"],
        t["GREEN"],t["GREEN2"],t["RED"],t["AMBER"],
        t["TXT"],t["TXT2"],t["TXT3"],t["MUTED"],t["BORDER"],t["BORDER2"],t["ROW"])
    PALETTE[:] = t["PALETTE"]; IS_LIGHT = t.get("LIGHT", False)

apply_theme("Dark Navy")

# ── Constantes UI ─────────────────────────────────────────────────────────────
JOURS      = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
MOIS_FR    = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
              7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}
JOURS_ABRV = {"Lundi":"Lun","Mardi":"Mar","Mercredi":"Mer","Jeudi":"Jeu","Vendredi":"Ven"}

def ss_base():
    sb = BORDER2 if not IS_LIGHT else "#B0BDD0"
    return f"""
    QWidget {{ background:{BG}; color:{TXT}; font-family:'Segoe UI'; font-size:13px; }}
    QScrollBar:vertical {{ background:{BG2}; width:5px; border-radius:3px; }}
    QScrollBar::handle:vertical {{ background:{sb}; border-radius:3px; min-height:24px; }}
    QScrollBar::handle:vertical:hover {{ background:{ACC3}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar:horizontal {{ height:0; }}
    QToolTip {{ background:{CARD2}; color:{TXT}; border:1px solid {ACC3}; padding:5px 8px; border-radius:6px; font-size:12px; }}
    QComboBox {{ background:{CARD}; color:{TXT}; border:1px solid {BORDER}; border-radius:7px; padding:0 10px; font-size:12px; min-height:32px; }}
    QComboBox:hover {{ border-color:{BORDER2}; }}
    QComboBox:focus {{ border-color:{ACC}; }}
    QComboBox::drop-down {{ border:none; width:20px; }}
    QComboBox QAbstractItemView {{ background:{CARD2}; color:{TXT}; border:1px solid {BORDER2};
        selection-background-color:{ACC3}; selection-color:{'white' if not IS_LIGHT else TXT}; }}
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
        if f.endswith(".json") and f not in ("settings.json", "achievements.json"):
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
    if IS_LIGHT: return
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(radius); fx.setColor(QColor(color)); fx.setOffset(0,0)
    widget.setGraphicsEffect(fx)

def _load_week_data(monday) -> dict:
    """Charge une semaine et retourne {total, jours:{jour:float}}. Lève exception si introuvable."""
    with open(save_file(monday), "r", encoding="utf-8") as f: d = json.load(f)
    total = 0.0; jour_h = {}
    for j in JOURS:
        jt = sum(calc_h(r.get("debut",""), r.get("fin","")) for r in d.get("jours",{}).get(j,[]))
        jour_h[j] = jt; total += jt
    return {"monday": monday, "label": week_label(monday), "total": total, "jours": jour_h, "_raw": d}

def load_all_weeks() -> list:
    """Charge toutes les semaines enregistrées, silence les erreurs."""
    weeks = []
    for monday in sorted(saved_weeks()):
        try: weeks.append(_load_week_data(monday))
        except: pass
    return weeks

# ── Widget helpers ────────────────────────────────────────────────────────────
def lbl(text, size=12, bold=False, color=None):
    c = color or TXT
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
    hover_bg = CARD2 if not IS_LIGHT else BG2
    b.setStyleSheet(f"""
        QPushButton {{ background:{CARD}; color:{TXT2}; border:1px solid {BORDER}; border-radius:8px;
                      padding:0 10px; font-size:11px; font-weight:500; }}
        QPushButton:hover {{ background:{hover_bg}; color:{TXT}; border-color:{ACC3}; }}
        QPushButton:pressed {{ background:{ACCD}; }}
    """)
    return b

def card_frame(radius=12):
    f = QFrame()
    f.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:{radius}px;")
    return f

def action_btn(text, primary=False):
    b = QPushButton(text); b.setFixedHeight(38); b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        b.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                          color:white; border:none; border-radius:9px; font-size:13px; font-weight:700; }}
            QPushButton:hover {{ background:{ACC}; }}
            QPushButton:pressed {{ background:{ACCD}; }}
        """)
    else:
        b.setStyleSheet(f"""
            QPushButton {{ background:{CARD2}; color:{TXT2}; border:1px solid {BORDER}; border-radius:9px; font-size:12px; }}
            QPushButton:hover {{ background:{CARD}; color:{TXT}; }}
            QPushButton:pressed {{ background:{ACCD}; }}
        """)
    return b

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
        if not IS_LIGHT: glow(badge, ACC, 16)
        lay.addWidget(badge)
        tc = QVBoxLayout(); tc.setSpacing(0)
        name = QLabel("Groupe ADE")
        name.setStyleSheet(f"color:{TXT}; font-family:'Segoe UI'; font-size:14px; font-weight:700; background:transparent;")
        sub = QLabel("Feuille de Temps")
        sub.setStyleSheet(f"color:{TXT2}; font-family:'Segoe UI'; font-size:10px; background:transparent;")
        tc.addWidget(name); tc.addWidget(sub); lay.addLayout(tc); lay.addStretch()
        ver = QLabel(APP_VERSION)
        ver.setStyleSheet(f"background:{ACCD}; color:{ACC2 if not IS_LIGHT else ACC}; border-radius:5px; padding:2px 7px; font-size:9px; font-weight:600;")
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
            c = ACC if IS_LIGHT else ACC2
            self.dur_lbl.setStyleSheet(f"color:{c}; background:transparent; font-weight:700; font-size:12px;")
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
        hdr.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {BG2},stop:1 {CARD}); border-radius:13px 13px 0 0; border-bottom:1px solid {BORDER};")
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
        self.tot_lbl = QLabel("–"); self.tot_lbl.setStyleSheet(f"color:{ACC2 if not IS_LIGHT else ACC}; font-size:12px; font-weight:700; background:transparent;")
        tbl.addWidget(self.tot_lbl); hl.addWidget(self.tot_badge); hl.addSpacing(6)
        add_btn = QPushButton("＋ Ligne"); add_btn.setFixedHeight(28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{ background:{ACC3}; color:white; border:none; border-radius:7px; padding:0 12px; font-size:11px; font-weight:600; }}
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
        if total >= 7:   color, bg, brd = GREEN, ("#0A2218" if not IS_LIGHT else "#D1FAE5"), GREEN2
        elif total > 0:  color, bg, brd = AMBER, ("#211A08" if not IS_LIGHT else "#FEF3C7"), ("#92700A" if not IS_LIGHT else "#D97706")
        else:            color, bg, brd = TXT2, ACCD, ACC3
        self.tot_lbl.setText(fmt_h(total) if total else "–")
        self.tot_lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:700; background:transparent;")
        self.tot_badge.setStyleSheet(f"background:{bg}; border-radius:8px; border:1px solid {brd};")
        self.data_changed.emit()

    def get_data(self):  return [r.get_data() for r in self.rows if r.has_data()]

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
            bar_c = GREEN if tot>=35 else (AMBER if tot>0 else MUTED)
            bg_c  = ("#091A10" if not IS_LIGHT else "#D1FAE5") if tot>=35 else \
                    ("#1A1408" if not IS_LIGHT else "#FEF3C7") if tot>0 else CARD
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
                QPushButton {{ background:{ACCD}; color:{ACC2 if not IS_LIGHT else ACC}; border:1px solid {ACC3}; border-radius:6px; font-size:11px; font-weight:600; }}
                QPushButton:hover {{ background:{ACC3}; color:white; }}
            """)
            btn.clicked.connect(lambda _,m=monday: self._pick(m)); cl.addWidget(btn)
            self.list_layout.insertWidget(self.list_layout.count()-1, card)

    def _pick(self, monday): self.week_selected.emit(monday); self.accept()

# ── ParamDialog ────────────────────────────────────────────────────────────────
class ParamDialog(QDialog):
    saved         = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.s = dict(settings)
        self.setWindowTitle("Paramètres — Groupe ADE")
        self.setFixedSize(540, 620)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        hdr = QFrame(); hdr.setFixedHeight(64)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0); hl.setSpacing(12)
        hl.addWidget(QLabel("⚙️"))
        tc = QVBoxLayout(); tc.setSpacing(2)
        tc.addWidget(lbl("Paramètres",14,bold=True))
        tc.addWidget(lbl(f"Groupe ADE  ·  {APP_VERSION}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch(); root.addWidget(hdr)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,16,20,16); bl.setSpacing(14)
        scroll.setWidget(body); root.addWidget(scroll, 1)
        bl.addWidget(self._section_header("👤", "Identité de l'employé"))
        frm1 = card_frame()
        f1l = QVBoxLayout(frm1); f1l.setContentsMargins(16,14,16,16); f1l.setSpacing(6)
        f1l.addWidget(lbl("Nom complet",9,color=TXT3))
        self.emp = styled_entry("Votre nom complet", height=36)
        self.emp.setText(self.s.get("employer",""))
        f1l.addWidget(self.emp)
        f1l.addWidget(lbl("Ce nom apparaîtra sur les feuilles exportées en PDF.",9,color=TXT3))
        bl.addWidget(frm1)
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
        bl.addWidget(self._section_header("🎨", "Thème d'affichage"))
        frm3 = card_frame()
        f3l = QVBoxLayout(frm3); f3l.setContentsMargins(16,14,16,16); f3l.setSpacing(10)
        f3l.addWidget(lbl("Choisir un thème  (appliqué immédiatement, sans redémarrage)",9,color=TXT3))
        self.theme_combo = QComboBox()
        for name in THEMES: self.theme_combo.addItem(name)
        cur = self.s.get("theme","Dark Navy")
        idx = self.theme_combo.findText(cur)
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentTextChanged.connect(self._preview_theme)
        f3l.addWidget(self.theme_combo)
        self.swatch_row = QHBoxLayout(); self.swatch_row.setSpacing(6)
        self._build_swatches(); f3l.addLayout(self.swatch_row)
        note = lbl("⚠️ Le thème n'affecte pas le rendu PDF — celui-ci est toujours en mode Dark Navy ADE.",9,color=AMBER)
        note.setWordWrap(True); f3l.addWidget(note)
        bl.addWidget(frm3); bl.addStretch()
        foot_widget = QWidget(); foot_widget.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fw = QHBoxLayout(foot_widget); fw.setContentsMargins(20,10,20,10); fw.setSpacing(10)
        fw.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); fw.addStretch()
        cancel_btn = action_btn("Annuler"); cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        save_btn = action_btn("💾  Enregistrer", primary=True); save_btn.setFixedWidth(140)
        save_btn.clicked.connect(self._save)
        fw.addWidget(cancel_btn); fw.addWidget(save_btn); root.addWidget(foot_widget)

    def _section_header(self, icon, title):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w); hl.setContentsMargins(0,4,0,0); hl.setSpacing(6)
        hl.addWidget(QLabel(icon)); hl.addWidget(lbl(title, 11, bold=True))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; background:{BORDER};"); sep.setFixedHeight(1)
        hl.addWidget(sep, 1); return w

    def _build_swatches(self):
        while self.swatch_row.count():
            item = self.swatch_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        cur = self.theme_combo.currentText()
        for name, tdata in THEMES.items():
            btn = QPushButton(); btn.setFixedSize(40, 30)
            btn.setToolTip(name); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            acc = tdata["ACC"]; bg = tdata["BG2"]; card = tdata["CARD"]
            is_light_t = tdata.get("LIGHT", False)
            border = "2px solid #333" if name==cur and is_light_t else \
                     "2px solid white" if name==cur else f"1px solid {tdata['BORDER2']}"
            btn.setStyleSheet(f"""
                QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {bg},stop:0.5 {card},stop:1 {acc});
                               border:{border}; border-radius:7px; }}
                QPushButton:hover {{ border:2px solid {acc}; }}
            """)
            btn.clicked.connect(lambda _, n=name: self._select_theme(n))
            self.swatch_row.addWidget(btn)
        self.swatch_row.addStretch()

    def _select_theme(self, name):
        idx = self.theme_combo.findText(name)
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)

    def _preview_theme(self, name):
        apply_theme(name); self.s["theme"] = name
        self.theme_changed.emit(name); self._build_swatches()

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
        hl.addWidget(QLabel("✉️")); hl.addSpacing(8)
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
        cancel_btn = action_btn("Annuler"); cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)
        self.send_btn = action_btn("✉️  Ouvrir dans mon client mail", primary=True)
        self.send_btn.setFixedHeight(40)
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
# ║                    STATISTIQUES v2                          ║
# ╚══════════════════════════════════════════════════════════════╝
class StatsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Statistiques — Groupe ADE"); self.resize(1060, 900)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        self._load(); self._build()

    def _load(self):
        self.weeks = []
        self.proj_totals:  dict[str, float] = {}
        self.tache_totals: dict[str, float] = {}
        self.proj_days:    dict[str, int]   = {}
        self.all_day_hours: list[float]     = []
        self.matin_h = 0.0; self.aprem_h = 0.0; self.overtime_h = 0.0
        self.jour_counts: dict[str, list[float]] = {j:[] for j in JOURS}
        self.monthly: dict[str, float] = {}

        for monday in sorted(saved_weeks()):
            try:
                with open(save_file(monday),"r",encoding="utf-8") as f: d = json.load(f)
                total = 0.0; jour_h: dict[str,float] = {}
                month_key = monday.strftime("%Y-%m")
                for j in JOURS:
                    jt = 0.0
                    proj_seen: set[str] = set()
                    for r in d.get("jours",{}).get(j,[]):
                        h = calc_h(r.get("debut",""), r.get("fin",""))
                        jt += h
                        p = r.get("projet","").strip()
                        if p and h > 0:
                            self.proj_totals[p] = self.proj_totals.get(p,0.0) + h
                            if p not in proj_seen:
                                self.proj_days[p] = self.proj_days.get(p,0) + 1
                                proj_seen.add(p)
                        t = r.get("tache","").strip()
                        if t and h > 0: self.tache_totals[t] = self.tache_totals.get(t,0.0) + h
                        s = parse_heure(r.get("debut","")); e = parse_heure(r.get("fin",""))
                        if s and e and e > s:
                            noon = s.replace(hour=12,minute=0,second=0)
                            if e <= noon: self.matin_h += h
                            elif s >= noon: self.aprem_h += h
                            else:
                                self.matin_h += (noon-s).seconds/3600
                                self.aprem_h += (e-noon).seconds/3600
                    jour_h[j] = jt
                    if jt > 0:
                        self.all_day_hours.append(jt)
                        self.jour_counts[j].append(jt)
                        if jt > 8: self.overtime_h += (jt - 8)
                    total += jt
                self.monthly[month_key] = self.monthly.get(month_key,0.0) + total
                self.weeks.append({"monday":monday,"label":week_label(monday),"total":total,"jours":jour_h})
            except: pass

        self.streak = 0
        check = get_monday(datetime.today())
        week_map = {w["monday"].date(): w for w in self.weeks}
        while True:
            wk = week_map.get(check.date())
            if wk and wk["total"] >= 35: self.streak += 1; check -= timedelta(weeks=1)
            else: break
        self.best_day_h = max(self.all_day_hours) if self.all_day_hours else 0.0

        totals = [w["total"] for w in self.weeks]; n = len(totals)
        if n >= 4:
            last4 = [t for t in totals[-4:] if t > 0]
            prev4 = [t for t in totals[-8:-4] if t > 0] if n >= 8 else [t for t in totals[:-4] if t > 0]
            self.trend_last = sum(last4)/len(last4) if last4 else 0
            self.trend_prev = sum(prev4)/len(prev4) if prev4 else 0
        else:
            self.trend_last = sum(totals)/n if n else 0; self.trend_prev = 0

        self.projection = 0.0
        today = datetime.today(); current_monday = get_monday(today); day_idx = today.weekday()
        if self.weeks and self.weeks[-1]["monday"].date() == current_monday.date():
            cw = self.weeks[-1]
            hours_so_far = sum(cw["jours"].get(JOURS[i],0) for i in range(min(day_idx+1,5)))
            avg_daily = sum(self.all_day_hours)/len(self.all_day_hours) if self.all_day_hours else 8.0
            self.projection = hours_so_far + avg_daily * max(0, 4 - day_idx)

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        hdr = QFrame(); hdr.setFixedHeight(60)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(22,0,22,0)
        hl.addWidget(QLabel("📊")); hl.addSpacing(8)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(lbl("Statistiques",14,bold=True))
        tc.addWidget(lbl(f"Rapport de {len(self.weeks)} semaine(s)  ·  {COPYRIGHT}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch()
        self.tab_btns = []
        for i, tab_name in enumerate(["Vue d'ensemble","Projets & Tâches","Calendrier","Tendances"]):
            btn = QPushButton(tab_name); btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            self.tab_btns.append(btn); hl.addWidget(btn)
        lay.addWidget(hdr)
        self.pages_widget = QWidget(); self.pages_widget.setStyleSheet(f"background:{BG};")
        self.pages_layout = QVBoxLayout(self.pages_widget); self.pages_layout.setContentsMargins(0,0,0,0)
        self.pages: list[QScrollArea] = []
        for i in range(4):
            sa = QScrollArea(); sa.setWidgetResizable(True)
            sa.setStyleSheet(f"QScrollArea {{ border:none; }} QWidget {{ background:{BG}; }}")
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            content = QWidget(); cl = QVBoxLayout(content)
            cl.setContentsMargins(16,16,16,16); cl.setSpacing(14)
            self._build_tab(i, cl)
            cl.addStretch(); sa.setWidget(content)
            self.pages_layout.addWidget(sa); self.pages.append(sa)
        lay.addWidget(self.pages_widget, 1)
        self._footer(lay); self._switch_tab(0)

    def _switch_tab(self, idx):
        for i, (btn, page) in enumerate(zip(self.tab_btns, self.pages)):
            active = (i == idx); page.setVisible(active); btn.setChecked(active)
            btn.setStyleSheet(f"""
                QPushButton {{ background:{ACC3 if active else CARD}; color:{'white' if active else TXT2};
                    border:1px solid {ACC if active else BORDER}; border-radius:8px; padding:0 12px;
                    font-size:11px; font-weight:{'700' if active else '500'}; }}
                QPushButton:hover {{ background:{ACC if active else CARD2}; color:{'white' if active else TXT}; }}
            """)

    def _build_tab(self, idx, cl):
        if idx == 0:   self._tab_overview(cl)
        elif idx == 1: self._tab_projects(cl)
        elif idx == 2: self._tab_calendar(cl)
        elif idx == 3: self._tab_trends(cl)

    def _tab_overview(self, cl):
        if not self.weeks:
            cl.addWidget(lbl("Aucune donnée disponible.",14,color=MUTED)); return
        totals   = [w["total"] for w in self.weeks]
        non_zero = [t for t in totals if t>0]
        best_wk  = max(self.weeks, key=lambda w: w["total"]) if self.weeks else None
        cl.addWidget(self._sec_title("KPI Principaux"))
        cr = QHBoxLayout(); cr.setSpacing(10)
        for title, val, color, sub, icon in [
            ("Total cumulé",   fmt_h(sum(totals)),   ACC,   f"{len(non_zero)} sem. actives","⏱"),
            ("Moyenne / sem.", fmt_h(sum(non_zero)/len(non_zero)) if non_zero else "–", GREEN, f"sur {len(non_zero)} sem.","📈"),
            ("Meilleure sem.", fmt_h(max(totals)) if totals else "–", AMBER, best_wk["label"] if best_wk and best_wk["total"]>0 else "–","🏆"),
            ("Sem. actives",   str(len(non_zero)), ACC2 if not IS_LIGHT else ACC, f"sur {len(self.weeks)} total","📅"),
        ]:
            cr.addWidget(self._kpi_card(title, val, color, sub, icon))
        cl.addLayout(cr)
        cr2 = QHBoxLayout(); cr2.setSpacing(10)
        streak_col = GREEN if self.streak >= 4 else AMBER if self.streak >= 1 else MUTED
        cr2.addWidget(self._kpi_card("Série en cours", f"{self.streak} sem." if self.streak else "–",
            streak_col, "sem. complètes (≥35h) consécutives","🔥"))
        cr2.addWidget(self._kpi_card("Record journalier", fmt_h(self.best_day_h) if self.best_day_h else "–",
            ACC2 if not IS_LIGHT else ACC, "meilleure journée toutes semaines","⚡"))
        ot_col = AMBER if self.overtime_h > 0 else MUTED
        cr2.addWidget(self._kpi_card("Heures supp.", fmt_h(self.overtime_h) if self.overtime_h else "–",
            ot_col, "total heures > 8h/jour","🕐"))
        total_dist = self.matin_h + self.aprem_h
        if total_dist > 0:
            mat_pct = int(self.matin_h / total_dist * 100)
            cr2.addWidget(self._kpi_card("Distribution", f"{mat_pct}% matin",
                "#A78BFA", f"{100-mat_pct}% après-midi","🌅"))
        else:
            cr2.addWidget(self._kpi_card("Distribution", "–", MUTED, "données insuffisantes","🌅"))
        cl.addLayout(cr2)

        cl.addWidget(self._sec_title("Moyenne par jour de la semaine"))
        dc = card_frame(); dl = QVBoxLayout(dc); dl.setContentsMargins(16,14,16,14); dl.setSpacing(10)
        avgs = {j:(sum(self.jour_counts[j])/len(self.jour_counts[j]) if self.jour_counts[j] else 0) for j in JOURS}
        max_avg = max(avgs.values()) or 1
        best_jour = max(avgs, key=avgs.get) if any(avgs.values()) else ""
        for j in JOURS:
            avg = avgs[j]; is_best = (j == best_jour and avg > 0)
            r = QHBoxLayout(); r.setSpacing(10)
            jl = lbl(j,11,color=TXT2); jl.setFixedWidth(80); r.addWidget(jl)
            prog_color = GREEN if is_best else f"qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC})"
            prog = QProgressBar(); prog.setValue(int(avg/max_avg*100) if avg else 0)
            prog.setFixedHeight(10); prog.setTextVisible(False)
            prog.setStyleSheet(f"QProgressBar {{ background:{BG2}; border-radius:5px; border:none; }} QProgressBar::chunk {{ background:{prog_color}; border-radius:5px; }}")
            r.addWidget(prog,1)
            cnt_lbl = lbl(f"({len(self.jour_counts[j])} j.)",9,color=TXT3); cnt_lbl.setFixedWidth(40); r.addWidget(cnt_lbl)
            val_lbl = lbl(fmt_h(avg) if avg else "–", 11, bold=True, color=GREEN if is_best else (ACC if IS_LIGHT else ACC2) if avg else MUTED)
            r.addWidget(val_lbl)
            if is_best: r.addWidget(lbl("★",10,color=GREEN))
            dl.addLayout(r)
        cl.addWidget(dc)

        cl.addWidget(self._sec_title("Distribution des semaines"))
        distr = card_frame(); drl = QHBoxLayout(distr); drl.setContentsMargins(16,14,16,14); drl.setSpacing(16)
        buckets = {"< 20h":0,"20–35h":0,"35–40h":0,"≥ 40h":0}
        for t in totals:
            if t < 20: buckets["< 20h"] += 1
            elif t < 35: buckets["20–35h"] += 1
            elif t < 40: buckets["35–40h"] += 1
            else: buckets["≥ 40h"] += 1
        for (label, cnt), color in zip(buckets.items(), [RED, AMBER, ACC, GREEN]):
            bw = QWidget(); bw.setStyleSheet("background:transparent;")
            bwl = QVBoxLayout(bw); bwl.setContentsMargins(0,0,0,0); bwl.setSpacing(4); bwl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            val_l = lbl(str(cnt),20,bold=True,color=color); val_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            name_l = lbl(label,10,color=TXT2); name_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            pct_l  = lbl(f"{cnt/len(totals)*100:.0f}%" if totals else "–",9,color=TXT3); pct_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            bwl.addWidget(val_l); bwl.addWidget(name_l); bwl.addWidget(pct_l)
            drl.addWidget(bw,1)
        cl.addWidget(distr)

        cl.addWidget(self._sec_title("Détail par semaine (10 dernières)"))
        tc3 = card_frame(); tl3 = QVBoxLayout(tc3); tl3.setContentsMargins(16,14,16,14); tl3.setSpacing(0)
        hd = QFrame(); hd.setStyleSheet(f"background:{CARD2}; border-radius:7px;")
        hdl = QHBoxLayout(hd); hdl.setContentsMargins(12,6,10,6); hdl.setSpacing(4)
        for txt, w in [("Semaine",0),("Lun",60),("Mar",60),("Mer",60),("Jeu",60),("Ven",60),("Total",80),("Statut",70)]:
            lh = QLabel(txt); lh.setStyleSheet(f"color:{TXT3}; font-size:9px; font-weight:700; letter-spacing:1px; background:transparent;")
            if w: lh.setFixedWidth(w)
            else: lh.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hdl.addWidget(lh)
        tl3.addWidget(hd)
        for i, wk in enumerate(list(reversed(self.weeks))[:10]):
            row = QFrame(); row.setStyleSheet(f"background:{ROW if i%2==0 else CARD}; border-radius:0;"); row.setFixedHeight(34)
            rl2 = QHBoxLayout(row); rl2.setContentsMargins(12,0,10,0); rl2.setSpacing(4)
            rl2.addWidget(lbl(wk["label"],10))
            for j in JOURS:
                v=wk["jours"].get(j,0); col = GREEN if v>=7 else TXT2 if v>0 else MUTED
                l2 = lbl(fmt_h(v) if v else "–",10,color=col); l2.setFixedWidth(60); rl2.addWidget(l2)
            tc_col = GREEN if wk["total"]>=35 else AMBER if wk["total"]>0 else MUTED
            tl_r = lbl(fmt_h(wk["total"]) if wk["total"] else "–",10,bold=True,color=tc_col); tl_r.setFixedWidth(80); rl2.addWidget(tl_r)
            if wk["total"] >= 40:   status, sc = "⚡ Sup.", AMBER
            elif wk["total"] >= 35: status, sc = "✓ Complet", GREEN
            elif wk["total"] > 0:   status, sc = "⚠ Partiel", AMBER
            else:                    status, sc = "○ Vide", MUTED
            sl = lbl(status, 9, color=sc); sl.setFixedWidth(70); rl2.addWidget(sl)
            tl3.addWidget(row)
        cl.addWidget(tc3)

    def _tab_projects(self, cl):
        if not self.proj_totals and not self.tache_totals:
            cl.addWidget(lbl("Aucune donnée de projet disponible.",14,color=MUTED)); return
        if self.proj_totals:
            cl.addWidget(self._sec_title(f"Répartition par projet — {len(self.proj_totals)} projet(s)"))
            pc = card_frame(); pl = QVBoxLayout(pc); pl.setContentsMargins(16,14,16,14); pl.setSpacing(8)
            all_h = sum(self.proj_totals.values()); max_h = max(self.proj_totals.values())
            sorted_proj = sorted(self.proj_totals.items(), key=lambda x:x[1], reverse=True)
            for idx, (proj, h) in enumerate(sorted_proj):
                pl.addWidget(self._bar_row_rich(proj, h, all_h, max_h, PALETTE[idx%len(PALETTE)], self.proj_days.get(proj,0)))
            cl.addWidget(pc)
            cl.addWidget(self._sec_title("Top 3 Projets"))
            top_row = QHBoxLayout(); top_row.setSpacing(10)
            for i, (proj, h) in enumerate(sorted_proj[:3]):
                color = PALETTE[i%len(PALETTE)]
                c = QFrame(); c.setStyleSheet(f"background:{CARD}; border:2px solid {color}; border-radius:12px;")
                cv = QVBoxLayout(c); cv.setContentsMargins(14,12,14,12); cv.setSpacing(4)
                th = QHBoxLayout()
                th.addWidget(QLabel(["🥇","🥈","🥉"][i])); th.addStretch()
                th.addWidget(lbl(f"{h/all_h*100:.1f}%",11,bold=True,color=color))
                cv.addLayout(th); cv.addWidget(lbl(proj,11,bold=True))
                cv.addWidget(lbl(fmt_h(h),18,bold=True,color=color)); top_row.addWidget(c,1)
            for _ in range(max(0, 3-len(sorted_proj))): top_row.addWidget(QWidget(),1)
            cl.addLayout(top_row)
        if self.tache_totals:
            cl.addWidget(self._sec_title(f"Répartition par tâche — {len(self.tache_totals)} tâche(s)"))
            tc2 = card_frame(); tl = QVBoxLayout(tc2); tl.setContentsMargins(16,14,16,14); tl.setSpacing(8)
            all_h2 = sum(self.tache_totals.values()); max_h2 = max(self.tache_totals.values())
            for idx, (tache, h) in enumerate(sorted(self.tache_totals.items(), key=lambda x:x[1], reverse=True)):
                tl.addWidget(self._bar_row(tache, h, all_h2, max_h2, PALETTE[(idx+3)%len(PALETTE)]))
            cl.addWidget(tc2)

    def _tab_calendar(self, cl):
        if not self.weeks:
            cl.addWidget(lbl("Aucune donnée disponible.",14,color=MUTED)); return
        cl.addWidget(self._sec_title("Heatmap — Présence journalière (12 dernières semaines)"))
        heat_card = card_frame()
        hl_out = QVBoxLayout(heat_card); hl_out.setContentsMargins(16,14,16,14); hl_out.setSpacing(8)
        leg = QHBoxLayout(); leg.addStretch()
        for label, color in [("0h", MUTED), ("1–6h", AMBER), ("6–8h", ACC), ("8h+", GREEN)]:
            dot = QFrame(); dot.setFixedSize(12,12); dot.setStyleSheet(f"background:{color}; border-radius:3px;")
            leg.addWidget(dot); leg.addSpacing(3)
            leg.addWidget(lbl(label,9,color=TXT3)); leg.addSpacing(10)
        hl_out.addLayout(leg)
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(3); hdr_row.addSpacing(52)
        for j in JOURS:
            jl = lbl(JOURS_ABRV[j],9,color=TXT3); jl.setFixedWidth(38); jl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr_row.addWidget(jl)
        hdr_row.addStretch(); hl_out.addLayout(hdr_row)
        recent_weeks = list(reversed(self.weeks[-12:] if len(self.weeks)>=12 else self.weeks))
        recent_weeks.reverse()
        for wk in recent_weeks:
            row = QHBoxLayout(); row.setSpacing(3)
            wk_lbl = lbl(wk["monday"].strftime("%d %b"),9,color=TXT3); wk_lbl.setFixedWidth(48)
            row.addWidget(wk_lbl)
            for j in JOURS:
                h = wk["jours"].get(j, 0)
                if h <= 0:   bg, tooltip = MUTED, "Pas de données"
                elif h < 6:  bg, tooltip = AMBER, fmt_h(h)
                elif h < 8:  bg, tooltip = ACC,   fmt_h(h)
                else:         bg, tooltip = GREEN,  f"{fmt_h(h)} ✓"
                cell = QFrame(); cell.setFixedSize(36, 28)
                cell.setStyleSheet(f"background:{bg}; border-radius:5px;")
                cell.setToolTip(f"{j} {fr_date(wk['monday'] + timedelta(days=JOURS.index(j)))} : {tooltip}")
                if h > 0:
                    cell_l = QHBoxLayout(cell); cell_l.setContentsMargins(0,0,0,0)
                    hl2 = QLabel(fmt_h(h) if h >= 6 else f"{int(h)}h"); hl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    hl2.setStyleSheet(f"color:{'white' if not IS_LIGHT else BG}; font-size:8px; font-weight:700; background:transparent;")
                    cell_l.addWidget(hl2)
                row.addWidget(cell)
            tot_c = GREEN if wk["total"]>=35 else AMBER if wk["total"]>0 else MUTED
            tl_lbl = lbl(fmt_h(wk["total"]) if wk["total"] else "–",9,bold=True,color=tot_c); tl_lbl.setFixedWidth(40)
            row.addWidget(tl_lbl); row.addStretch(); hl_out.addLayout(row)
        cl.addWidget(heat_card)
        if self.monthly:
            cl.addWidget(self._sec_title("Total mensuel"))
            mc = card_frame(); ml = QVBoxLayout(mc); ml.setContentsMargins(16,14,16,14); ml.setSpacing(6)
            max_m = max(self.monthly.values()) or 1
            for mkey in sorted(self.monthly.keys(), reverse=True)[:12]:
                h = self.monthly[mkey]
                try: mo = datetime.strptime(mkey, "%Y-%m"); mname = f"{MOIS_FR[mo.month]} {mo.year}"
                except: mname = mkey
                r = QHBoxLayout(); r.setSpacing(10)
                ml2 = lbl(mname,11,color=TXT2); ml2.setFixedWidth(120); r.addWidget(ml2)
                prog = QProgressBar(); prog.setValue(int(h/max_m*100) if max_m else 0)
                prog.setFixedHeight(8); prog.setTextVisible(False)
                col = GREEN if h >= 140 else ACC if h >= 100 else AMBER
                prog.setStyleSheet(f"QProgressBar {{ background:{BG2}; border-radius:4px; border:none; }} QProgressBar::chunk {{ background:{col}; border-radius:4px; }}")
                r.addWidget(prog, 1); r.addWidget(lbl(fmt_h(h),11,bold=True,color=col))
                ml.addLayout(r)
            cl.addWidget(mc)

    def _tab_trends(self, cl):
        if not self.weeks:
            cl.addWidget(lbl("Aucune donnée disponible.",14,color=MUTED)); return
        totals = [w["total"] for w in self.weeks]
        cl.addWidget(self._sec_title("Tendance récente"))
        trend_card = card_frame()
        trl = QHBoxLayout(trend_card); trl.setContentsMargins(16,14,16,14); trl.setSpacing(20)
        if self.trend_prev > 0:
            delta = self.trend_last - self.trend_prev; delta_pct = delta / self.trend_prev * 100
            arrow = "↑" if delta > 0 else "↓"; arrow_col = GREEN if delta > 0 else RED
        else:
            delta = 0; delta_pct = 0; arrow = "→"; arrow_col = AMBER
        for k in (
            self._kpi_card("4 dernières sem.", fmt_h(self.trend_last), ACC, "moyenne hebdo","📊"),
            self._kpi_card("4 sem. précédentes", fmt_h(self.trend_prev) if self.trend_prev else "–", TXT2, "référence","📋"),
            self._kpi_card("Évolution", f"{arrow} {abs(delta_pct):.1f}%", arrow_col, f"{'+' if delta>0 else ''}{fmt_h(abs(delta))} en moyenne","📈"),
            self._kpi_card("Projection sem.", fmt_h(self.projection) if self.projection > 0 else "–",
                GREEN if self.projection >= 35 else AMBER if self.projection > 0 else MUTED,
                "estimation semaine en cours","🔮"),
        ): trl.addWidget(k, 1)
        cl.addWidget(trend_card)

        cl.addWidget(self._sec_title("Évolution des 16 dernières semaines"))
        chart_card = card_frame()
        chart_l = QVBoxLayout(chart_card); chart_l.setContentsMargins(16,14,16,14); chart_l.setSpacing(0)
        recent16 = self.weeks[-16:] if len(self.weeks) >= 16 else self.weeks
        max_t = max((w["total"] for w in recent16), default=1) or 1
        BAR_MAX = 160
        bars_row = QHBoxLayout(); bars_row.setSpacing(4); bars_row.setAlignment(Qt.AlignmentFlag.AlignBottom)
        for wk in recent16:
            col_w = QWidget(); col_w.setStyleSheet("background:transparent;")
            col_l = QVBoxLayout(col_w); col_l.setContentsMargins(0,0,0,0); col_l.setSpacing(2)
            col_l.setAlignment(Qt.AlignmentFlag.AlignBottom)
            bar_h = max(4, int(wk["total"] / max_t * BAR_MAX)); t = wk["total"]
            bar_col = GREEN if t>=40 else ACC if t>=35 else AMBER if t>0 else MUTED
            col_l.addWidget(QWidget()); col_l.itemAt(0).widget().setFixedSize(26, BAR_MAX - bar_h)
            col_l.itemAt(0).widget().setStyleSheet("background:transparent;")
            bar = QFrame(); bar.setFixedSize(26, bar_h)
            bar.setStyleSheet(f"background:{bar_col}; border-radius:4px 4px 0 0;")
            bar.setToolTip(f"{wk['label']}\n{fmt_h(t)}")
            h_lbl = QLabel(fmt_h(t) if t else "–"); h_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            h_lbl.setStyleSheet(f"color:{bar_col}; font-size:8px; font-weight:700; background:transparent;")
            d_lbl = QLabel(wk["monday"].strftime("%d/%m")); d_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            d_lbl.setStyleSheet(f"color:{TXT3}; font-size:8px; background:transparent;")
            col_l.addWidget(bar); col_l.addWidget(h_lbl); col_l.addWidget(d_lbl)
            bars_row.addWidget(col_w)
        bars_row.addStretch(); chart_l.addLayout(bars_row)
        ref_line = QFrame(); ref_line.setFixedHeight(1); ref_line.setStyleSheet(f"background:{GREEN}; margin:4px 0;")
        chart_l.addWidget(ref_line); chart_l.addWidget(lbl("── Objectif 35h",9,color=GREEN))
        cl.addWidget(chart_card)

        cl.addWidget(self._sec_title("Insights automatiques"))
        insights_card = card_frame()
        il = QVBoxLayout(insights_card); il.setContentsMargins(16,14,16,14); il.setSpacing(8)
        for icon, text, color in self._generate_insights(totals):
            row = QHBoxLayout(); row.setSpacing(10)
            ico_lbl = QLabel(icon); ico_lbl.setStyleSheet("background:transparent; font-size:16px;")
            ico_lbl.setFixedWidth(28); row.addWidget(ico_lbl)
            txt_lbl = lbl(text, 11, color=color); txt_lbl.setWordWrap(True)
            row.addWidget(txt_lbl, 1); il.addLayout(row)
            sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"color:{BORDER}; background:{BORDER};"); sep.setFixedHeight(1)
            il.addWidget(sep)
        cl.addWidget(insights_card)

    def _generate_insights(self, totals) -> list:
        insights = []
        if not totals: return insights
        non_zero = [t for t in totals if t > 0]
        avg = sum(non_zero)/len(non_zero) if non_zero else 0
        if self.streak >= 4:
            insights.append(("🔥", f"Série impressionnante ! {self.streak} semaines consécutives de 35h+. Excellent rythme.", GREEN))
        elif self.streak >= 2:
            insights.append(("🔥", f"{self.streak} semaines consécutives complètes. Continuez !", AMBER))
        if avg >= 38:
            insights.append(("💪", f"Moyenne de {fmt_h(avg)} — Tu dépasses régulièrement les 35h. Attention à l'équilibre.", AMBER))
        elif avg >= 35:
            insights.append(("✅", f"Moyenne de {fmt_h(avg)} — Tu atteins l'objectif de 35h/sem. en moyenne. Bravo !", GREEN))
        elif avg > 0:
            insights.append(("📉", f"Moyenne de {fmt_h(avg)} — Il manque en moyenne {fmt_h(35-avg)} pour atteindre 35h.", RED))
        if self.overtime_h > 20:
            insights.append(("⏰", f"{fmt_h(self.overtime_h)} d'heures supplémentaires (>8h/jour) accumulées au total.", AMBER))
        total_dist = self.matin_h + self.aprem_h
        if total_dist > 0:
            mat_pct = self.matin_h / total_dist * 100
            if mat_pct > 65:
                insights.append(("🌅", f"Tu travailles principalement le matin ({mat_pct:.0f}% des heures avant midi).", ACC))
            elif mat_pct < 35:
                insights.append(("🌆", f"Tu travailles principalement l'après-midi ({100-mat_pct:.0f}% des heures).", ACC))
        if len(totals) >= 3 and all(t == 0 for t in totals[-3:]):
            insights.append(("⚠️", "Aucune heure enregistrée sur les 3 dernières semaines.", RED))
        if self.trend_prev > 0 and self.trend_last > self.trend_prev * 1.15:
            insights.append(("📈", f"Ta productivité est en hausse ! +{(self.trend_last/self.trend_prev-1)*100:.0f}% vs les 4 semaines précédentes.", GREEN))
        elif self.trend_prev > 0 and self.trend_last < self.trend_prev * 0.85:
            insights.append(("📉", f"Baisse de rythme détectée : -{(1-self.trend_last/self.trend_prev)*100:.0f}% vs les 4 semaines précédentes.", AMBER))
        if not insights:
            insights.append(("💡", "Continuez à enregistrer vos heures pour obtenir des analyses plus précises.", TXT2))
        return insights

    def _sec_title(self, text):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w); hl.setContentsMargins(2,4,0,0); hl.setSpacing(8)
        dot = QFrame(); dot.setFixedSize(6,6); dot.setStyleSheet(f"background:{ACC}; border-radius:3px;")
        hl.addWidget(dot); hl.addWidget(lbl(text,11,bold=True)); hl.addStretch(); return w

    def _kpi_card(self, title, val, color, sub, icon):
        c = QFrame(); c.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-top:3px solid {color}; border-radius:12px;")
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

    def _bar_row_rich(self, name, h, all_h, max_h, color, days):
        row = QFrame(); row.setStyleSheet(f"background:{CARD2}; border-radius:9px; border:none;")
        rl = QHBoxLayout(row); rl.setContentsMargins(0,7,12,7); rl.setSpacing(0)
        bl2 = QFrame(); bl2.setFixedWidth(4); bl2.setStyleSheet(f"background:{color}; border-radius:2px; margin:4px 0;"); rl.addWidget(bl2)
        info = QWidget(); info.setStyleSheet("background:transparent;")
        il = QVBoxLayout(info); il.setContentsMargins(12,0,0,0); il.setSpacing(4)
        tr = QHBoxLayout(); tr.addWidget(lbl(name,11,bold=True)); tr.addStretch()
        sub_info = f"{fmt_h(h)}  ·  {h/all_h*100:.1f}%" + (f"  ·  {days} j." if days > 0 else "")
        tr.addWidget(lbl(sub_info,11,color=color)); il.addLayout(tr)
        prog = QProgressBar(); prog.setValue(int(h/max_h*100)); prog.setFixedHeight(6); prog.setTextVisible(False)
        prog.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:3px; border:none; }} QProgressBar::chunk {{ background:{color}; border-radius:3px; }}")
        il.addWidget(prog); rl.addWidget(info); return row

    def _footer(self, lay):
        foot = QFrame(); foot.setFixedHeight(30)
        foot.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fl = QHBoxLayout(foot); fl.setContentsMargins(20,0,20,0)
        fl.addWidget(lbl(f"Groupe ADE  ·  {APP_VERSION}",9,color=TXT3)); fl.addStretch()
        fl.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); lay.addWidget(foot)

# ╔══════════════════════════════════════════════════════════════╗
# ║              SYSTÈME D'ACHIEVEMENTS / BADGES                ║
# ╚══════════════════════════════════════════════════════════════╝

ACHIEVEMENTS_DEF = [
    # ── Semaine ──────────────────────────────────────────────────────
    {"id":"sem_35",     "icon":"✅", "titre":"Semaine complète",      "desc":"35h dans une semaine",              "type":"semaine",     "seuil":35,   "color":"#34D399", "tier":1},
    {"id":"sem_40",     "icon":"💪", "titre":"Au-delà des limites",   "desc":"40h dans une semaine",              "type":"semaine",     "seuil":40,   "color":"#4F8EF7", "tier":2},
    {"id":"sem_45",     "icon":"🔥", "titre":"En feu !",              "desc":"45h dans une semaine",              "type":"semaine",     "seuil":45,   "color":"#FB923C", "tier":2},
    {"id":"sem_50",     "icon":"⚡", "titre":"Mode turbo",            "desc":"50h dans une semaine",              "type":"semaine",     "seuil":50,   "color":"#FBBF24", "tier":3},
    {"id":"sem_60",     "icon":"🚀", "titre":"Workaholique",          "desc":"60h dans une semaine",              "type":"semaine",     "seuil":60,   "color":"#F472B6", "tier":3},
    # ── Série ────────────────────────────────────────────────────────
    {"id":"serie_2",    "icon":"🔗", "titre":"Dans le rythme",        "desc":"2 semaines complètes de suite",     "type":"serie",       "seuil":2,    "color":"#34D399", "tier":1},
    {"id":"serie_4",    "icon":"📅", "titre":"Un mois solide",        "desc":"4 semaines complètes de suite",     "type":"serie",       "seuil":4,    "color":"#4F8EF7", "tier":2},
    {"id":"serie_8",    "icon":"🏅", "titre":"Deux mois non-stop",    "desc":"8 semaines complètes de suite",     "type":"serie",       "seuil":8,    "color":"#FB923C", "tier":2},
    {"id":"serie_12",   "icon":"👑", "titre":"Trimestre parfait",     "desc":"12 semaines de suite",              "type":"serie",       "seuil":12,   "color":"#FBBF24", "tier":3},
    {"id":"serie_26",   "icon":"🌟", "titre":"Demi-année légendaire", "desc":"26 semaines de suite",              "type":"serie",       "seuil":26,   "color":"#A78BFA", "tier":3},
    # ── Annuel ───────────────────────────────────────────────────────
    {"id":"an_100",     "icon":"💯", "titre":"Centenaire",            "desc":"100h dans l'année",                 "type":"annuel",      "seuil":100,  "color":"#34D399", "tier":1},
    {"id":"an_200",     "icon":"📈", "titre":"200h !",                "desc":"200h dans l'année",                 "type":"annuel",      "seuil":200,  "color":"#4F8EF7", "tier":1},
    {"id":"an_500",     "icon":"🏆", "titre":"Demi-millénaire",       "desc":"500h dans l'année",                 "type":"annuel",      "seuil":500,  "color":"#FB923C", "tier":2},
    {"id":"an_1000",    "icon":"💎", "titre":"Millénaire",            "desc":"1000h dans l'année",                "type":"annuel",      "seuil":1000, "color":"#FBBF24", "tier":2},
    {"id":"an_1500",    "icon":"🌙", "titre":"Nuit et jour",          "desc":"1500h dans l'année",                "type":"annuel",      "seuil":1500, "color":"#A78BFA", "tier":3},
    {"id":"an_2000",    "icon":"🎯", "titre":"Perfectionniste",       "desc":"2000h dans l'année",                "type":"annuel",      "seuil":2000, "color":"#F472B6", "tier":3},
    # ── Global ───────────────────────────────────────────────────────
    {"id":"gl_500",     "icon":"🥉", "titre":"Apprenti",              "desc":"500h enregistrées au total",        "type":"global",      "seuil":500,  "color":"#CD7F32", "tier":1},
    {"id":"gl_1000",    "icon":"🥈", "titre":"Confirmé",              "desc":"1000h au total",                    "type":"global",      "seuil":1000, "color":"#C0C0C0", "tier":2},
    {"id":"gl_2000",    "icon":"🥇", "titre":"Expert",                "desc":"2000h au total",                    "type":"global",      "seuil":2000, "color":"#FFD700", "tier":2},
    {"id":"gl_5000",    "icon":"🏛️","titre":"Légende ADE",            "desc":"5000h au total",                    "type":"global",      "seuil":5000, "color":"#A78BFA", "tier":3},
    # ── Spéciaux ─────────────────────────────────────────────────────
    {"id":"sp_5sem",    "icon":"🗓️","titre":"Fidèle",                 "desc":"5 semaines enregistrées",           "type":"nb_sem",      "seuil":5,    "color":"#34D399", "tier":1},
    {"id":"sp_20sem",   "icon":"📋", "titre":"Régulier",              "desc":"20 semaines enregistrées",          "type":"nb_sem",      "seuil":20,   "color":"#4F8EF7", "tier":2},
    {"id":"sp_50sem",   "icon":"📚", "titre":"Vétéran",               "desc":"50 semaines enregistrées",          "type":"nb_sem",      "seuil":50,   "color":"#FBBF24", "tier":3},
    {"id":"sp_lundi",   "icon":"🌅", "titre":"Lève-tôt",              "desc":"Journée de lundi ≥ 9h",             "type":"jour_max",    "seuil":9,    "color":"#22D3EE", "tier":1, "jour":"Lundi"},
    {"id":"sp_vendredi","icon":"🎉", "titre":"TGIF marathon",         "desc":"Journée de vendredi ≥ 9h",          "type":"jour_max",    "seuil":9,    "color":"#F472B6", "tier":1, "jour":"Vendredi"},
    {"id":"sp_parfait", "icon":"⭐", "titre":"Semaine parfaite",      "desc":"5h+ chaque jour de la semaine",     "type":"sem_parfaite","seuil":5,    "color":"#FBBF24", "tier":3},
]

# Index rapide par ID
_ACH_INDEX: dict[str, dict] = {a["id"]: a for a in ACHIEVEMENTS_DEF}
TIER_LABELS = {1: "Bronze", 2: "Argent", 3: "Or"}
TIER_COLORS = {1: "#CD7F32", 2: "#C0C0C0", 3: "#FFD700"}


class AchievementStore:
    """Persistance des achievements — lecture/écriture atomique avec cache en mémoire."""
    _cache: dict | None = None

    @classmethod
    def _get(cls) -> dict:
        if cls._cache is None:
            try:
                with open(ACHIEVEMENTS_FILE, "r", encoding="utf-8") as f:
                    cls._cache = json.load(f)
            except: cls._cache = {}
        return cls._cache

    @classmethod
    def _flush(cls):
        with open(ACHIEVEMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(cls._cache, f, ensure_ascii=False, indent=2)

    @classmethod
    def unlock(cls, aid: str) -> bool:
        """Débloque un achievement. Retourne True si c'est nouveau."""
        data = cls._get()
        if aid in data: return False
        data[aid] = datetime.now().strftime("%Y-%m-%d %H:%M")
        cls._flush(); return True

    @classmethod
    def data(cls) -> dict: return cls._get()

    @classmethod
    def is_unlocked(cls, aid: str) -> bool: return aid in cls._get()

    @classmethod
    def invalidate(cls): cls._cache = None


def compute_achievements(weeks: list) -> list[str]:
    """Retourne la liste des IDs nouvellement débloqués."""
    if not weeks: return []
    newly = []
    totals      = [w["total"] for w in weeks]
    this_year   = datetime.today().year
    annual      = sum(w["total"] for w in weeks if w["monday"].year == this_year)
    total_global= sum(totals)
    nb_sem      = sum(1 for t in totals if t > 0)

    # Streak consécutif (semaines ≥ 35h)
    streak = 0
    check = get_monday(datetime.today())
    week_map = {w["monday"].date(): w for w in weeks}
    while True:
        wk = week_map.get(check.date())
        if wk and wk["total"] >= 35: streak += 1; check -= timedelta(weeks=1)
        else: break

    for ach in ACHIEVEMENTS_DEF:
        aid   = ach["id"]
        t     = ach["type"]
        seuil = ach["seuil"]
        if AchievementStore.is_unlocked(aid): continue  # déjà acquis → skip
        unlocked = False
        if   t == "semaine":     unlocked = any(w["total"] >= seuil for w in weeks)
        elif t == "serie":       unlocked = streak >= seuil
        elif t == "annuel":      unlocked = annual >= seuil
        elif t == "global":      unlocked = total_global >= seuil
        elif t == "nb_sem":      unlocked = nb_sem >= seuil
        elif t == "jour_max":
            jour = ach.get("jour","")
            unlocked = any(w["jours"].get(jour,0) >= seuil for w in weeks)
        elif t == "sem_parfaite":
            unlocked = any(all(w["jours"].get(j,0) >= seuil for j in JOURS) for w in weeks)
        if unlocked and AchievementStore.unlock(aid):
            newly.append(aid)
    return newly


# ── Toast d'achievement animé ─────────────────────────────────────────────────
class AchievementToast(QFrame):
    """Notification toast animée, slide-in depuis le bas à droite, auto-disparaît après 4s."""

    def __init__(self, parent, ach: dict):
        super().__init__(parent)
        color  = ach.get("color", "#4F8EF7")
        tier   = ach.get("tier", 1)
        tier_c = TIER_COLORS.get(tier, "#CD7F32")
        tier_l = TIER_LABELS.get(tier, "Bronze")

        self.setFixedSize(340, 88)
        self.setStyleSheet(f"""
            QFrame {{ background:{CARD}; border:1px solid {color}; border-left:4px solid {color}; border-radius:12px; }}
        """)

        lay = QHBoxLayout(self); lay.setContentsMargins(14,10,14,10); lay.setSpacing(12)

        ico_frame = QFrame(); ico_frame.setFixedSize(52,52)
        ico_frame.setStyleSheet(f"background:{color}33; border-radius:26px; border:2px solid {color};")
        ico_l = QHBoxLayout(ico_frame); ico_l.setContentsMargins(0,0,0,0)
        ico_lbl = QLabel(ach.get("icon","🏆")); ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_lbl.setStyleSheet("font-size:24px; background:transparent; border:none;")
        ico_l.addWidget(ico_lbl); lay.addWidget(ico_frame)

        txt = QVBoxLayout(); txt.setSpacing(2)
        header = QHBoxLayout(); header.setSpacing(6)
        new_badge = QLabel("🔓 ACHIEVEMENT DÉBLOQUÉ")
        new_badge.setStyleSheet(f"color:{color}; font-size:8px; font-weight:800; letter-spacing:1.5px; background:transparent;")
        header.addWidget(new_badge); header.addStretch()
        tier_badge = QLabel(f"● {tier_l}")
        tier_badge.setStyleSheet(f"color:{tier_c}; font-size:8px; font-weight:700; background:transparent;")
        header.addWidget(tier_badge); txt.addLayout(header)
        titre_lbl = QLabel(ach.get("titre",""))
        titre_lbl.setStyleSheet(f"color:{TXT}; font-size:13px; font-weight:800; background:transparent;")
        txt.addWidget(titre_lbl)
        desc_lbl = QLabel(ach.get("desc",""))
        desc_lbl.setStyleSheet(f"color:{TXT2}; font-size:10px; background:transparent;")
        txt.addWidget(desc_lbl); lay.addLayout(txt, 1)

        # Barre timer visuelle
        self._prog_bar = QProgressBar(self)
        self._prog_bar.setGeometry(0, 83, 340, 5)
        self._prog_bar.setTextVisible(False); self._prog_bar.setValue(100)
        self._prog_bar.setStyleSheet(
            f"QProgressBar {{ background:{BORDER}; border-radius:0px; border:none; }}"
            f"QProgressBar::chunk {{ background:{color}; border-radius:0px; }}")

        self._tick = 0
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick_down); self._timer.start(40)
        self._anim_in(color)

    def _anim_in(self, color):
        p = self.parent()
        if not p: return
        pw, ph = p.width(), p.height()
        self.move(pw - self.width() - 24, ph)
        self.show(); self.raise_()
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(350)
        anim.setStartValue(QPoint(pw - self.width() - 24, ph))
        anim.setEndValue(QPoint(pw - self.width() - 24, ph - self.height() - 60))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim = anim; anim.start()

    def _tick_down(self):
        self._tick += 1
        self._prog_bar.setValue(max(0, 100 - self._tick))
        if self._tick >= 100:
            self._timer.stop(); self._anim_out()

    def _anim_out(self):
        p = self.parent()
        if not p: return
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(300)
        anim.setStartValue(self.pos())
        anim.setEndValue(QPoint(self.x(), p.height() + 10))
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.deleteLater)
        self._anim_out_ref = anim; anim.start()


class ToastQueue:
    """File d'attente de toasts — un à la fois, décalés verticalement si plusieurs."""
    def __init__(self, parent):
        self._parent = parent; self._queue: list[str] = []; self._showing = False

    def push(self, aid: str):
        ach = _ACH_INDEX.get(aid)
        if ach: self._queue.append(aid)
        if not self._showing: self._show_next()

    def _show_next(self):
        if not self._queue: self._showing = False; return
        self._showing = True; aid = self._queue.pop(0)
        ach = _ACH_INDEX.get(aid)
        if not ach: self._show_next(); return
        toast = AchievementToast(self._parent, ach)
        p = self._parent; pw, ph = p.width(), p.height()
        toast.move(pw - toast.width() - 24, ph - toast.height() - 60)
        toast.show(); toast.raise_()
        QTimer.singleShot(4500, self._show_next)


# ── AchievementsDialog ────────────────────────────────────────────────────────
class AchievementsDialog(QDialog):
    def __init__(self, parent, weeks: list):
        super().__init__(parent)
        self.setWindowTitle("Trophées — Groupe ADE")
        self.resize(880, 720); self.setMinimumSize(700, 500)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        self._weeks = weeks
        self._data  = AchievementStore.data()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        # Header
        hdr = QFrame(); hdr.setFixedHeight(68)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(22,0,22,0); hl.setSpacing(12)
        ico = QLabel("🏆"); ico.setStyleSheet("font-size:26px; background:transparent;")
        hl.addWidget(ico)
        tc = QVBoxLayout(); tc.setSpacing(2)
        nb_unlocked = len(self._data); nb_total = len(ACHIEVEMENTS_DEF)
        tc.addWidget(lbl("Trophées & Achievements",14,bold=True))
        tc.addWidget(lbl(f"{nb_unlocked} / {nb_total} débloqués  ·  {COPYRIGHT}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch()
        # Barre progression globale
        pf = QFrame(); pf.setFixedWidth(160)
        pf.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:10px;")
        pfl = QVBoxLayout(pf); pfl.setContentsMargins(10,6,10,6); pfl.setSpacing(3)
        pct = int(nb_unlocked/nb_total*100) if nb_total else 0
        pfl.addWidget(lbl(f"{pct}% complété",10,bold=True,color=ACC))
        pg = QProgressBar(); pg.setValue(pct); pg.setFixedHeight(6); pg.setTextVisible(False)
        pg.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:3px; border:none; }} QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC}); border-radius:3px; }}")
        pfl.addWidget(pg); hl.addWidget(pf); lay.addWidget(hdr)

        # Compteurs par tier
        tier_row = QWidget(); tier_row.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        trl = QHBoxLayout(tier_row); trl.setContentsMargins(22,8,22,8); trl.setSpacing(20)
        for tier in (1,2,3):
            ids_tier = [a["id"] for a in ACHIEVEMENTS_DEF if a.get("tier")==tier]
            got = sum(1 for aid in ids_tier if aid in self._data)
            tc2 = QFrame(); tc2.setStyleSheet(f"background:{CARD}; border:1px solid {TIER_COLORS[tier]}44; border-radius:8px;")
            tl2 = QHBoxLayout(tc2); tl2.setContentsMargins(12,5,12,5); tl2.setSpacing(8)
            dot = QFrame(); dot.setFixedSize(10,10); dot.setStyleSheet(f"background:{TIER_COLORS[tier]}; border-radius:5px;")
            tl2.addWidget(dot); tl2.addWidget(lbl(f"{TIER_LABELS[tier]}  {got}/{len(ids_tier)}",10,bold=True,color=TIER_COLORS[tier]))
            trl.addWidget(tc2)
        # Bouton reset (admin) discret
        reset_btn = QPushButton("↺ Réinitialiser"); reset_btn.setFixedHeight(26)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{TXT3}; border:1px solid {BORDER}; border-radius:6px; font-size:9px; padding:0 8px; }} QPushButton:hover {{ color:{RED}; border-color:{RED}; }}")
        reset_btn.clicked.connect(self._reset_achievements); trl.addWidget(reset_btn)
        trl.addStretch(); lay.addWidget(tier_row)

        # Scroll grille
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; }} QWidget {{ background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(); cl = QVBoxLayout(content)
        cl.setContentsMargins(16,14,16,14); cl.setSpacing(16)

        categories = [
            ("🗓️ Semaine",  [a for a in ACHIEVEMENTS_DEF if a["type"]=="semaine"]),
            ("🔗 Séries",   [a for a in ACHIEVEMENTS_DEF if a["type"]=="serie"]),
            ("📅 Annuel",   [a for a in ACHIEVEMENTS_DEF if a["type"]=="annuel"]),
            ("🌍 Global",   [a for a in ACHIEVEMENTS_DEF if a["type"]=="global"]),
            ("⭐ Spéciaux", [a for a in ACHIEVEMENTS_DEF if a["type"] in ("nb_sem","jour_max","sem_parfaite")]),
        ]
        for cat_title, achs in categories:
            cl.addWidget(self._section_title(cat_title))
            grid = QWidget(); grid.setStyleSheet("background:transparent;")
            gl = QHBoxLayout(grid); gl.setContentsMargins(0,0,0,0); gl.setSpacing(10)
            gl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            for ach in achs: gl.addWidget(self._ach_card(ach))
            cl.addWidget(grid)
        cl.addStretch(); scroll.setWidget(content); lay.addWidget(scroll)

        foot = QFrame(); foot.setFixedHeight(30)
        foot.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fl = QHBoxLayout(foot); fl.setContentsMargins(20,0,20,0)
        fl.addWidget(lbl(f"Groupe ADE  ·  {APP_VERSION}",9,color=TXT3)); fl.addStretch()
        fl.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); lay.addWidget(foot)

    def _reset_achievements(self):
        rep = QMessageBox.question(self, "Réinitialiser les trophées",
            "Tous les trophées débloqués seront effacés.\nCette action est irréversible.\n\nContinuer ?")
        if rep == QMessageBox.StandardButton.Yes:
            if os.path.exists(ACHIEVEMENTS_FILE): os.remove(ACHIEVEMENTS_FILE)
            AchievementStore.invalidate()
            QMessageBox.information(self, "Réinitialisé", "✓ Tous les trophées ont été réinitialisés.")
            self.accept()

    def _section_title(self, text):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w); hl.setContentsMargins(2,4,0,0); hl.setSpacing(8)
        dot = QFrame(); dot.setFixedSize(6,6); dot.setStyleSheet(f"background:{ACC}; border-radius:3px;")
        hl.addWidget(dot); hl.addWidget(lbl(text,11,bold=True)); hl.addStretch(); return w

    def _ach_card(self, ach: dict) -> QFrame:
        aid      = ach["id"]
        unlocked = aid in self._data
        color    = ach["color"] if unlocked else MUTED
        tier     = ach.get("tier",1)
        tier_c   = TIER_COLORS[tier] if unlocked else MUTED
        date_str = self._data.get(aid,"")

        card = QFrame(); card.setFixedSize(152, 152)
        border = f"border:2px solid {color};" if unlocked else f"border:1px solid {BORDER};"
        bg     = f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {color}18,stop:1 {color}08);" if unlocked else f"background:{CARD};"
        card.setStyleSheet(f"QFrame {{ {bg} {border} border-radius:14px; }}")

        cl = QVBoxLayout(card); cl.setContentsMargins(10,10,10,10); cl.setSpacing(4)
        cl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        ico_frame = QFrame(); ico_frame.setFixedSize(48,48)
        ico_frame.setStyleSheet(f"background:{color}22; border-radius:24px; border:{'2px solid '+color if unlocked else '1px solid '+BORDER};")
        ifl = QHBoxLayout(ico_frame); ifl.setContentsMargins(0,0,0,0)
        ico_lbl = QLabel(ach["icon"] if unlocked else "🔒")
        ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_lbl.setStyleSheet(f"font-size:{'20' if unlocked else '16'}px; background:transparent; border:none;")
        ifl.addWidget(ico_lbl); cl.addWidget(ico_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        titre_lbl = QLabel(ach["titre"]); titre_lbl.setWordWrap(True)
        titre_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        titre_lbl.setStyleSheet(f"color:{TXT if unlocked else TXT3}; font-size:10px; font-weight:{'800' if unlocked else '600'}; background:transparent;")
        cl.addWidget(titre_lbl)

        desc_lbl = QLabel(ach["desc"]); desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        desc_lbl.setStyleSheet(f"color:{TXT3}; font-size:8px; background:transparent;")
        cl.addWidget(desc_lbl)

        if unlocked:
            bottom_text = f"✓ {date_str[:10]}" if date_str else f"● {TIER_LABELS[tier]}"
            b_lbl = QLabel(bottom_text); b_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            b_lbl.setStyleSheet(f"color:{color if date_str else tier_c}; font-size:8px; font-weight:700; background:transparent;")
            cl.addWidget(b_lbl)

        return card


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
        apply_theme(self.settings.get("theme","Dark Navy"))
        self.setStyleSheet(ss_base())

        self.day_cards: dict[str, DayCard] = {}
        self._dirty    = False
        self._last_pdf = ""
        self._toast_queue: ToastQueue | None = None

        AutoCompleteRegistry.load_all()
        self._build()
        self._toast_queue = ToastQueue(self)
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

        # Navigation semaine
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
            QPushButton {{ background:{ACCD}; color:{ACC2 if not IS_LIGHT else ACC}; border:1px solid {ACC3}; border-radius:8px; font-size:11px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC3}; color:white; }}
        """)
        today_btn.clicked.connect(self._today); nl.addWidget(today_btn)
        lay.addWidget(nav); lay.addWidget(h_sep())

        # Résumé semaine
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
        self.total_big.setStyleSheet(f"color:{ACC2 if not IS_LIGHT else ACC}; font-family:'Segoe UI'; font-size:28px; font-weight:800; background:transparent;")
        tfl.addWidget(self.total_big); tfl.addWidget(lbl("heures cette semaine",10,color=TXT2))
        self.prog = QProgressBar(); self.prog.setFixedHeight(5); self.prog.setTextVisible(False)
        self.prog.setStyleSheet(f"""
            QProgressBar {{ background:{BG}; border-radius:2px; border:none; margin-top:4px; }}
            QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC}); border-radius:2px; }}
        """)
        tfl.addWidget(self.prog); rl2.addWidget(tot_frame)

        # Mini-streak indicator dans sidebar
        self._streak_lbl = lbl("",9,color=TXT3)
        self._streak_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl2.addWidget(self._streak_lbl)
        lay.addWidget(res); lay.addWidget(h_sep())

        # Actions
        act = QWidget(); act.setStyleSheet("background:transparent;")
        al = QVBoxLayout(act); al.setContentsMargins(10,8,10,6); al.setSpacing(3)
        al.addWidget(section_lbl("ACTIONS"))
        for text, cmd in [("📅  Historique",self._historique),("📊  Statistiques",self._stats),
                          ("🏆  Trophées",self._trophees),
                          ("📄  Exporter PDF",self._pdf),("⚙️   Paramètres",self._parametres)]:
            b = sidebar_btn(text); b.clicked.connect(cmd); al.addWidget(b)
        self.send_mail_btn = QPushButton("✉️  Envoyer par courriel")
        self.send_mail_btn.setFixedHeight(34); self.send_mail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mail_bg = f"qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCD},stop:1 #1E2E60)" if not IS_LIGHT else ACCD
        self.send_mail_btn.setStyleSheet(f"""
            QPushButton {{ background:{mail_bg}; color:{ACC2 if not IS_LIGHT else ACC}; border:1px solid {ACC3}; border-radius:8px; padding:0 10px; font-size:11px; font-weight:700; }}
            QPushButton:hover {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC}); color:white; border-color:{ACC}; }}
            QPushButton:pressed {{ background:{ACCD}; }}
        """)
        self.send_mail_btn.clicked.connect(self._envoyer_courriel); al.addWidget(self.send_mail_btn)
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
        upd_bg = "#1A2E10" if not IS_LIGHT else "#D1FAE5"
        self.update_frame.setStyleSheet(f"""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {upd_bg},stop:1 #0F1E0A);
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
                          color:{'#0A1A0A' if not IS_LIGHT else 'white'}; border:none; border-radius:7px; font-size:11px; font-weight:700; }}
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
        self.week_total_lbl.setStyleSheet(f"color:{ACC2 if not IS_LIGHT else ACC}; font-size:14px; font-weight:700; background:{ACCD}; border:1px solid {ACC3}; border-radius:9px; padding:3px 14px;")
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

    # ── Navigation ────────────────────────────────────────────────────────────
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
        self._update_streak_display()

    def _recalc_week(self):
        total = sum(self.day_cards[j].get_total() for j in JOURS)
        txt = fmt_h(total) if total else "0h"
        self.week_total_lbl.setText(f"Total : {txt}"); self.total_big.setText(txt)
        col = GREEN if total>=35 else ACC if total>=15 else AMBER if total>0 else (ACC2 if not IS_LIGHT else ACC)
        self.total_big.setStyleSheet(f"color:{col}; font-family:'Segoe UI'; font-size:28px; font-weight:800; background:transparent;")
        self.prog.setValue(min(int(total/40*100),100))

    def _update_streak_display(self):
        """Met à jour l'indicateur de streak dans la sidebar."""
        try:
            weeks = load_all_weeks()
            streak = 0; check = get_monday(datetime.today())
            week_map = {w["monday"].date(): w for w in weeks}
            while True:
                wk = week_map.get(check.date())
                if wk and wk["total"] >= 35: streak += 1; check -= timedelta(weeks=1)
                else: break
            if streak >= 2:
                icon = "🔥" if streak >= 4 else "✅"
                self._streak_lbl.setText(f"{icon} Série : {streak} semaine{'s' if streak>1 else ''}")
                self._streak_lbl.setStyleSheet(f"color:{GREEN if streak>=4 else AMBER}; font-size:9px; background:transparent;")
            else:
                self._streak_lbl.setText("")
        except: pass

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
        QTimer.singleShot(600, self._check_achievements)
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
    def _trophees(self):
        self._save(silent=True)
        weeks = load_all_weeks()
        AchievementStore.invalidate()  # rafraîchir cache
        AchievementsDialog(self, weeks).exec()

    def _check_achievements(self):
        """Vérifie et affiche les nouveaux achievements débloqués en arrière-plan."""
        if self._toast_queue is None: return
        try:
            weeks = load_all_weeks()
            for aid in compute_achievements(weeks):
                self._toast_queue.push(aid)
            self._update_streak_display()
        except: pass

    def _parametres(self):
        dlg = ParamDialog(self, self.settings)
        dlg.theme_changed.connect(self._apply_theme_live)
        dlg.saved.connect(self._apply_settings)
        old_theme = self.settings.get("theme","Dark Navy")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self._apply_theme_live(old_theme)

    def _apply_theme_live(self, theme_name):
        apply_theme(theme_name)
        app = QApplication.instance()
        pal = app.palette()
        for role, hex_c in [
            (pal.ColorRole.Window, BG), (pal.ColorRole.WindowText, TXT),
            (pal.ColorRole.Base, BG), (pal.ColorRole.AlternateBase, BG2),
            (pal.ColorRole.Text, TXT), (pal.ColorRole.Button, CARD),
            (pal.ColorRole.ButtonText, TXT), (pal.ColorRole.Highlight, ACC),
            (pal.ColorRole.HighlightedText, "#FFFFFF"),
        ]: pal.setColor(role, QColor(hex_c))
        app.setPalette(pal); app.setStyleSheet(ss_base())

        emp_text     = self.emp_entry.text()
        week_data    = {j: self.day_cards[j].get_data() for j in JOURS}
        monday       = self.monday
        update_shown = not self.update_frame.isHidden()
        update_ver   = self.update_ver_lbl.text()
        update_notes = self.update_notes_lbl.text()

        self.autosave_timer.stop()
        old_central = self.centralWidget()
        self.day_cards = {}
        self._build()
        self._toast_queue = ToastQueue(self)
        if old_central: old_central.deleteLater()

        self.emp_entry.setText(emp_text)
        self.monday = monday
        lbl_txt = week_label(monday)
        self.week_lbl.setText(lbl_txt); self.week_info_lbl.setText(f"Semaine du {lbl_txt}")
        for j in JOURS:
            self.day_cards[j].set_date(monday)
            if week_data[j]: self.day_cards[j].load_data(week_data[j])
            while len(self.day_cards[j].rows) < 5: self.day_cards[j].add_blank_row()
        self._recalc_week(); self._dirty = False
        if update_shown:
            self.update_ver_lbl.setText(update_ver)
            self.update_notes_lbl.setText(update_notes)
            self.update_frame.show()
        self.autosave_timer.start(30_000)
        self.status_bar.set("✓ Thème appliqué", GREEN)
        self._update_streak_display()

    def _apply_settings(self, s):
        self.settings = s; write_settings(self.settings)
        self._apply_theme_live(s.get("theme", "Dark Navy"))
        self.emp_entry.setText(s.get("employer", ""))

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
        dlg.exec(); self.status_bar.set("✓ Prêt", GREEN)

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

    # ── PDF (toujours Dark Navy ADE) ──────────────────────────────────────────
    def _generate_pdf_silent(self):
        try: from reportlab.pdfgen import canvas as rl  # noqa
        except ImportError: return ""
        dest = os.path.join(SAVE_PATH, f"GroupeADE_FeuilleTemps_{week_key(self.monday)}.pdf")
        try: self._build_pdf(dest); return dest
        except: return ""

    def _pdf(self):
        try: from reportlab.pdfgen import canvas as rl  # noqa
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

    _s = load_settings()
    apply_theme(_s.get("theme","Dark Navy"))

    pal = app.palette()
    for role, hex_c in [
        (pal.ColorRole.Window, BG), (pal.ColorRole.WindowText, TXT),
        (pal.ColorRole.Base, BG), (pal.ColorRole.AlternateBase, BG2),
        (pal.ColorRole.Text, TXT), (pal.ColorRole.Button, CARD),
        (pal.ColorRole.ButtonText, TXT), (pal.ColorRole.Highlight, ACC),
        (pal.ColorRole.HighlightedText, "#FFFFFF"),
    ]: pal.setColor(role, QColor(hex_c))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())