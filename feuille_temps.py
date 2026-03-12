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
    QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor

# ── Chemins ───────────────────────────────────────────────────────────────────
SAVE_PATH     = os.path.join(os.path.expanduser("~"), "Documents", "FeuilleTemps")
SETTINGS_FILE = os.path.join(SAVE_PATH, "settings.json")
os.makedirs(SAVE_PATH, exist_ok=True)

APP_NAME    = "Groupe ADE"
APP_SUB     = "Feuille de Temps"
APP_VERSION = "v3.6"
COPYRIGHT   = "© 2026 Thierry Rouillard"
DEV_CREDIT  = "Développé par Thierry Rouillard"

# ── Auto-update ───────────────────────────────────────────────────────────────
GITHUB_USER        = "trouillard-star"
GITHUB_REPO        = "feuille-temps-ade"
GITHUB_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest/download/FeuilleTemps_ADE.exe"
EXE_NAME           = "FeuilleTemps_ADE.exe"

# ── Comparateur de versions ───────────────────────────────────────────────────
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

# ── Threads update ────────────────────────────────────────────────────────────
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
            current_dir = os.path.dirname(current_exe)
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

# ── Constantes UI ─────────────────────────────────────────────────────────────
JOURS   = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
MOIS_FR = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
           7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}
PALETTE = ["#4F8EF7","#34D399","#FBBF24","#A78BFA","#F472B6",
           "#22D3EE","#FB923C","#A3E635","#F87171","#2DD4BF"]

BG      = "#080C14"; BG2 = "#0D1220"; BG3 = "#111827"
CARD    = "#141C2E"; CARD2 = "#1A2340"
ACC     = "#4F8EF7"; ACC2 = "#7EAAFF"; ACC3 = "#2A5FD4"; ACCD = "#1A3A8A"
GREEN   = "#34D399"; GREEN2 = "#059669"
RED     = "#F87171"; AMBER = "#FBBF24"
TXT     = "#EEF2FF"; TXT2 = "#6B7FAA"; TXT3 = "#3D4F72"
MUTED   = "#2D3A55"; BORDER = "#1E2C47"; BORDER2 = "#263351"; ROW = "#0F1629"

SS_BASE = f"""
    QWidget {{ background:{BG}; color:{TXT}; font-family:'Segoe UI'; font-size:13px; }}
    QScrollBar:vertical {{ background:{BG2}; width:5px; border-radius:3px; }}
    QScrollBar::handle:vertical {{ background:{BORDER2}; border-radius:3px; min-height:24px; }}
    QScrollBar::handle:vertical:hover {{ background:{ACC3}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar:horizontal {{ height:0; }}
    QToolTip {{ background:{CARD2}; color:{TXT}; border:1px solid {ACC3}; padding:5px 8px; border-radius:6px; font-size:12px; }}
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
    except: return {"employer":"", "email_dest":"", "email_cc":""}

def write_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def glow(widget, color=ACC, radius=16):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(radius); fx.setColor(QColor(color)); fx.setOffset(0,0)
    widget.setGraphicsEffect(fx)

# ── Widget helpers ────────────────────────────────────────────────────────────
def lbl(text, size=12, bold=False, color=TXT):
    l = QLabel(text); f = QFont("Segoe UI", size); f.setBold(bold)
    l.setFont(f); l.setStyleSheet(f"color:{color}; background:transparent;")
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

_DUR_ON  = f"color:{ACC2}; background:transparent; font-weight:700; font-size:12px;"
_DUR_OFF = f"color:{MUTED}; background:transparent; font-weight:600; font-size:12px;"

# ── Colonnes header — NOUVELLE COLONNE TÂCHE ─────────────────────────────────
# (Date, Début, Fin, Tâche, Projet, Client/Desc, Durée, Suppr)
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
        self.tache  = AutoEntry("tache",  "Tâche...",  140)   # ← nouvelle colonne
        self.projet = AutoEntry("projet", "Projet...", 150)
        self.desc   = AutoEntry("desc",   "Client lié au projet...")
        self.desc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.dur_lbl = QLabel("–"); self.dur_lbl.setFixedWidth(64)
        self.dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.dur_lbl.setStyleSheet(_DUR_OFF)

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
        self.dur_lbl.setText(fmt_h(h) if h else "–")
        self.dur_lbl.setStyleSheet(_DUR_ON if h else _DUR_OFF)
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
        self.dur_lbl.setText("–"); self.dur_lbl.setStyleSheet(_DUR_OFF)

# ── DayCard ───────────────────────────────────────────────────────────────────
class DayCard(QFrame):
    data_changed = pyqtSignal()

    def __init__(self, jour, idx):
        super().__init__()
        self.jour = jour; self.idx = idx; self.rows = []; self.monday = None
        self.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;")

        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)

        # Header card
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

        # Col headers
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
        self.setStyleSheet(SS_BASE + f"QDialog {{ background:{BG}; }}")
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

# ── ParamDialog ───────────────────────────────────────────────────────────────
class ParamDialog(QDialog):
    saved = pyqtSignal(dict)

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle("Paramètres — Groupe ADE"); self.setFixedSize(460,400)
        self.setStyleSheet(SS_BASE + f"QDialog {{ background:{BG}; }}")
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        hdr = QFrame(); hdr.setFixedHeight(60)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        hl.addWidget(QLabel("⚙️")); hl.addSpacing(8)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(lbl("Paramètres",14,bold=True))
        tc.addWidget(lbl("Configuration de l'application",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch(); lay.addWidget(hdr)

        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,18,20,18); bl.setSpacing(12)

        # Bloc employé
        frm1 = QFrame(); frm1.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:12px;")
        f1l = QVBoxLayout(frm1); f1l.setContentsMargins(14,12,14,14); f1l.setSpacing(6)
        f1l.addWidget(lbl("👤  Nom de l'employé",10,bold=True,color=TXT2))
        self.emp = styled_entry("Votre nom complet", height=34)
        self.emp.setText(settings.get("employer","")); f1l.addWidget(self.emp); bl.addWidget(frm1)

        # Bloc courriel
        frm2 = QFrame(); frm2.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:12px;")
        f2l = QVBoxLayout(frm2); f2l.setContentsMargins(14,12,14,14); f2l.setSpacing(8)

        eh = QHBoxLayout()
        eh.addWidget(lbl("✉️  Envoi par courriel",10,bold=True,color=TXT2)); eh.addStretch()
        eh.addWidget(lbl("Bouton « Envoyer »",9,color=TXT3)); f2l.addLayout(eh)

        f2l.addWidget(lbl("Destinataire (À :)",9,color=TXT3))
        self.email_dest = styled_entry("superviseur@groupeade.com", height=34)
        self.email_dest.setText(settings.get("email_dest","")); f2l.addWidget(self.email_dest)

        f2l.addWidget(lbl("Copie conforme (CC :)  — optionnel",9,color=TXT3))
        self.email_cc = styled_entry("rh@groupeade.com  ou  laisser vide", height=34)
        self.email_cc.setText(settings.get("email_cc","")); f2l.addWidget(self.email_cc)
        bl.addWidget(frm2)

        save_btn = QPushButton("💾  Enregistrer les paramètres"); save_btn.setFixedHeight(42)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                          color:white; border:none; border-radius:10px; font-size:13px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC}; }}
        """)
        save_btn.clicked.connect(self._save); bl.addWidget(save_btn)
        lay.addWidget(body)

        foot = QFrame(); foot.setFixedHeight(28)
        foot.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER};")
        fl2 = QHBoxLayout(foot); fl2.setContentsMargins(14,0,14,0); fl2.addStretch()
        fl2.addWidget(lbl(f"{DEV_CREDIT}  ·  {COPYRIGHT}",9,color=TXT3)); lay.addWidget(foot)

    def _save(self):
        self.s["employer"]   = self.emp.text()
        self.s["email_dest"] = self.email_dest.text().strip()
        self.s["email_cc"]   = self.email_cc.text().strip()
        self.saved.emit(self.s); self.accept()

# ── EnvoiDialog ───────────────────────────────────────────────────────────────
class EnvoiDialog(QDialog):
    """Prévisualisation courriel — ouvre le client mail par défaut avec mailto:"""

    def __init__(self, parent, employer, week_lbl, total_h, pdf_path, settings):
        super().__init__(parent)
        self.pdf_path = pdf_path; self.settings = settings
        self.setWindowTitle("Envoyer la feuille de temps — Groupe ADE")
        self.setFixedSize(560, 630)
        self.setStyleSheet(SS_BASE + f"QDialog {{ background:{BG}; }}")

        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        # Header
        hdr = QFrame(); hdr.setFixedHeight(62)
        hdr.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        ico = QLabel("✉️"); ico.setStyleSheet("font-size:22px; background:transparent;")
        hl.addWidget(ico); hl.addSpacing(8)
        tc = QVBoxLayout(); tc.setSpacing(1)
        tc.addWidget(lbl("Envoyer la feuille de temps",14,bold=True))
        tc.addWidget(lbl(f"Semaine du {week_lbl}",10,color=TXT2))
        hl.addLayout(tc); hl.addStretch(); lay.addWidget(hdr)

        # Corps
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(20,16,20,16); bl.setSpacing(10)

        # Champs À / CC / Objet
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

        # Message
        bl.addWidget(lbl("Message :",10,bold=True,color=TXT2))
        self.msg_edit = QTextEdit(); self.msg_edit.setFixedHeight(175)
        self.msg_edit.setStyleSheet(f"""
            QTextEdit {{ background:{CARD}; color:{TXT}; border:1px solid {BORDER}; border-radius:10px;
                        padding:10px; font-family:'Segoe UI'; font-size:13px; }}
            QTextEdit:focus {{ border-color:{ACC}; }}
        """)
        self.msg_edit.setPlainText(
            f"Bonjour,\n\n"
            f"Veuillez trouver ci-joint ma feuille de temps pour la semaine du {week_lbl}.\n\n"
            f"Total des heures : {total_h}\n\n"
            f"Cordialement,\n{employer}"
        )
        bl.addWidget(self.msg_edit)

        # Pièce jointe
        att_row = QHBoxLayout(); att_row.setSpacing(8)
        att_row.addWidget(QLabel("📎"))
        fname = os.path.basename(pdf_path) if pdf_path and os.path.exists(pdf_path) else None
        if fname:
            att_lbl = lbl(fname, 10, color=TXT2)
        else:
            att_lbl = lbl("PDF non encore généré — sera créé automatiquement", 10, color=AMBER)
        att_row.addWidget(att_lbl); att_row.addStretch(); bl.addLayout(att_row)

        # Hint
        hint = lbl("💡 Votre client de messagerie s'ouvrira avec le courriel prêt.\n"
                   "    Glissez-déposez le PDF dans le courriel avant d'envoyer.", 9, color=TXT3)
        hint.setWordWrap(True); bl.addWidget(hint)

        # Boutons
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
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                color:white; border:none; border-radius:9px; font-size:13px; font-weight:600;
            }}
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
        to   = self.to_entry.text().strip()
        cc   = self.cc_entry.text().strip()
        subj = self.subj_entry.text().strip()
        body = self.msg_edit.toPlainText().strip()

        if not to:
            QMessageBox.warning(self, "Destinataire manquant",
                "Veuillez entrer une adresse dans le champ « À ».")
            self.to_entry.setFocus(); return

        # Sauvegarder les adresses pour la prochaine fois
        self.settings["email_dest"] = to
        self.settings["email_cc"]   = cc
        write_settings(self.settings)

        # Construire l'URI mailto:
        params = {"subject": subj, "body": body}
        if cc: params["cc"] = cc
        query      = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        mailto_uri = f"mailto:{urllib.parse.quote(to)}?{query}"

        try:
            if sys.platform == "win32":
                os.startfile(mailto_uri)
                # Ouvrir l'explorateur sur le dossier du PDF pour faciliter le glisser-déposer
                if self.pdf_path and os.path.exists(self.pdf_path):
                    subprocess.Popen(["explorer", "/select,", self.pdf_path],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", mailto_uri])
                if self.pdf_path and os.path.exists(self.pdf_path):
                    subprocess.Popen(["open", "-R", self.pdf_path])
            else:
                subprocess.Popen(["xdg-open", mailto_uri])

            msg = ("✓ Votre client de messagerie s'est ouvert avec le courriel prêt.\n\n"
                   f"📎 Le dossier contenant le PDF s'est aussi ouvert :\n"
                   f"   {os.path.basename(self.pdf_path)}\n\n"
                   "Glissez-déposez le PDF dans le courriel, puis cliquez Envoyer."
                   if self.pdf_path and os.path.exists(self.pdf_path)
                   else "✓ Votre client de messagerie s'est ouvert avec le courriel prêt à envoyer.")

            QMessageBox.information(self, "Courriel préparé — Groupe ADE", msg)
            self.accept()
        except Exception as ex:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le client mail :\n{ex}")

# ── StatsDialog ───────────────────────────────────────────────────────────────
class StatsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Statistiques — Groupe ADE"); self.resize(920,720)
        self.setStyleSheet(SS_BASE + f"QDialog {{ background:{BG}; }}")
        self._load(); self._build()

    def _load(self):
        self.weeks = []; self.proj_totals = {}
        for monday in saved_weeks():
            try:
                with open(save_file(monday),"r",encoding="utf-8") as f: d = json.load(f)
                total = 0.0; jour_h = {}
                for j in JOURS:
                    jt = 0.0
                    for r in d.get("jours",{}).get(j,[]):
                        h = calc_h(r.get("debut",""), r.get("fin",""))
                        jt += h
                        p = r.get("projet","").strip()
                        if p and h > 0: self.proj_totals[p] = self.proj_totals.get(p,0.0)+h
                    jour_h[j] = jt; total += jt
                self.weeks.append({"monday":monday,"label":week_label(monday),"total":total,"jours":jour_h})
            except: pass

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
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
        cl.setContentsMargins(16,16,16,16); cl.setSpacing(12)
        scroll.setWidget(content); lay.addWidget(scroll)

        if not self.weeks:
            cl.addWidget(lbl("Aucune donnée disponible.",14,color=MUTED)); cl.addStretch()
            self._footer(lay); return

        totals = [w["total"] for w in self.weeks]; non_zero = [t for t in totals if t>0]
        best = max(self.weeks, key=lambda w: w["total"]) if self.weeks else None

        cr = QHBoxLayout(); cr.setSpacing(10)
        for title, val, color, sub, icon in [
            ("Total cumulé",   fmt_h(sum(totals)),   ACC,   f"{len(non_zero)} sem. actives","⏱"),
            ("Moyenne / sem.", fmt_h(sum(non_zero)/len(non_zero)) if non_zero else "–", GREEN, f"sur {len(non_zero)} sem.","📈"),
            ("Meilleure sem.", fmt_h(max(totals)) if totals else "–", AMBER, best["label"] if best and best["total"]>0 else "–","🏆"),
            ("Sem. actives",   str(len(non_zero)), ACC2, f"sur {len(self.weeks)} total","📅"),
        ]:
            c = QFrame(); c.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-top:2px solid {color}; border-radius:12px;")
            cv = QVBoxLayout(c); cv.setContentsMargins(14,12,14,12); cv.setSpacing(3)
            th = QHBoxLayout(); th.addWidget(lbl(title,10,bold=True,color=TXT2)); th.addStretch(); th.addWidget(QLabel(icon))
            cv.addLayout(th); cv.addWidget(lbl(val,22,bold=True,color=color)); cv.addWidget(lbl(sub,10,color=TXT3))
            cr.addWidget(c)
        cl.addLayout(cr)

        if self.proj_totals:
            pc = QFrame(); pc.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:12px;")
            pl = QVBoxLayout(pc); pl.setContentsMargins(16,14,16,14); pl.setSpacing(7)
            ph = QHBoxLayout(); ph.addWidget(lbl("Heures par projet",12,bold=True)); ph.addStretch()
            ph.addWidget(lbl(f"{len(self.proj_totals)} projet(s)",10,color=TXT3)); pl.addLayout(ph)
            all_h = sum(self.proj_totals.values()); max_h = max(self.proj_totals.values())
            for idx,(proj,h) in enumerate(sorted(self.proj_totals.items(),key=lambda x:x[1],reverse=True)):
                color = PALETTE[idx%len(PALETTE)]
                row = QFrame(); row.setStyleSheet(f"background:{CARD2}; border-radius:9px; border:none;")
                rl = QHBoxLayout(row); rl.setContentsMargins(0,7,12,7); rl.setSpacing(0)
                bl2 = QFrame(); bl2.setFixedWidth(4); bl2.setStyleSheet(f"background:{color}; border-radius:2px; margin:4px 0;"); rl.addWidget(bl2)
                info = QWidget(); info.setStyleSheet("background:transparent;")
                il = QVBoxLayout(info); il.setContentsMargins(12,0,0,0); il.setSpacing(4)
                tr = QHBoxLayout(); tr.addWidget(lbl(proj,11,bold=True)); tr.addStretch()
                tr.addWidget(lbl(f"{fmt_h(h)}  ·  {h/all_h*100:.1f}%",11,color=color)); il.addLayout(tr)
                prog = QProgressBar(); prog.setValue(int(h/max_h*100)); prog.setFixedHeight(5); prog.setTextVisible(False)
                prog.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:2px; border:none; }} QProgressBar::chunk {{ background:{color}; border-radius:2px; }}")
                il.addWidget(prog); rl.addWidget(info); pl.addWidget(row)
            cl.addWidget(pc)

        dc = QFrame(); dc.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:12px;")
        dl = QVBoxLayout(dc); dl.setContentsMargins(16,14,16,14); dl.setSpacing(8)
        dl.addWidget(lbl("Moyenne par jour",12,bold=True))
        sums={j:0.0 for j in JOURS}; cnts={j:0 for j in JOURS}
        for wk in self.weeks:
            for j in JOURS:
                v=wk["jours"].get(j,0)
                if v>0: sums[j]+=v; cnts[j]+=1
        max_avg = max((sums[j]/cnts[j] if cnts[j] else 0 for j in JOURS),default=1) or 1
        for j in JOURS:
            avg = sums[j]/cnts[j] if cnts[j] else 0
            r = QHBoxLayout(); r.setSpacing(10)
            jl = lbl(j,11,color=TXT2); jl.setFixedWidth(80); r.addWidget(jl)
            prog = QProgressBar(); prog.setValue(int(avg/max_avg*100) if avg else 0)
            prog.setFixedHeight(10); prog.setTextVisible(False)
            prog.setStyleSheet(f"""
                QProgressBar {{ background:{BG2}; border-radius:5px; border:none; }}
                QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC}); border-radius:5px; }}
            """)
            r.addWidget(prog,1); r.addWidget(lbl(fmt_h(avg) if avg else "–",11,bold=True,color=ACC2 if avg else MUTED))
            dl.addLayout(r)
        cl.addWidget(dc)

        tc2 = QFrame(); tc2.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:12px;")
        tl2 = QVBoxLayout(tc2); tl2.setContentsMargins(16,14,16,14); tl2.setSpacing(0)
        tl2.addWidget(lbl("Détail par semaine",12,bold=True)); tl2.addSpacing(8)
        hd = QFrame(); hd.setStyleSheet(f"background:{CARD2}; border-radius:7px;")
        hdl = QHBoxLayout(hd); hdl.setContentsMargins(12,6,10,6); hdl.setSpacing(4)
        for txt,w in [("Semaine",0),("Lun",60),("Mar",60),("Mer",60),("Jeu",60),("Ven",60),("Total",80)]:
            l = QLabel(txt); l.setStyleSheet(f"color:{TXT3}; font-size:9px; font-weight:700; letter-spacing:1px; background:transparent;")
            if w: l.setFixedWidth(w)
            else: l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hdl.addWidget(l)
        tl2.addWidget(hd)
        for i,wk in enumerate(reversed(self.weeks)):
            row = QFrame(); row.setStyleSheet(f"background:{ROW if i%2==0 else CARD}; border-radius:0;"); row.setFixedHeight(34)
            rl2 = QHBoxLayout(row); rl2.setContentsMargins(12,0,10,0); rl2.setSpacing(4)
            rl2.addWidget(lbl(wk["label"],10))
            for j in JOURS:
                v=wk["jours"].get(j,0); col = GREEN if v>=7 else TXT2 if v>0 else MUTED
                l2 = lbl(fmt_h(v) if v else "–",10,color=col); l2.setFixedWidth(60); rl2.addWidget(l2)
            tc2_col = GREEN if wk["total"]>=35 else AMBER if wk["total"]>0 else MUTED
            tl_r = lbl(fmt_h(wk["total"]) if wk["total"] else "–",10,bold=True,color=tc2_col)
            tl_r.setFixedWidth(80); rl2.addWidget(tl_r); tl2.addWidget(row)
        cl.addWidget(tc2); cl.addStretch(); self._footer(lay)

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
            bold = t.startswith("Groupe")
            lay.addWidget(lbl(t,9,bold=bold,color=TXT3))

    def set(self, text, color):
        self.dot.setStyleSheet(f"color:{color}; font-size:9px; background:transparent;")
        self.msg.setText(text); self.msg.setStyleSheet(f"color:{color}; background:transparent; font-size:10px;")

_SAVE_SS = f"""
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
        self.setStyleSheet(SS_BASE)

        self.today     = datetime.today()
        self.monday    = get_monday(self.today)
        self.settings  = load_settings()
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

        # ── Bouton Envoyer par courriel ─────────────────────────────────────
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

        # Update frame (caché)
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
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor); self.save_btn.setStyleSheet(_SAVE_SS)
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
            self.save_btn.setText("✓  Sauvegardé !")
            self.save_btn.setStyleSheet(_SAVE_SS.replace(ACC3,GREEN2).replace(ACC,GREEN))
            QTimer.singleShot(1800, lambda: (self.save_btn.setText("💾  Sauvegarder"), self.save_btn.setStyleSheet(_SAVE_SS)))

    # ── Actions ───────────────────────────────────────────────────────────────
    def _historique(self):
        dlg = HistoriqueDialog(self); dlg.week_selected.connect(self._load_from_hist); dlg.exec()
    def _load_from_hist(self, monday):
        self._save(silent=True); self.monday=monday; self._last_pdf=""
        for j in JOURS: self.day_cards[j].clear_all()
        self._load_week(monday)
    def _stats(self): self._save(silent=True); StatsDialog(self).exec()
    def _parametres(self):
        dlg = ParamDialog(self, self.settings); dlg.saved.connect(self._apply_settings); dlg.exec()
    def _apply_settings(self, s): self.settings=s; self.emp_entry.setText(s.get("employer",""))
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
                "Aucune adresse courriel n'est encore configurée.\n\n"
                "Voulez-vous ouvrir les Paramètres pour en ajouter une ?")
            if rep == QMessageBox.StandardButton.Yes: self._parametres()
            return
        # Générer le PDF si pas encore fait
        if not self._last_pdf or not os.path.exists(self._last_pdf):
            self.status_bar.set("Génération du PDF…", AMBER)
            QApplication.processEvents()
            self._last_pdf = self._generate_pdf_silent() or ""
        total = sum(self.day_cards[j].get_total() for j in JOURS)
        dlg = EnvoiDialog(self,
                          employer = self.emp_entry.text() or "Employé",
                          week_lbl = week_label(self.monday),
                          total_h  = fmt_h(total) if total else "0h",
                          pdf_path = self._last_pdf,
                          settings = self.settings)
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

    # ── PDF ───────────────────────────────────────────────────────────────────
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
        from reportlab.pdfgen import canvas as rl
        from reportlab.lib.pagesizes import letter
        c = rl.Canvas(dest, pagesize=letter); PW, PH = letter

        def bg(): c.setFillColorRGB(0.031,0.047,0.078); c.rect(0,0,PW,PH,fill=1,stroke=0)

        bg()
        # Header
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
            # Jour header
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
            # Col headers — avec TÂCHE
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
                c.drawString(214, y-7, r.tache.text()[:18])   # Tâche
                c.drawString(310, y-7, r.projet.text()[:16])  # Projet
                c.drawString(400, y-7, r.desc.text()[:22])    # Client / Desc
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