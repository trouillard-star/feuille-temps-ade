"""
╔══════════════════════════════════════════════════════════════╗
║         Feuille de Temps — Le Groupe ADE  v3.11             ║
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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize
from PyQt6.QtWidgets import QLayout
from PyQt6.QtGui import QFont, QColor

# ── Chemins ───────────────────────────────────────────────────────────────────
SAVE_PATH     = os.path.join(os.path.expanduser("~"), "Documents", "FeuilleTemps")
SETTINGS_FILE = os.path.join(SAVE_PATH, "settings.json")
ACHIEVEMENTS_FILE = os.path.join(SAVE_PATH, "achievements.json")
os.makedirs(SAVE_PATH, exist_ok=True)

APP_NAME    = "Groupe ADE"
APP_SUB     = "Feuille de Temps"
APP_VERSION = "v3.13"
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

# unlock_at = total d'heures globales requis pour débloquer (0 = toujours disponible)
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
        "LIGHT": False, "unlock_at": 0,
        "desc": "Thème par défaut",
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
        "LIGHT": False, "unlock_at": 0,
        "desc": "Thème par défaut",
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
        "LIGHT": False, "unlock_at": 0,
        "desc": "Thème par défaut",
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
        "LIGHT": False, "unlock_at": 0,
        "desc": "Thème par défaut",
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
        "LIGHT": False, "unlock_at": 0,
        "desc": "Thème par défaut",
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
        "LIGHT": True, "unlock_at": 0,
        "desc": "Thème par défaut",
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
        "LIGHT": True, "unlock_at": 0,
        "desc": "Thème par défaut",
    },
    # ── Thèmes débloquables ────────────────────────────────────────────────
    "Violet Dream": {
        "BG":"#0A0614","BG2":"#100B1E","BG3":"#150F26",
        "CARD":"#160E2A","CARD2":"#1E1438",
        "ACC":"#C084FC","ACC2":"#D8B4FE","ACC3":"#7C3AED","ACCD":"#2E1065",
        "GREEN":"#4ADE80","GREEN2":"#16A34A",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#FAF5FF","TXT2":"#A78BFA","TXT3":"#4C1D95",
        "MUTED":"#2E1065","BORDER":"#2D1B69","BORDER2":"#4C1D95","ROW":"#0A0614",
        "PALETTE":["#C084FC","#4ADE80","#FCD34D","#38BDF8","#F472B6",
                   "#A78BFA","#FB923C","#A3E635","#F87171","#2DD4BF"],
        "LIGHT": False, "unlock_at": 500,
        "desc": "🔒 Débloqué à 500h cumulées",
    },
    "Cyberpunk": {
        "BG":"#020608","BG2":"#03080C","BG3":"#050C10",
        "CARD":"#060D14","CARD2":"#0A1420",
        "ACC":"#00FFF0","ACC2":"#80FFFA","ACC3":"#00B8AD","ACCD":"#003330",
        "GREEN":"#39FF14","GREEN2":"#27B30E",
        "RED":"#FF0055","AMBER":"#FFE000",
        "TXT":"#E0FFFF","TXT2":"#00B8AD","TXT3":"#004D47",
        "MUTED":"#003330","BORDER":"#00443F","BORDER2":"#006660","ROW":"#020608",
        "PALETTE":["#00FFF0","#39FF14","#FFE000","#FF00FF","#FF0055",
                   "#00B8FF","#FF6600","#CCFF00","#FF0055","#00FFCC"],
        "LIGHT": False, "unlock_at": 500,
        "desc": "🔒 Débloqué à 500h cumulées",
    },
    "Sunset": {
        "BG":"#0F0608","BG2":"#180B10","BG3":"#1E0E14",
        "CARD":"#1C0E14","CARD2":"#26121C",
        "ACC":"#FB923C","ACC2":"#FDBA74","ACC3":"#EA580C","ACCD":"#431407",
        "GREEN":"#4ADE80","GREEN2":"#16A34A",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#FFF7ED","TXT2":"#FDBA74","TXT3":"#7C2D12",
        "MUTED":"#431407","BORDER":"#431407","BORDER2":"#7C2D12","ROW":"#0F0608",
        "PALETTE":["#FB923C","#F472B6","#FCD34D","#C084FC","#4ADE80",
                   "#38BDF8","#F87171","#A3E635","#E879F9","#2DD4BF"],
        "LIGHT": False, "unlock_at": 500,
        "desc": "🔒 Débloqué à 500h cumulées",
    },
    "Deep Ocean": {
        "BG":"#020A12","BG2":"#041524","BG3":"#051C2E",
        "CARD":"#061B30","CARD2":"#082440",
        "ACC":"#22D3EE","ACC2":"#67E8F9","ACC3":"#0891B2","ACCD":"#0E3A4A",
        "GREEN":"#34D399","GREEN2":"#059669",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#ECFEFF","TXT2":"#67E8F9","TXT3":"#164E63",
        "MUTED":"#0E3A4A","BORDER":"#0E3A4A","BORDER2":"#155E75","ROW":"#020A12",
        "PALETTE":["#22D3EE","#34D399","#FCD34D","#818CF8","#F472B6",
                   "#67E8F9","#FB923C","#A3E635","#F87171","#2DD4BF"],
        "LIGHT": False, "unlock_at": 1000,
        "desc": "🔒 Débloqué à 1 000h cumulées",
    },
    "Aurora": {
        "BG":"#030A08","BG2":"#051410","BG3":"#071A15",
        "CARD":"#071A15","CARD2":"#0B261E",
        "ACC":"#2DD4BF","ACC2":"#99F6E4","ACC3":"#0F766E","ACCD":"#042F2E",
        "GREEN":"#A3E635","GREEN2":"#65A30D",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#F0FDFA","TXT2":"#99F6E4","TXT3":"#134E4A",
        "MUTED":"#042F2E","BORDER":"#042F2E","BORDER2":"#115E59","ROW":"#030A08",
        "PALETTE":["#2DD4BF","#A3E635","#818CF8","#F472B6","#FCD34D",
                   "#22D3EE","#34D399","#C084FC","#F87171","#67E8F9"],
        "LIGHT": False, "unlock_at": 1000,
        "desc": "🔒 Débloqué à 1 000h cumulées",
    },
    "Rose Gold": {
        "BG":"#FDF2F5","BG2":"#F9E4EC","BG3":"#FAEDF2",
        "CARD":"#FFFFFF","CARD2":"#FFF0F5",
        "ACC":"#DB2777","ACC2":"#BE185D","ACC3":"#EC4899","ACCD":"#FCE7F3",
        "GREEN":"#059669","GREEN2":"#047857",
        "RED":"#DC2626","AMBER":"#D97706",
        "TXT":"#1F0A12","TXT2":"#831843","TXT3":"#FBCFE8",
        "MUTED":"#FBCFE8","BORDER":"#FCE7F3","BORDER2":"#F9A8D4","ROW":"#FFF5F8",
        "PALETTE":["#DB2777","#059669","#D97706","#7C3AED","#0891B2",
                   "#EA580C","#65A30D","#DC2626","#0D9488","#C026D3"],
        "LIGHT": True, "unlock_at": 1000,
        "desc": "🔒 Débloqué à 1 000h cumulées",
    },
    "Obsidian Gold": {
        "BG":"#080706","BG2":"#0F0E0A","BG3":"#141210",
        "CARD":"#141210","CARD2":"#1C1A14",
        "ACC":"#D4A820","ACC2":"#F5D060","ACC3":"#A07A10","ACCD":"#2A2008",
        "GREEN":"#4ADE80","GREEN2":"#16A34A",
        "RED":"#F87171","AMBER":"#F5D060",
        "TXT":"#FDF8E8","TXT2":"#D4A820","TXT3":"#4A3A10",
        "MUTED":"#2A2008","BORDER":"#2A2008","BORDER2":"#4A3A10","ROW":"#080706",
        "PALETTE":["#D4A820","#4ADE80","#F5D060","#C084FC","#F472B6",
                   "#22D3EE","#FB923C","#A3E635","#F87171","#2DD4BF"],
        "LIGHT": False, "unlock_at": 2000,
        "desc": "🔒 Débloqué à 2 000h cumulées",
    },
    "Sakura": {
        "BG":"#FFF5F7","BG2":"#FFE8EE","BG3":"#FFEEF3",
        "CARD":"#FFFFFF","CARD2":"#FFF0F4",
        "ACC":"#E879F9","ACC2":"#D946EF","ACC3":"#C026D3","ACCD":"#FDF4FF",
        "GREEN":"#059669","GREEN2":"#047857",
        "RED":"#DC2626","AMBER":"#D97706",
        "TXT":"#1A0A1A","TXT2":"#7E22CE","TXT3":"#F5D0FE",
        "MUTED":"#F5D0FE","BORDER":"#FAE8FF","BORDER2":"#F0ABFC","ROW":"#FFF8FA",
        "PALETTE":["#E879F9","#059669","#D97706","#2563EB","#DB2777",
                   "#0891B2","#EA580C","#65A30D","#DC2626","#0D9488"],
        "LIGHT": True, "unlock_at": 2000,
        "desc": "🔒 Débloqué à 2 000h cumulées",
    },
    "Void": {
        "BG":"#000000","BG2":"#050505","BG3":"#080808",
        "CARD":"#0A0A0A","CARD2":"#101010",
        "ACC":"#FFFFFF","ACC2":"#CCCCCC","ACC3":"#888888","ACCD":"#1A1A1A",
        "GREEN":"#4ADE80","GREEN2":"#16A34A",
        "RED":"#F87171","AMBER":"#FCD34D",
        "TXT":"#FFFFFF","TXT2":"#888888","TXT3":"#333333",
        "MUTED":"#1A1A1A","BORDER":"#1A1A1A","BORDER2":"#2A2A2A","ROW":"#000000",
        "PALETTE":["#FFFFFF","#CCCCCC","#888888","#555555","#AAAAAA",
                   "#DDDDDD","#666666","#BBBBBB","#999999","#444444"],
        "LIGHT": False, "unlock_at": 5000,
        "desc": "🔒 Débloqué à 5 000h cumulées — Légendaire",
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

def is_theme_unlocked(name: str, total_global_h: float) -> bool:
    t = THEMES.get(name)
    if not t: return False
    return total_global_h >= t.get("unlock_at", 0)

apply_theme("Dark Navy")

# ── Constantes UI ─────────────────────────────────────────────────────────────
JOURS      = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
MOIS_FR    = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
              7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}
JOURS_ABRV = {"Lundi":"Lun","Mardi":"Mar","Mercredi":"Mer","Jeudi":"Jeu","Vendredi":"Ven"}
OBJECTIF_H = 40.0  # Semaine standard ADE

# ── Système XP / Niveaux ──────────────────────────────────────────────────────
XP_LEVELS = [
    (0,    1,  "Stagiaire",      "#94A3B8"),
    (50,   2,  "Junior",         "#60A5FA"),
    (150,  3,  "Intermédiaire",  "#34D399"),
    (300,  4,  "Confirmé",       "#FBBF24"),
    (500,  5,  "Senior",         "#FB923C"),
    (750,  6,  "Expert",         "#F472B6"),
    (1000, 7,  "Vétéran",        "#A78BFA"),
    (1500, 8,  "Élite",          "#E879F9"),
    (2500, 9,  "Maître",         "#38BDF8"),
    (5000, 10, "Légende ADE",    "#FFD700"),
]
# XP = 1 pt par heure travaillée + bonus trophées

def get_xp_info(total_h: float, nb_trophees: int = 0) -> dict:
    """Retourne niveau, titre, couleur, xp courant, xp requis prochain niveau."""
    xp = int(total_h) + nb_trophees * 5  # 1 XP/h + 5 XP/trophée
    cur_lvl = XP_LEVELS[0]
    next_lvl = None
    for i, lvl in enumerate(XP_LEVELS):
        if xp >= lvl[0]:
            cur_lvl = lvl
            next_lvl = XP_LEVELS[i + 1] if i + 1 < len(XP_LEVELS) else None
        else:
            break
    xp_cur  = xp - cur_lvl[0]
    xp_need = (next_lvl[0] - cur_lvl[0]) if next_lvl else 0
    pct     = int(xp_cur / xp_need * 100) if xp_need else 100
    return {
        "xp": xp, "level": cur_lvl[1], "title": cur_lvl[2], "color": cur_lvl[3],
        "xp_cur": xp_cur, "xp_need": xp_need, "pct": pct,
        "next_title": next_lvl[2] if next_lvl else None,
        "is_max": next_lvl is None,
    }


def ss_base():
    sb = BORDER2 if not IS_LIGHT else "#B0BDD0"
    return f"""
    QWidget {{ background:{BG}; color:{TXT}; font-family:'Segoe UI'; font-size:13px; }}
    QScrollBar:vertical {{ background:transparent; width:6px; border-radius:3px; margin:2px 1px; }}
    QScrollBar::handle:vertical {{ background:{sb}; border-radius:3px; min-height:30px; }}
    QScrollBar::handle:vertical:hover {{ background:{ACC}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; border:none; }}
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
    with open(save_file(monday), "r", encoding="utf-8") as f: d = json.load(f)
    total = 0.0; jour_h = {}
    for j in JOURS:
        jt = sum(calc_h(r.get("debut",""), r.get("fin","")) for r in d.get("jours",{}).get(j,[]))
        jour_h[j] = jt; total += jt
    return {"monday": monday, "label": week_label(monday), "total": total, "jours": jour_h, "_raw": d}

def load_all_weeks() -> list:
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
        if self._suggestion and event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete,
                                                Qt.Key.Key_Escape):
            # Garder seulement la partie tapée (avant la sélection) et annuler la suggestion
            typed = self.text()[:self.selectionStart()]
            if event.key() == Qt.Key.Key_Backspace and typed:
                typed = typed[:-1]  # supprimer le dernier caractère tapé
            self._suggestion = ""
            self.blockSignals(True); self.setText(typed)
            self.setCursorPosition(len(typed)); self.blockSignals(False)
            event.accept(); return
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
        if total >= 8:      color, bg, brd = GREEN, ("#0A2218" if not IS_LIGHT else "#D1FAE5"), GREEN2
        elif total >= 4:    color, bg, brd = ACC,   ACCD, ACC3
        elif total > 0:     color, bg, brd = AMBER, ("#211A08" if not IS_LIGHT else "#FEF3C7"), ("#92700A" if not IS_LIGHT else "#D97706")
        else:               color, bg, brd = TXT2,  ACCD, BORDER
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
            bar_c = GREEN if tot>=40 else (AMBER if tot>0 else MUTED)
            bg_c  = ("#091A10" if not IS_LIGHT else "#D1FAE5") if tot>=40 else \
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


# ── FlowLayout — layout wrapping automatique ──────────────────────────────────
class FlowLayout(QLayout):
    """Layout qui enroule automatiquement les widgets à la ligne."""
    def __init__(self, parent=None, h_spacing=8, v_spacing=8):
        super().__init__(parent)
        self._h = h_spacing; self._v = v_spacing
        self._items: list = []

    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i):
        if 0 <= i < len(self._items): return self._items.pop(i)
        return None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self._do_layout(QRect(0,0,width,0), dry=True)
    def setGeometry(self, rect): super().setGeometry(rect); self._do_layout(rect, dry=False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QSize()
        for it in self._items: s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left()+m.right(), m.top()+m.bottom())

    def _do_layout(self, rect, dry):
        m = self.contentsMargins()
        x = rect.x() + m.left(); y = rect.y() + m.top()
        right = rect.right() - m.right()
        row_h = 0; row_x = x
        for it in self._items:
            w = it.sizeHint().width(); h = it.sizeHint().height()
            if row_x + w > right and row_x != x:
                row_x = x; y += row_h + self._v; row_h = 0
            if not dry: it.setGeometry(QRect(QPoint(row_x, y), it.sizeHint()))
            row_x += w + self._h; row_h = max(row_h, h)
        return y + row_h - rect.y() + m.bottom()

# ── ParamDialog ────────────────────────────────────────────────────────────────
class ParamDialog(QDialog):
    saved         = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)

    def __init__(self, parent, settings, total_global_h=0.0):
        super().__init__(parent)
        self.s = dict(settings)
        self._total_h = total_global_h
        self.setWindowTitle("Paramètres — Groupe ADE")
        self.setFixedSize(580, 680)
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
        # Progress unlock
        next_unlock = self._next_unlock_threshold()
        if next_unlock:
            remaining = max(0, next_unlock - self._total_h)
            unlock_pct = min(100, int(self._total_h / next_unlock * 100)) if next_unlock > 0 else 100
            unlock_info = lbl(f"🔓 Prochain thème à {next_unlock:.0f}h — encore {fmt_h(remaining)}", 9, color=AMBER)
            unlock_info.setWordWrap(True); f3l.addWidget(unlock_info)
            upg = QProgressBar(); upg.setValue(unlock_pct); upg.setFixedHeight(5); upg.setTextVisible(False)
            upg.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:2px; border:none; }} QProgressBar::chunk {{ background:{AMBER}; border-radius:2px; }}")
            f3l.addWidget(upg)
        f3l.addWidget(lbl("Choisir un thème  (appliqué immédiatement, sans redémarrage)",9,color=TXT3))
        self.theme_combo = QComboBox()
        for name, tdata in THEMES.items():
            locked = not is_theme_unlocked(name, self._total_h)
            display = name if not locked else f"🔒 {name}  ({tdata.get('unlock_at',0):.0f}h req.)"
            self.theme_combo.addItem(display, name)
        # Select current
        cur = self.s.get("theme","Dark Navy")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == cur:
                self.theme_combo.setCurrentIndex(i); break
        self.theme_combo.currentIndexChanged.connect(self._on_combo_change)
        f3l.addWidget(self.theme_combo)
        # Container swatches — wheel bloqué pour ne pas propager au ScrollArea parent
        self._swatch_container = QWidget()
        self._swatch_container.setStyleSheet("background:transparent;")
        self._swatch_container.setFixedHeight(46)
        self._swatch_container.installEventFilter(self)
        self.swatch_row = QHBoxLayout(self._swatch_container)
        self.swatch_row.setContentsMargins(0,4,0,4); self.swatch_row.setSpacing(6)
        self._build_swatches(); f3l.addWidget(self._swatch_container)
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

    def eventFilter(self, obj, event):
        """Bloque le scroll de la molette sur le container swatches."""
        from PyQt6.QtCore import QEvent
        if obj is self._swatch_container and event.type() == QEvent.Type.Wheel:
            return True  # avalé — ne remonte pas au QScrollArea
        return super().eventFilter(obj, event)

    def _next_unlock_threshold(self):
        thresholds = sorted(set(t.get("unlock_at",0) for t in THEMES.values() if t.get("unlock_at",0) > 0))
        for th in thresholds:
            if self._total_h < th: return th
        return None

    def _section_header(self, icon, title):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w); hl.setContentsMargins(0,4,0,0); hl.setSpacing(6)
        hl.addWidget(QLabel(icon)); hl.addWidget(lbl(title, 11, bold=True))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; background:{BORDER};"); sep.setFixedHeight(1)
        hl.addWidget(sep, 1); return w

    def _build_swatches(self):
        # Vider proprement sans déclencher de relayout intermédiaire
        self._swatch_container.setUpdatesEnabled(False)
        while self.swatch_row.count():
            item = self.swatch_row.takeAt(0)
            if item and item.widget(): item.widget().deleteLater()
        cur_data = self.theme_combo.currentData() or "Dark Navy"
        for name, tdata in THEMES.items():
            locked = not is_theme_unlocked(name, self._total_h)
            btn = QPushButton(); btn.setFixedSize(38, 32)
            lines = [f"<b>{name}</b>"]
            if tdata.get("desc"): lines.append(tdata["desc"])
            if locked: lines.append(f"🔒 Débloqué à {tdata.get('unlock_at',0):.0f}h")
            btn.setToolTip("<br>".join(lines))
            btn.setCursor(Qt.CursorShape.ForbiddenCursor if locked else Qt.CursorShape.PointingHandCursor)
            acc = tdata["ACC"]; bg_t = tdata["BG2"]; card_t = tdata["CARD"]
            is_cur = (name == cur_data)
            is_light_t = tdata.get("LIGHT", False)
            if is_cur:
                border = f"2px solid {'#333' if is_light_t else 'white'}"
            else:
                border = f"1px solid {tdata['BORDER2']}"
            opacity = "opacity:0.30;" if locked else ""
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {bg_t}, stop:0.5 {card_t}, stop:1 {acc});
                    border:{border}; border-radius:8px; {opacity}
                }}
                QPushButton:hover {{ border:2px solid {acc if not locked else BORDER}; }}
            """)
            if not locked:
                btn.clicked.connect(lambda _, n=name: self._select_theme(n))
            self.swatch_row.addWidget(btn)
        self.swatch_row.addStretch()
        self._swatch_container.setUpdatesEnabled(True)

    def _on_combo_change(self, idx):
        name = self.theme_combo.itemData(idx)
        if not name: return
        if not is_theme_unlocked(name, self._total_h):
            # Revert to current
            cur = self.s.get("theme","Dark Navy")
            for i in range(self.theme_combo.count()):
                if self.theme_combo.itemData(i) == cur:
                    self.theme_combo.blockSignals(True)
                    self.theme_combo.setCurrentIndex(i)
                    self.theme_combo.blockSignals(False)
                    break
            req = THEMES[name].get("unlock_at",0)
            QMessageBox.information(self, "Thème verrouillé 🔒",
                f"Le thème « {name} » se débloque à {req:.0f}h cumulées.\n\nActuellement : {fmt_h(self._total_h)} enregistrées.")
            return
        self._preview_theme(name)

    def _select_theme(self, name):
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == name:
                self.theme_combo.setCurrentIndex(i); break

    def _preview_theme(self, name):
        apply_theme(name); self.s["theme"] = name
        self.theme_changed.emit(name); self._build_swatches()

    def _save(self):
        self.s["employer"]   = self.emp.text().strip()
        self.s["email_dest"] = self.email_dest.text().strip()
        self.s["email_cc"]   = self.email_cc.text().strip()
        self.s["theme"]      = self.theme_combo.currentData() or "Dark Navy"
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
                    subprocess.Popen(f'explorer /select,"{self.pdf_path}"',
                                     shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
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
# ║                    STATISTIQUES v3                          ║
# ╚══════════════════════════════════════════════════════════════╝
class StatsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Statistiques — Groupe ADE"); self.resize(1100, 920)
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
                        pass  # overtime calculé à la semaine
                    total += jt
                self.monthly[month_key] = self.monthly.get(month_key,0.0) + total
                if total > OBJECTIF_H: self.overtime_h += (total - OBJECTIF_H)
                self.weeks.append({"monday":monday,"label":week_label(monday),"total":total,"jours":jour_h})
            except: pass

        self.streak = 0
        check = get_monday(datetime.today())
        week_map = {w["monday"].date(): w for w in self.weeks}
        while True:
            wk = week_map.get(check.date())
            if wk and wk["total"] >= 40: self.streak += 1; check -= timedelta(weeks=1)
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

        self.total_global = sum(w["total"] for w in self.weeks)
        self.this_year_h  = sum(w["total"] for w in self.weeks if w["monday"].year == datetime.today().year)

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

    # ── Vue d'ensemble améliorée ──────────────────────────────────────────────
    def _tab_overview(self, cl):
        if not self.weeks:
            cl.addWidget(lbl("Aucune donnée disponible.",14,color=MUTED)); return
        totals   = [w["total"] for w in self.weeks]
        non_zero = [t for t in totals if t>0]
        best_wk  = max(self.weeks, key=lambda w: w["total"]) if self.weeks else None

        # ── Barre de progression globale ──────────────────────────────────────
        cl.addWidget(self._sec_title("🌍 Progression globale"))
        globe_card = card_frame()
        gl = QVBoxLayout(globe_card); gl.setContentsMargins(18,16,18,16); gl.setSpacing(12)

        # Jauge principale stylisée
        jauge_row = QHBoxLayout(); jauge_row.setSpacing(16)
        # Gros chiffre total
        total_col = QVBoxLayout()
        tot_lbl = QLabel(fmt_h(self.total_global))
        tot_lbl.setStyleSheet(f"color:{ACC}; font-size:36px; font-weight:800; background:transparent;")
        tot_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl = lbl("heures au total", 9, color=TXT3)
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_col.addWidget(tot_lbl); total_col.addWidget(sub_lbl)
        jauge_row.addLayout(total_col)

        # Barres de paliers débloquables
        paliers = [(500,"🟤","Bronze",TIER_COLORS[1]),(1000,"⚪","Argent",TIER_COLORS[2]),
                   (2000,"🟡","Or",TIER_COLORS[3]),(5000,"🟣","Légendaire","#A78BFA")]
        paliers_col = QVBoxLayout(); paliers_col.setSpacing(8)
        for target, ico, label, color in paliers:
            pct = min(100, int(self.total_global / target * 100))
            done = self.total_global >= target
            p_row = QHBoxLayout(); p_row.setSpacing(8)
            ico_lbl = QLabel(ico); ico_lbl.setFixedWidth(18)
            ico_lbl.setStyleSheet("background:transparent; font-size:12px;")
            p_row.addWidget(ico_lbl)
            p_lbl = lbl(f"{label}  {target:.0f}h", 9, bold=done, color=color if done else TXT3)
            p_lbl.setFixedWidth(100); p_row.addWidget(p_lbl)
            pbar = QProgressBar(); pbar.setValue(pct); pbar.setFixedHeight(7); pbar.setTextVisible(False)
            col_css = color if done else MUTED
            pbar.setStyleSheet(f"QProgressBar {{ background:{BG2}; border-radius:3px; border:none; }} QProgressBar::chunk {{ background:{col_css}; border-radius:3px; }}")
            p_row.addWidget(pbar, 1)
            check = QLabel("✓" if done else f"{fmt_h(self.total_global)}/{target:.0f}h")
            check.setStyleSheet(f"color:{color if done else TXT3}; font-size:9px; font-weight:700; background:transparent; min-width:60px;")
            p_row.addWidget(check)
            paliers_col.addLayout(p_row)
        jauge_row.addLayout(paliers_col, 1)
        gl.addLayout(jauge_row)
        cl.addWidget(globe_card)

        # ── KPIs principaux ───────────────────────────────────────────────────
        cl.addWidget(self._sec_title("📊 KPI Principaux"))
        cr = QHBoxLayout(); cr.setSpacing(10)
        avg_h = sum(non_zero)/len(non_zero) if non_zero else 0
        for title, val, color, sub, icon in [
            ("Total cumulé",   fmt_h(self.total_global), ACC,   f"{len(non_zero)} sem. actives","⏱"),
            ("Cette année",    fmt_h(self.this_year_h),  GREEN, f"{datetime.today().year}","📆"),
            ("Moy. / semaine", fmt_h(avg_h) if avg_h else "–", "#A78BFA", f"sur {len(non_zero)} sem.","📈"),
            ("Meilleure sem.", fmt_h(max(totals)) if totals else "–", AMBER, best_wk["label"] if best_wk and best_wk["total"]>0 else "–","🏆"),
        ]:
            cr.addWidget(self._kpi_card(title, val, color, sub, icon))
        cl.addLayout(cr)

        cr2 = QHBoxLayout(); cr2.setSpacing(10)
        streak_col = GREEN if self.streak >= 4 else AMBER if self.streak >= 1 else MUTED
        cr2.addWidget(self._kpi_card("Série en cours", f"{self.streak} sem." if self.streak else "–",
            streak_col, "sem. ≥40h de suite","🔥"))
        cr2.addWidget(self._kpi_card("Record journalier", fmt_h(self.best_day_h) if self.best_day_h else "–",
            ACC2 if not IS_LIGHT else ACC, "meilleure journée","⚡"))
        ot_col = AMBER if self.overtime_h > 0 else MUTED
        cr2.addWidget(self._kpi_card("Heures supp.", fmt_h(self.overtime_h) if self.overtime_h else "–",
            ot_col, "total >40h/sem.","🕐"))
        total_dist = self.matin_h + self.aprem_h
        if total_dist > 0:
            mat_pct = int(self.matin_h / total_dist * 100)
            cr2.addWidget(self._kpi_card("Distribution", f"{mat_pct}% matin",
                "#A78BFA", f"{100-mat_pct}% après-midi","🌅"))
        else:
            cr2.addWidget(self._kpi_card("Distribution", "–", MUTED, "données insuffisantes","🌅"))
        cl.addLayout(cr2)

        # ── Moyenne par jour ──────────────────────────────────────────────────
        cl.addWidget(self._sec_title("📅 Moyenne par jour de la semaine"))
        dc = card_frame(); dl = QVBoxLayout(dc); dl.setContentsMargins(16,14,16,14); dl.setSpacing(8)
        avgs = {j:(sum(self.jour_counts[j])/len(self.jour_counts[j]) if self.jour_counts[j] else 0) for j in JOURS}
        max_avg = max(avgs.values()) or 1
        best_jour = max(avgs, key=avgs.get) if any(avgs.values()) else ""
        for j in JOURS:
            avg = avgs[j]; is_best = (j == best_jour and avg > 0)
            r = QHBoxLayout(); r.setSpacing(10)
            # Pastille couleur jour
            dot_colors = {"Lundi":"#4F8EF7","Mardi":"#34D399","Mercredi":"#FBBF24","Jeudi":"#A78BFA","Vendredi":"#F472B6"}
            dot = QFrame(); dot.setFixedSize(10,10)
            dot.setStyleSheet(f"background:{dot_colors.get(j,ACC)}; border-radius:5px;")
            r.addWidget(dot)
            jl = lbl(j,11,bold=is_best,color=TXT if is_best else TXT2); jl.setFixedWidth(76); r.addWidget(jl)
            prog_color = GREEN if is_best else dot_colors.get(j,ACC)
            prog = QProgressBar(); prog.setValue(int(avg/max_avg*100) if avg else 0)
            prog.setFixedHeight(10); prog.setTextVisible(False)
            prog.setStyleSheet(f"QProgressBar {{ background:{BG2}; border-radius:5px; border:none; }} QProgressBar::chunk {{ background:{prog_color}; border-radius:5px; }}")
            r.addWidget(prog,1)
            cnt_lbl = lbl(f"{len(self.jour_counts[j])} j.",9,color=TXT3); cnt_lbl.setFixedWidth(36); r.addWidget(cnt_lbl)
            val_lbl = lbl(fmt_h(avg) if avg else "–", 11, bold=True, color=GREEN if is_best else (ACC if IS_LIGHT else dot_colors.get(j,ACC2)) if avg else MUTED)
            val_lbl.setFixedWidth(48); r.addWidget(val_lbl)
            if is_best: r.addWidget(lbl("⭐",10,color=GREEN))
            dl.addLayout(r)
        cl.addWidget(dc)

        # ── Distribution des semaines ─────────────────────────────────────────
        cl.addWidget(self._sec_title("📦 Distribution des semaines"))
        distr = card_frame(); drl = QHBoxLayout(distr); drl.setContentsMargins(16,14,16,14); drl.setSpacing(0)
        buckets = [("< 20h",0,RED),("20–39h",0,AMBER),("40–44h",0,ACC),("≥ 45h",0,GREEN)]
        totals_copy = totals[:]
        for t in totals_copy:
            if t < 20: buckets[0] = (buckets[0][0], buckets[0][1]+1, buckets[0][2])
            elif t < 40: buckets[1] = (buckets[1][0], buckets[1][1]+1, buckets[1][2])
            elif t < 45: buckets[2] = (buckets[2][0], buckets[2][1]+1, buckets[2][2])
            else: buckets[3] = (buckets[3][0], buckets[3][1]+1, buckets[3][2])
        bar_max = max(cnt for _,cnt,_ in buckets) or 1
        BAR_H = 70
        for label, cnt, color in buckets:
            bw = QWidget(); bw.setStyleSheet("background:transparent;")
            bwl = QVBoxLayout(bw); bwl.setContentsMargins(8,0,8,0); bwl.setSpacing(4)
            bwl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            # Barre verticale
            bar_container = QWidget(); bar_container.setFixedHeight(BAR_H)
            bar_container.setStyleSheet("background:transparent;")
            bcl = QVBoxLayout(bar_container); bcl.setContentsMargins(0,0,0,0)
            bcl.setAlignment(Qt.AlignmentFlag.AlignBottom)
            if cnt > 0:
                h = max(6, int(cnt/bar_max*BAR_H))
                bar = QFrame(); bar.setFixedHeight(h)
                bar.setStyleSheet(f"background:{color}; border-radius:4px 4px 0 0;")
                bcl.addWidget(bar)
            bwl.addWidget(bar_container)
            val_l = lbl(str(cnt),18,bold=True,color=color); val_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            name_l = lbl(label,10,color=TXT2); name_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            pct_l  = lbl(f"{cnt/len(totals_copy)*100:.0f}%" if totals_copy else "–",9,color=TXT3)
            pct_l.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            bwl.addWidget(val_l); bwl.addWidget(name_l); bwl.addWidget(pct_l)
            drl.addWidget(bw,1)
        cl.addWidget(distr)

        # ── Tableau 10 dernières semaines ─────────────────────────────────────
        cl.addWidget(self._sec_title("📋 Détail par semaine (10 dernières)"))
        tc3 = card_frame(); tl3 = QVBoxLayout(tc3); tl3.setContentsMargins(0,0,0,8); tl3.setSpacing(0)
        hd = QFrame(); hd.setStyleSheet(f"background:{CARD2}; border-radius:12px 12px 0 0;")
        hdl = QHBoxLayout(hd); hdl.setContentsMargins(14,8,12,8); hdl.setSpacing(4)
        for txt, w in [("Semaine",0),("Lun",56),("Mar",56),("Mer",56),("Jeu",56),("Ven",56),("Total",72),("Statut",80)]:
            lh = QLabel(txt); lh.setStyleSheet(f"color:{TXT3}; font-size:9px; font-weight:700; letter-spacing:1px; background:transparent;")
            if w: lh.setFixedWidth(w)
            else: lh.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hdl.addWidget(lh)
        tl3.addWidget(hd)
        for i, wk in enumerate(list(reversed(self.weeks))[:10]):
            row = QFrame()
            row.setStyleSheet(f"background:{ROW if i%2==0 else CARD}; border:none;"); row.setFixedHeight(34)
            rl2 = QHBoxLayout(row); rl2.setContentsMargins(14,0,12,0); rl2.setSpacing(4)
            rl2.addWidget(lbl(wk["label"],10))
            for j in JOURS:
                v=wk["jours"].get(j,0)
                col = GREEN if v>=8 else ACC if v>=7 else AMBER if v>0 else MUTED
                l2 = lbl(fmt_h(v) if v else "–",10,color=col); l2.setFixedWidth(56); rl2.addWidget(l2)
            tc_col = GREEN if wk["total"]>=40 else AMBER if wk["total"]>0 else MUTED
            tl_r = lbl(fmt_h(wk["total"]) if wk["total"] else "–",10,bold=True,color=tc_col); tl_r.setFixedWidth(72); rl2.addWidget(tl_r)
            if wk["total"] >= 40:   status, sc, sicon = "Sup.+", AMBER, "⚡"
            elif wk["total"] >= 40: status, sc, sicon = "Complet", GREEN, "✓"
            elif wk["total"] > 0:   status, sc, sicon = "Partiel", AMBER, "⚠"
            else:                    status, sc, sicon = "Vide", MUTED, "○"
            status_badge = QFrame(); status_badge.setFixedSize(76, 20)
            status_badge.setStyleSheet(f"background:{sc}22; border:1px solid {sc}44; border-radius:5px;")
            sbl = QHBoxLayout(status_badge); sbl.setContentsMargins(4,0,4,0); sbl.setSpacing(3)
            sbl.addWidget(lbl(sicon,8,color=sc)); sbl.addWidget(lbl(status,8,bold=True,color=sc))
            rl2.addWidget(status_badge)
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
            tot_c = GREEN if wk["total"]>=40 else AMBER if wk["total"]>0 else MUTED
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
                col = GREEN if h >= 160 else ACC if h >= 120 else AMBER
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
                GREEN if self.projection >= 40 else AMBER if self.projection > 0 else MUTED,
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
            bar_col = GREEN if t>=45 else ACC if t>=40 else AMBER if t>0 else MUTED
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
        chart_l.addWidget(ref_line); chart_l.addWidget(lbl("── Objectif 40h",9,color=GREEN))
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
            insights.append(("🔥", f"Série impressionnante ! {self.streak} semaines consécutives de 40h+. Excellent rythme.", GREEN))
        elif self.streak >= 2:
            insights.append(("🔥", f"{self.streak} semaines complètes (≥40h) de suite. Continuez !", AMBER))
        if avg >= 43:
            insights.append(("💪", f"Moyenne de {fmt_h(avg)} — Tu dépasses régulièrement les 40h. Attention à l'équilibre.", AMBER))
        elif avg >= 40:
            insights.append(("✅", f"Moyenne de {fmt_h(avg)} — Tu atteins l'objectif de 40h/sem. en moyenne. Bravo !", GREEN))
        elif avg > 0:
            insights.append(("📉", f"Moyenne de {fmt_h(avg)} — Il manque en moyenne {fmt_h(40-avg)} pour atteindre 40h.", RED))
        if self.overtime_h > 10:
            insights.append(("⏰", f"{fmt_h(self.overtime_h)} d'heures supplémentaires (>40h/sem.) accumulées au total.", AMBER))
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
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background:{BORDER}; border:none;"); line.setFixedHeight(1)
        hl.addWidget(dot); hl.addWidget(lbl(text,11,bold=True,color=TXT))
        hl.addSpacing(6); hl.addWidget(line,1); return w

    def _kpi_card(self, title, val, color, sub, icon):
        c = QFrame(); c.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-top:4px solid {color}; border-radius:14px;")
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
# ║          SYSTÈME D'ACHIEVEMENTS / BADGES v2                 ║
# ╚══════════════════════════════════════════════════════════════╝

ACHIEVEMENTS_DEF = [
    # ── Semaine ──────────────────────────────────────────────────────
    {"id":"sem_30",      "icon":"🌱", "titre":"Premier pas",           "desc":"30h dans une semaine",               "type":"semaine",      "seuil":30,   "color":"#86EFAC", "tier":1},
    {"id":"sem_35",      "icon":"💼", "titre":"Bonne semaine",           "desc":"35h dans une semaine",               "type":"semaine",      "seuil":35,   "color":"#34D399", "tier":1},
    {"id":"sem_40",      "icon":"✅", "titre":"Semaine complète",        "desc":"40h — semaine standard",               "type":"semaine",      "seuil":40,   "color":"#4F8EF7", "tier":2},
    {"id":"sem_45",      "icon":"🔥", "titre":"En feu !",               "desc":"45h dans une semaine",               "type":"semaine",      "seuil":45,   "color":"#FB923C", "tier":2},
    {"id":"sem_50",      "icon":"⚡", "titre":"Mode turbo",             "desc":"50h dans une semaine",               "type":"semaine",      "seuil":50,   "color":"#FBBF24", "tier":3},
    {"id":"sem_55",      "icon":"🌋", "titre":"Éruption totale",        "desc":"55h dans une semaine",               "type":"semaine",      "seuil":55,   "color":"#F472B6", "tier":3},
    {"id":"sem_60",      "icon":"🚀", "titre":"Workaholique",           "desc":"60h dans une semaine",               "type":"semaine",      "seuil":60,   "color":"#A78BFA", "tier":3},
    # ── Journée ──────────────────────────────────────────────────────
    {"id":"jour_8",      "icon":"🌞", "titre":"Journée pleine",         "desc":"8h en une seule journée",            "type":"jour_single",  "seuil":8,    "color":"#FCD34D", "tier":1},
    {"id":"jour_10",     "icon":"💡", "titre":"Noctambule",             "desc":"10h en une seule journée",           "type":"jour_single",  "seuil":10,   "color":"#818CF8", "tier":2},
    {"id":"jour_12",     "icon":"🌙", "titre":"Nuit blanche",           "desc":"12h en une seule journée",           "type":"jour_single",  "seuil":12,   "color":"#6366F1", "tier":3},
    # ── Série ────────────────────────────────────────────────────────
    {"id":"serie_2",     "icon":"🔗", "titre":"Dans le rythme",         "desc":"2 semaines complètes (≥40h) de suite",      "type":"serie",        "seuil":2,    "color":"#34D399", "tier":1},
    {"id":"serie_4",     "icon":"📅", "titre":"Un mois solide",         "desc":"4 semaines complètes (≥40h) de suite",      "type":"serie",        "seuil":4,    "color":"#4F8EF7", "tier":2},
    {"id":"serie_8",     "icon":"🏅", "titre":"Deux mois non-stop",     "desc":"8 semaines complètes (≥40h) de suite",      "type":"serie",        "seuil":8,    "color":"#FB923C", "tier":2},
    {"id":"serie_12",    "icon":"👑", "titre":"Trimestre parfait",      "desc":"12 semaines ≥40h de suite",               "type":"serie",        "seuil":12,   "color":"#FBBF24", "tier":3},
    {"id":"serie_26",    "icon":"🌟", "titre":"Demi-année légendaire",  "desc":"26 semaines ≥40h de suite",               "type":"serie",        "seuil":26,   "color":"#A78BFA", "tier":3},
    {"id":"serie_52",    "icon":"🎖️","titre":"L'Indestructible",        "desc":"52 semaines ≥40h de suite — 1 an !",      "type":"serie",        "seuil":52,   "color":"#F472B6", "tier":3},
    # ── Annuel ───────────────────────────────────────────────────────
    {"id":"an_100",      "icon":"💯", "titre":"Centenaire",             "desc":"100h dans l'année",                  "type":"annuel",       "seuil":100,  "color":"#34D399", "tier":1},
    {"id":"an_200",      "icon":"📈", "titre":"200h !",                 "desc":"200h dans l'année",                  "type":"annuel",       "seuil":200,  "color":"#4F8EF7", "tier":1},
    {"id":"an_500",      "icon":"🏆", "titre":"Demi-millénaire",        "desc":"500h dans l'année",                  "type":"annuel",       "seuil":500,  "color":"#FB923C", "tier":2},
    {"id":"an_750",      "icon":"🎯", "titre":"750h annuelles",         "desc":"750h dans l'année",                  "type":"annuel",       "seuil":750,  "color":"#FBBF24", "tier":2},
    {"id":"an_1000",     "icon":"💎", "titre":"Millénaire",             "desc":"1000h dans l'année",                 "type":"annuel",       "seuil":1000, "color":"#FBBF24", "tier":2},
    {"id":"an_1500",     "icon":"🌙", "titre":"Nuit et jour",           "desc":"1500h dans l'année",                 "type":"annuel",       "seuil":1500, "color":"#A78BFA", "tier":3},
    {"id":"an_2000",     "icon":"🎖️","titre":"Perfectionniste annuel",  "desc":"2000h dans l'année",                 "type":"annuel",       "seuil":2000, "color":"#F472B6", "tier":3},
    # ── Global ───────────────────────────────────────────────────────
    {"id":"gl_100",      "icon":"🌱", "titre":"Début du voyage",        "desc":"100h enregistrées au total",         "type":"global",       "seuil":100,  "color":"#86EFAC", "tier":1},
    {"id":"gl_250",      "icon":"🚶","titre":"En route",                "desc":"250h au total",                      "type":"global",       "seuil":250,  "color":"#6EE7B7", "tier":1},
    {"id":"gl_500",      "icon":"🥉", "titre":"Apprenti",               "desc":"500h enregistrées au total",         "type":"global",       "seuil":500,  "color":"#CD7F32", "tier":1},
    {"id":"gl_1000",     "icon":"🥈", "titre":"Confirmé",               "desc":"1000h au total",                     "type":"global",       "seuil":1000, "color":"#C0C0C0", "tier":2},
    {"id":"gl_1500",     "icon":"🏛️","titre":"Expert ADE",              "desc":"1500h au total",                     "type":"global",       "seuil":1500, "color":"#D4A820", "tier":2},
    {"id":"gl_2000",     "icon":"🥇", "titre":"Maître",                 "desc":"2000h au total",                     "type":"global",       "seuil":2000, "color":"#FFD700", "tier":2},
    {"id":"gl_3000",     "icon":"💎", "titre":"Grand maître",           "desc":"3000h au total",                     "type":"global",       "seuil":3000, "color":"#22D3EE", "tier":3},
    {"id":"gl_5000",     "icon":"🏛️","titre":"Légende ADE",             "desc":"5000h au total",                     "type":"global",       "seuil":5000, "color":"#A78BFA", "tier":3},
    {"id":"gl_10000",    "icon":"⚡", "titre":"Transcendance",          "desc":"10 000h au total — mythique",         "type":"global",       "seuil":10000,"color":"#F472B6", "tier":3},
    # ── Spéciaux ─────────────────────────────────────────────────────
    {"id":"sp_1sem",     "icon":"🎉", "titre":"La première fois",       "desc":"1ère semaine enregistrée",           "type":"nb_sem",       "seuil":1,    "color":"#86EFAC", "tier":1},
    {"id":"sp_5sem",     "icon":"🗓️","titre":"Fidèle",                  "desc":"5 semaines enregistrées",            "type":"nb_sem",       "seuil":5,    "color":"#34D399", "tier":1},
    {"id":"sp_10sem",    "icon":"📖", "titre":"Assidu",                  "desc":"10 semaines enregistrées",           "type":"nb_sem",       "seuil":10,   "color":"#38BDF8", "tier":1},
    {"id":"sp_20sem",    "icon":"📋", "titre":"Régulier",               "desc":"20 semaines enregistrées",           "type":"nb_sem",       "seuil":20,   "color":"#4F8EF7", "tier":2},
    {"id":"sp_50sem",    "icon":"📚", "titre":"Vétéran",                "desc":"50 semaines enregistrées",           "type":"nb_sem",       "seuil":50,   "color":"#FBBF24", "tier":3},
    {"id":"sp_100sem",   "icon":"🏆", "titre":"Centurion",              "desc":"100 semaines enregistrées",          "type":"nb_sem",       "seuil":100,  "color":"#F472B6", "tier":3},
    {"id":"sp_lundi",    "icon":"🌅", "titre":"Lève-tôt du lundi",      "desc":"Journée de lundi ≥ 9h",              "type":"jour_max",     "seuil":9,    "color":"#22D3EE", "tier":1, "jour":"Lundi"},
    {"id":"sp_vendredi", "icon":"🎉", "titre":"TGIF marathon",          "desc":"Journée de vendredi ≥ 9h",           "type":"jour_max",     "seuil":9,    "color":"#F472B6", "tier":1, "jour":"Vendredi"},
    {"id":"sp_mercredi", "icon":"🐪", "titre":"Hump Day Hero",          "desc":"Journée de mercredi ≥ 10h",          "type":"jour_max",     "seuil":10,   "color":"#FBBF24", "tier":2, "jour":"Mercredi"},
    {"id":"sp_parfait",  "icon":"⭐", "titre":"Semaine parfaite",       "desc":"5h+ chaque jour lun-ven",      "type":"sem_parfaite", "seuil":5,    "color":"#FBBF24", "tier":3},
    {"id":"sp_super",    "icon":"🦸", "titre":"Semaine de super-héros", "desc":"7h+ chaque jour lun-ven",      "type":"sem_parfaite", "seuil":7,    "color":"#F472B6", "tier":3},
    {"id":"sp_3proj",    "icon":"🎭", "titre":"Multi-casquettes",       "desc":"3 projets différents en 1 semaine",  "type":"multi_proj",   "seuil":3,    "color":"#818CF8", "tier":2},
    {"id":"sp_5proj",    "icon":"🌐", "titre":"Chef d'orchestre",       "desc":"5 projets différents en 1 semaine",  "type":"multi_proj",   "seuil":5,    "color":"#A78BFA", "tier":3},
    {"id":"sp_早起",     "icon":"🐓", "titre":"Coq du matin",           "desc":"Début de journée avant 7h00",        "type":"early_start",  "seuil":7,    "color":"#FCD34D", "tier":2},
    {"id":"sp_nuit",     "icon":"🦉", "titre":"Hibou de nuit",          "desc":"Fin de journée après 20h00",         "type":"late_end",     "seuil":20,   "color":"#818CF8", "tier":2},
    {"id":"sp_5jours",   "icon":"📆", "titre":"5/5 Présent",            "desc":"Au moins 1h enregistrée les 5 jours","type":"sem_5jours",   "seuil":1,    "color":"#38BDF8", "tier":1},
    {"id":"sp_theme",    "icon":"🎨", "titre":"Décorateur",             "desc":"A changé de thème au moins 1 fois",  "type":"theme_change", "seuil":1,    "color":"#F472B6", "tier":1},
]

_ACH_INDEX: dict[str, dict] = {a["id"]: a for a in ACHIEVEMENTS_DEF}
TIER_LABELS = {1: "Bronze", 2: "Argent", 3: "Or"}
TIER_COLORS = {1: "#CD7F32", 2: "#C0C0C0", 3: "#FFD700"}


class AchievementStore:
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


def compute_achievements(weeks: list, settings: dict | None = None) -> list[str]:
    if not weeks: return []
    newly = []
    totals      = [w["total"] for w in weeks]
    this_year   = datetime.today().year
    annual      = sum(w["total"] for w in weeks if w["monday"].year == this_year)
    total_global= sum(totals)
    nb_sem      = sum(1 for t in totals if t > 0)

    streak = 0
    check = get_monday(datetime.today())
    week_map = {w["monday"].date(): w for w in weeks}
    while True:
        wk = week_map.get(check.date())
        if wk and wk["total"] >= 40: streak += 1; check -= timedelta(weeks=1)
        else: break

    # Calcul max journée et multi-projets
    all_jour_hours = []
    has_early_start = False
    has_late_end = False
    max_proj_in_week = 0
    for monday in sorted(saved_weeks()):
        try:
            with open(save_file(monday),"r",encoding="utf-8") as f: d = json.load(f)
            week_proj = set()
            for j in JOURS:
                for r in d.get("jours",{}).get(j,[]):
                    h = calc_h(r.get("debut",""), r.get("fin",""))
                    if h > 0: all_jour_hours.append(h)
                    p = r.get("projet","").strip()
                    if p: week_proj.add(p)
                    # Early/late
                    s = parse_heure(r.get("debut",""))
                    e = parse_heure(r.get("fin",""))
                    if s and s.hour < 7: has_early_start = True
                    if e and e.hour >= 20: has_late_end = True
            max_proj_in_week = max(max_proj_in_week, len(week_proj))
        except: pass

    for ach in ACHIEVEMENTS_DEF:
        aid   = ach["id"]
        t     = ach["type"]
        seuil = ach["seuil"]
        if AchievementStore.is_unlocked(aid): continue
        unlocked = False
        if   t == "semaine":      unlocked = any(w["total"] >= seuil for w in weeks)
        elif t == "serie":        unlocked = streak >= seuil
        elif t == "annuel":       unlocked = annual >= seuil
        elif t == "global":       unlocked = total_global >= seuil
        elif t == "nb_sem":       unlocked = nb_sem >= seuil
        elif t == "jour_max":
            jour = ach.get("jour","")
            unlocked = any(w["jours"].get(jour,0) >= seuil for w in weeks)
        elif t == "jour_single":  unlocked = any(h >= seuil for h in all_jour_hours)
        elif t == "sem_parfaite": unlocked = any(all(w["jours"].get(j,0) >= seuil for j in JOURS) for w in weeks)
        elif t == "multi_proj":   unlocked = max_proj_in_week >= seuil
        elif t == "early_start":  unlocked = has_early_start
        elif t == "late_end":     unlocked = has_late_end
        elif t == "sem_5jours":
            unlocked = any(all(w["jours"].get(j,0) >= seuil for j in JOURS) for w in weeks)
        elif t == "theme_change":
            # Déclenché manuellement lors d'un changement de thème
            unlocked = (settings or {}).get("_theme_ever_changed", False)
        if unlocked and AchievementStore.unlock(aid):
            newly.append(aid)
    return newly


# ── Toast d'achievement animé ─────────────────────────────────────────────────
class AchievementToast(QFrame):
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
    def __init__(self, parent, weeks: list, total_global_h: float = 0.0):
        super().__init__(parent)
        self.setWindowTitle("Trophées — Groupe ADE")
        self.resize(980, 780); self.setMinimumSize(700, 500)
        self.setStyleSheet(ss_base() + f"QDialog {{ background:{BG}; }}")
        self._weeks = weeks
        self._data  = AchievementStore.data()
        self._total_h = total_global_h
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

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
        pf = QFrame(); pf.setFixedWidth(160)
        pf.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:10px;")
        pfl = QVBoxLayout(pf); pfl.setContentsMargins(10,6,10,6); pfl.setSpacing(3)
        pct = int(nb_unlocked/nb_total*100) if nb_total else 0
        pfl.addWidget(lbl(f"{pct}% complété",10,bold=True,color=ACC))
        pg = QProgressBar(); pg.setValue(pct); pg.setFixedHeight(6); pg.setTextVisible(False)
        pg.setStyleSheet(f"QProgressBar {{ background:{BG}; border-radius:3px; border:none; }} QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC}); border-radius:3px; }}")
        pfl.addWidget(pg); hl.addWidget(pf); lay.addWidget(hdr)

        # Thèmes débloquables aperçu
        themes_row = QWidget()
        themes_row.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        trl2 = QHBoxLayout(themes_row); trl2.setContentsMargins(22,8,22,8); trl2.setSpacing(10)
        trl2.addWidget(lbl("🎨 Thèmes débloquables :", 9, bold=True, color=TXT2))
        for name, tdata in THEMES.items():
            req = tdata.get("unlock_at", 0)
            if req == 0: continue
            done = self._total_h >= req
            color = tdata["ACC"]
            badge = QFrame(); badge.setFixedHeight(22)
            badge.setStyleSheet(f"background:{color}22; border:1px solid {color if done else BORDER}; border-radius:6px;")
            bl2 = QHBoxLayout(badge); bl2.setContentsMargins(6,0,6,0); bl2.setSpacing(4)
            bl2.addWidget(lbl("✓" if done else "🔒", 8, color=color if done else TXT3))
            bl2.addWidget(lbl(f"{name}  {req:.0f}h", 8, bold=done, color=color if done else TXT3))
            trl2.addWidget(badge)
        trl2.addStretch()
        lay.addWidget(themes_row)

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
        reset_btn = QPushButton("↺ Réinitialiser"); reset_btn.setFixedHeight(26)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{TXT3}; border:1px solid {BORDER}; border-radius:6px; font-size:9px; padding:0 8px; }} QPushButton:hover {{ color:{RED}; border-color:{RED}; }}")
        reset_btn.clicked.connect(self._reset_achievements); trl.addWidget(reset_btn)
        trl.addStretch(); lay.addWidget(tier_row)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; }} QWidget {{ background:{BG}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(); cl = QVBoxLayout(content)
        cl.setContentsMargins(16,14,16,14); cl.setSpacing(16)

        categories = [
            ("🗓️ Semaine",    [a for a in ACHIEVEMENTS_DEF if a["type"]=="semaine"]),
            ("☀️ Journée",    [a for a in ACHIEVEMENTS_DEF if a["type"]=="jour_single"]),
            ("🔗 Séries",     [a for a in ACHIEVEMENTS_DEF if a["type"]=="serie"]),
            ("📅 Annuel",     [a for a in ACHIEVEMENTS_DEF if a["type"]=="annuel"]),
            ("🌍 Global",     [a for a in ACHIEVEMENTS_DEF if a["type"]=="global"]),
            ("⭐ Spéciaux",   [a for a in ACHIEVEMENTS_DEF if a["type"] in (
                "nb_sem","jour_max","sem_parfaite","multi_proj",
                "early_start","late_end","sem_5jours","theme_change")]),
        ]
        for cat_title, achs in categories:
            if not achs: continue
            cl.addWidget(self._section_title(cat_title))
            grid = QWidget(); grid.setStyleSheet("background:transparent;")
            fl = FlowLayout(grid, h_spacing=10, v_spacing=10)
            fl.setContentsMargins(0,0,0,0)
            for ach in achs: fl.addWidget(self._ach_card(ach))
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
        tier     = ach.get("tier", 1)
        tier_c   = TIER_COLORS[tier] if unlocked else MUTED
        date_str = self._data.get(aid, "")

        card = QFrame(); card.setFixedSize(152, 156)
        if unlocked:
            card.setStyleSheet(f"""QFrame {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color}1A, stop:1 {color}06);
                border:2px solid {color}; border-radius:16px;
            }}""")
        else:
            card.setStyleSheet(f"""QFrame {{
                background:{CARD}; border:1px solid {BORDER};
                border-radius:16px;
            }}""")

        cl = QVBoxLayout(card); cl.setContentsMargins(10,10,10,10); cl.setSpacing(5)
        cl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Tier badge (coin haut-droit)
        tier_badge = QLabel(("●" if tier==1 else "◆" if tier==2 else "★"))
        tier_badge.setStyleSheet(f"color:{tier_c}; font-size:8px; background:transparent;")
        tier_badge.setAlignment(Qt.AlignmentFlag.AlignRight)
        cl.addWidget(tier_badge)

        # Icône circulaire
        ico_frame = QFrame(); ico_frame.setFixedSize(46, 46)
        ico_frame.setStyleSheet(f"""QFrame {{
            background:{color}20;
            border-radius:23px;
            border:{"2px solid "+color if unlocked else "1px solid "+BORDER};
        }}""")
        ifl = QHBoxLayout(ico_frame); ifl.setContentsMargins(0,0,0,0)
        ico_lbl = QLabel(ach["icon"] if unlocked else "🔒")
        ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_lbl.setStyleSheet(f"font-size:{'20' if unlocked else '15'}px; background:transparent; border:none;")
        ifl.addWidget(ico_lbl)
        cl.addWidget(ico_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # Titre
        titre_lbl = QLabel(ach["titre"]); titre_lbl.setWordWrap(True)
        titre_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        titre_lbl.setStyleSheet(
            f"color:{TXT if unlocked else TXT3}; font-size:9px; "
            f"font-weight:{'800' if unlocked else '500'}; background:transparent;")
        cl.addWidget(titre_lbl)

        # Description
        desc_lbl = QLabel(ach["desc"]); desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        desc_lbl.setStyleSheet(f"color:{TXT3}; font-size:7px; background:transparent;")
        cl.addWidget(desc_lbl)

        # Date débloquée ou label tier
        if unlocked:
            if date_str and len(date_str) >= 10:
                try:
                    from datetime import date as _date
                    d = _date.fromisoformat(date_str[:10])
                    date_fmt = f"{d.day} {MOIS_FR[d.month]} {d.year}"
                except Exception:
                    date_fmt = date_str[:10]
                b_text = f"✓ {date_fmt}"
                b_col  = color
            else:
                b_text = f"● {TIER_LABELS[tier]}"
                b_col  = tier_c
            b_lbl = QLabel(b_text); b_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            b_lbl.setStyleSheet(
                f"color:{b_col}; font-size:7px; font-weight:700; background:transparent;")
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
        self._total_global_h = 0.0
        self._nb_trophees    = 0

        AutoCompleteRegistry.load_all()
        self._build()
        self._toast_queue = ToastQueue(self)
        self._load_week(self.monday)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start(30_000)
        QTimer.singleShot(2000, self._start_update_check)
        QTimer.singleShot(500,  self._compute_global_total)
        QTimer.singleShot(1200, self._update_xp_widget)  # rafraîchi après build complet

    def closeEvent(self, event): self._save(silent=True); event.accept()

    def _compute_global_total(self):
        try:
            weeks = load_all_weeks()
            self._total_global_h = sum(w["total"] for w in weeks)
            AchievementStore.invalidate()          # relit le fichier à jour
            self._nb_trophees = len(AchievementStore.data())
        except Exception:
            self._total_global_h = 0.0
            self._nb_trophees    = 0
        self._update_xp_widget()

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

        res = QWidget(); res.setStyleSheet("background:transparent;")
        rl2 = QVBoxLayout(res); rl2.setContentsMargins(12,10,12,10); rl2.setSpacing(6)
        rl2.addWidget(section_lbl("RÉSUMÉ"))

        # ── Total semaine ──────────────────────────────────────────────────────
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
        self._streak_lbl = lbl("",9,color=TXT3)
        self._streak_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl2.addWidget(self._streak_lbl)

        # ── XP / Niveau ────────────────────────────────────────────────────────
        xp_frame = QFrame(); xp_frame.setObjectName("xp_frame")
        xp_frame.setStyleSheet(f"""
            QFrame#xp_frame {{
                background:{BG3}; border:1px solid {BORDER2};
                border-radius:12px;
            }}
        """)
        xfl = QVBoxLayout(xp_frame); xfl.setContentsMargins(12,9,12,9); xfl.setSpacing(4)

        # Ligne titre : badge niveau + titre
        xp_top = QHBoxLayout(); xp_top.setSpacing(6)
        self._xp_lvl_badge = QLabel("Nv.1")
        self._xp_lvl_badge.setFixedSize(34, 20)
        self._xp_lvl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._xp_lvl_badge.setStyleSheet(f"""
            background:{ACC3}; color:white; border-radius:6px;
            font-size:9px; font-weight:800;
        """)
        self._xp_title_lbl = lbl("Stagiaire", 10, bold=True, color=ACC)
        xp_top.addWidget(self._xp_lvl_badge)
        xp_top.addWidget(self._xp_title_lbl, 1)
        self._xp_pts_lbl = lbl("0 XP", 8, color=TXT3)
        xp_top.addWidget(self._xp_pts_lbl)
        xfl.addLayout(xp_top)

        # Barre XP
        self._xp_bar = QProgressBar(); self._xp_bar.setFixedHeight(6)
        self._xp_bar.setTextVisible(False); self._xp_bar.setValue(0)
        self._xp_bar.setStyleSheet(f"""
            QProgressBar {{ background:{BG}; border-radius:3px; border:none; }}
            QProgressBar::chunk {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACC3},stop:1 {ACC});
                border-radius:3px;
            }}
        """)
        xfl.addWidget(self._xp_bar)

        # Ligne prochain niveau
        self._xp_next_lbl = lbl("", 8, color=TXT3)
        self._xp_next_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        xfl.addWidget(self._xp_next_lbl)

        rl2.addWidget(xp_frame)
        lay.addWidget(res); lay.addWidget(h_sep())

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

        tr = QWidget(); tr.setStyleSheet("background:transparent;")
        tl2 = QVBoxLayout(tr); tl2.setContentsMargins(10,8,10,6); tl2.setSpacing(3)
        tl2.addWidget(section_lbl("TRANSFERT"))
        for text, cmd in [("📤  Exporter .zip",self._export_zip),("📥  Importer .zip",self._import_zip),
                          ("📁  Ouvrir le dossier",self._open_folder)]:
            b = sidebar_btn(text); b.clicked.connect(cmd); tl2.addWidget(b)
        lay.addWidget(tr); lay.addStretch()

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

    def _update_xp_widget(self):
        """Met à jour le widget XP/niveau dans la sidebar."""
        if not hasattr(self, "_xp_bar") or self._xp_bar is None: return
        try: self._xp_bar.value()  # teste que le widget est vivant
        except RuntimeError: return
        info = get_xp_info(self._total_global_h, self._nb_trophees)
        c = info["color"]
        # Badge niveau
        self._xp_lvl_badge.setText(f"Nv.{info['level']}")
        self._xp_lvl_badge.setStyleSheet(f"""
            background:{c}; color:{'#0A0A0A' if info['level']==10 else 'white'};
            border-radius:6px; font-size:9px; font-weight:800;
        """)
        # Titre
        self._xp_title_lbl.setText(info["title"])
        self._xp_title_lbl.setStyleSheet(f"color:{c}; font-size:10px; font-weight:700; background:transparent;")
        # Points XP
        self._xp_pts_lbl.setText(f"{info['xp']} XP")
        # Barre progression
        self._xp_bar.setValue(info["pct"])
        self._xp_bar.setStyleSheet(f"""
            QProgressBar {{ background:{BG}; border-radius:3px; border:none; }}
            QProgressBar::chunk {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {c}AA,stop:1 {c});
                border-radius:3px;
            }}
        """)
        # Prochain niveau
        if info["is_max"]:
            self._xp_next_lbl.setText("★ Niveau max !")
            self._xp_next_lbl.setStyleSheet(f"color:{c}; font-size:8px; font-weight:700; background:transparent;")
        else:
            remaining = info["xp_need"] - info["xp_cur"]
            self._xp_next_lbl.setText(f"{remaining} XP → {info['next_title']}")
            self._xp_next_lbl.setStyleSheet(f"color:{TXT3}; font-size:8px; background:transparent;")

    def _nav_btn(self, text):
        b = QPushButton(text); b.setFixedSize(28,28); b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{ background:{CARD}; color:{TXT2}; border:1px solid {BORDER}; border-radius:7px;
                           font-size:10px; font-weight:600; }}
            QPushButton:hover {{ background:{ACC3}; color:white; border-color:{ACC3}; }}
            QPushButton:pressed {{ background:{ACCD}; }}
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
        txt   = fmt_h(total) if total else "0h"
        pct   = min(int(total / OBJECTIF_H * 100), 100)
        if   total >= OBJECTIF_H: col, badge_bg, badge_bd = GREEN,  ("#0A2218" if not IS_LIGHT else "#D1FAE5"), GREEN2
        elif total >= 20:         col, badge_bg, badge_bd = ACC,    ACCD, ACC3
        elif total > 0:           col, badge_bg, badge_bd = AMBER,  ("#211A08" if not IS_LIGHT else "#FEF3C7"), "#92700A"
        else:                     col, badge_bg, badge_bd = TXT3,   BG2, BORDER
        self.week_total_lbl.setText(f"Total : {txt}")
        self.week_total_lbl.setStyleSheet(
            f"color:{col}; font-size:14px; font-weight:700;"
            f"background:{badge_bg}; border:1px solid {badge_bd}; border-radius:9px; padding:3px 14px;")
        self.total_big.setText(txt)
        self.total_big.setStyleSheet(f"color:{col}; font-family:'Segoe UI'; font-size:28px; font-weight:800; background:transparent;")
        self.prog.setValue(pct)

    def _update_streak_display(self):
        try:
            weeks = load_all_weeks()
            streak = 0; check = get_monday(datetime.today())
            week_map = {w["monday"].date(): w for w in weeks}
            while True:
                wk = week_map.get(check.date())
                if wk and wk["total"] >= 40: streak += 1; check -= timedelta(weeks=1)
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
        self._total_global_h = sum(w["total"] for w in weeks)
        AchievementStore.invalidate()
        AchievementsDialog(self, weeks, self._total_global_h).exec()

    def _check_achievements(self):
        if self._toast_queue is None: return
        try:
            weeks = load_all_weeks()
            self._total_global_h = sum(w["total"] for w in weeks)
            for aid in compute_achievements(weeks, self.settings):
                self._toast_queue.push(aid)
            self._update_streak_display()
        except: pass

    def _parametres(self):
        self._compute_global_total()
        dlg = ParamDialog(self, self.settings, self._total_global_h)
        dlg.theme_changed.connect(self._apply_theme_live)
        dlg.saved.connect(self._apply_settings)
        old_theme = self.settings.get("theme","Dark Navy")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self._apply_theme_live(old_theme)
        else:
            # Marquer qu'un thème a été changé pour le trophée "Décorateur"
            if self.settings.get("theme","Dark Navy") != old_theme:
                self.settings["_theme_ever_changed"] = True
                write_settings(self.settings)
                QTimer.singleShot(300, self._check_achievements)

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
        QTimer.singleShot(100, self._compute_global_total)  # restaure XP après rebuild

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

            # ── Palette claire ──────────────────────────────────────────
            def bg():
                c.setFillColorRGB(1.0, 1.0, 1.0)
                c.rect(0, 0, PW, PH, fill=1, stroke=0)

            bg()

            # Bandeau entête bleu ADE sobre
            c.setFillColorRGB(0.129, 0.290, 0.729)
            c.rect(0, PH-68, PW, 68, fill=1, stroke=0)
            c.setFillColorRGB(0.051, 0.184, 0.604)
            c.rect(0, PH-68, 5, 68, fill=1, stroke=0)

            # Titre blanc
            c.setFillColorRGB(1.0, 1.0, 1.0)
            c.setFont("Helvetica-Bold", 20)
            c.drawString(22, PH-36, "Groupe ADE")
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.78, 0.87, 1.0)
            c.drawString(22, PH-53, f"Feuille de Temps  ·  {APP_VERSION}")

            c.setFillColorRGB(1.0, 1.0, 1.0)
            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(PW-22, PH-34, week_label(self.monday))
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.78, 0.87, 1.0)
            c.drawRightString(PW-22, PH-50, f"Employé : {self.emp_entry.text()}")

            # Sous-bandeau gris très clair
            c.setFillColorRGB(0.945, 0.949, 0.957)
            c.rect(0, PH-84, PW, 16, fill=1, stroke=0)
            c.setFillColorRGB(0.42, 0.44, 0.50)
            c.setFont("Helvetica", 7.5)
            c.drawString(22, PH-78, f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
            c.drawRightString(PW-22, PH-78, f"{DEV_CREDIT}  ·  {COPYRIGHT}")

            c.setStrokeColorRGB(0.82, 0.85, 0.91)
            c.setLineWidth(0.5)
            c.line(20, PH-86, PW-20, PH-86)

            y = PH-104; week_tot = 0.0

            for jour in JOURS:
                card = self.day_cards[jour]
                rows = [r for r in card.rows if r.start.text() or r.end.text()]

                if y < 130:
                    # Pied de page
                    c.setFillColorRGB(0.945, 0.949, 0.957)
                    c.rect(0, 0, PW, 22, fill=1, stroke=0)
                    c.setFillColorRGB(0.50, 0.52, 0.58)
                    c.setFont("Helvetica", 7.5)
                    c.drawString(22, 7, f"Groupe ADE  ·  {APP_VERSION}  ·  {DEV_CREDIT}")
                    c.drawRightString(PW-22, 7, COPYRIGHT)
                    c.showPage(); bg()
                    # En-tête allégé pages suivantes
                    c.setFillColorRGB(0.129, 0.290, 0.729)
                    c.rect(0, PH-32, PW, 32, fill=1, stroke=0)
                    c.setFillColorRGB(1.0, 1.0, 1.0)
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(22, PH-19, "Groupe ADE  —  Feuille de Temps (suite)")
                    c.setFont("Helvetica", 9)
                    c.setFillColorRGB(0.78, 0.87, 1.0)
                    c.drawRightString(PW-22, PH-19, week_label(self.monday))
                    c.setStrokeColorRGB(0.82, 0.85, 0.91); c.setLineWidth(0.5)
                    c.line(20, PH-34, PW-20, PH-34)
                    y = PH-52

                # En-tête jour : fond gris doux + pastille bleue
                c.setFillColorRGB(0.933, 0.941, 0.961)
                c.rect(20, y-22, PW-40, 24, fill=1, stroke=0)
                c.setFillColorRGB(0.129, 0.290, 0.729)
                c.rect(20, y-22, 4, 24, fill=1, stroke=0)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(32, y-12, jour.upper())
                day_tot = card.get_total(); week_tot += day_tot
                c.drawRightString(PW-24, y-12, f"Total : {fmt_h(day_tot)}" if day_tot else "Total : –")
                c.setStrokeColorRGB(0.75, 0.80, 0.90); c.setLineWidth(0.4)
                c.line(20, y-22, PW-20, y-22)
                y -= 28

                if not rows:
                    c.setFillColorRGB(0.60, 0.62, 0.68)
                    c.setFont("Helvetica-Oblique", 9)
                    c.drawString(36, y-8, "Aucune entrée")
                    y -= 20
                    c.setStrokeColorRGB(0.88, 0.90, 0.94); c.setLineWidth(0.3)
                    c.line(20, y-2, PW-20, y-2); y -= 8
                    continue

                # En-tête colonnes
                c.setFillColorRGB(0.965, 0.969, 0.976)
                c.rect(20, y-16, PW-40, 18, fill=1, stroke=0)
                c.setFillColorRGB(0.40, 0.43, 0.52)
                c.setFont("Helvetica-Bold", 7.5)
                for txt, x in [("DATE",28),("DÉBUT",118),("FIN",162),("TÂCHE",210),("PROJET",306),("CLIENT / DESC",396),("DURÉE",PW-52)]:
                    c.drawString(x, y-9, txt)
                c.setStrokeColorRGB(0.80, 0.84, 0.91); c.setLineWidth(0.3)
                c.line(20, y-16, PW-20, y-16)
                y -= 18

                for i, r in enumerate(rows):
                    if y < 40:
                        c.setFillColorRGB(0.945, 0.949, 0.957)
                        c.rect(0, 0, PW, 22, fill=1, stroke=0)
                        c.setFillColorRGB(0.50, 0.52, 0.58)
                        c.setFont("Helvetica", 7.5)
                        c.drawString(22, 7, f"Groupe ADE  ·  {APP_VERSION}  ·  {DEV_CREDIT}")
                        c.drawRightString(PW-22, 7, COPYRIGHT)
                        c.showPage(); bg()
                        c.setFillColorRGB(0.129, 0.290, 0.729)
                        c.rect(0, PH-32, PW, 32, fill=1, stroke=0)
                        c.setFillColorRGB(1.0, 1.0, 1.0)
                        c.setFont("Helvetica-Bold", 11)
                        c.drawString(22, PH-19, "Groupe ADE  —  Feuille de Temps (suite)")
                        c.setFont("Helvetica", 9)
                        c.setFillColorRGB(0.78, 0.87, 1.0)
                        c.drawRightString(PW-22, PH-19, week_label(self.monday))
                        c.setStrokeColorRGB(0.82, 0.85, 0.91); c.setLineWidth(0.5)
                        c.line(20, PH-34, PW-20, PH-34)
                        y = PH-52

                    # Zébrage blanc / gris très clair
                    if i % 2 == 0:
                        c.setFillColorRGB(1.0, 1.0, 1.0)
                    else:
                        c.setFillColorRGB(0.973, 0.976, 0.984)
                    c.rect(20, y-14, PW-40, 16, fill=1, stroke=0)

                    # Texte quasi-noir
                    c.setFillColorRGB(0.13, 0.15, 0.20)
                    c.setFont("Helvetica", 8.5)
                    c.drawString(28,   y-7, r.date_lbl.text())
                    c.drawString(118,  y-7, r.start.text())
                    c.drawString(162,  y-7, r.end.text())
                    c.drawString(210,  y-7, r.tache.text()[:18])
                    c.drawString(306,  y-7, r.projet.text()[:16])
                    c.drawString(396,  y-7, r.desc.text()[:22])

                    # Durée en bleu
                    c.setFillColorRGB(0.129, 0.290, 0.729)
                    c.setFont("Helvetica-Bold", 8.5)
                    c.drawRightString(PW-24, y-7, fmt_h(calc_h(r.start.text(), r.end.text())))

                    c.setStrokeColorRGB(0.88, 0.90, 0.94); c.setLineWidth(0.2)
                    c.line(20, y-14, PW-20, y-14)
                    y -= 16

                # Séparation entre jours
                c.setStrokeColorRGB(0.70, 0.75, 0.85); c.setLineWidth(0.5)
                c.line(20, y-4, PW-20, y-4)
                y -= 14

            # Bandeau total semaine
            y -= 4
            c.setFillColorRGB(0.129, 0.290, 0.729)
            c.rect(20, y-28, PW-40, 32, fill=1, stroke=0)
            c.setFillColorRGB(1.0, 1.0, 1.0)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(28, y-16, "TOTAL DE LA SEMAINE")
            c.drawRightString(PW-24, y-16, fmt_h(week_tot))

            # Pied de page dernière page
            c.setFillColorRGB(0.945, 0.949, 0.957)
            c.rect(0, 0, PW, 22, fill=1, stroke=0)
            c.setFillColorRGB(0.50, 0.52, 0.58)
            c.setFont("Helvetica", 7.5)
            c.drawString(22, 7, f"Groupe ADE  ·  {APP_VERSION}  ·  {DEV_CREDIT}")
            c.drawRightString(PW-22, 7, COPYRIGHT)
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