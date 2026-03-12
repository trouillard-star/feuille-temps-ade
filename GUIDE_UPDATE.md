# Guide — Auto-Update Groupe ADE
## Développé par Thierry Rouillard

---

## 1. SETUP INITIAL (une seule fois)

### 1.1 Créer le repo GitHub
1. Va sur https://github.com/new
2. Nom du repo : **feuille-temps-ade** (ou ce que tu veux)
3. Visibilité : **Public** (nécessaire pour que le .exe puisse lire version.json sans token)
4. Crée le repo

### 1.2 Configurer feuille_temps.py
Ouvre `feuille_temps.py` et modifie ces 2 lignes en haut :
```python
GITHUB_USER = "ton-vrai-username-github"   # ex: "thierry-rouillard"
GITHUB_REPO = "feuille-temps-ade"          # nom exact du repo créé
```

### 1.3 Mettre version.json sur GitHub
Upload `version.json` à la racine du repo (branche `main`).
C'est ce fichier que l'app va lire pour savoir s'il y a une mise à jour.

### 1.4 Installer les dépendances
```
pip install pyqt6 reportlab pyinstaller
```

### 1.5 Premier build
Double-clique sur `build_exe.bat`
→ Produit `dist\FeuilleTemps_ADE.exe`

### 1.6 Créer le premier GitHub Release
1. Sur ton repo GitHub → **Releases** → **Create a new release**
2. Tag : `v3.3`
3. Titre : `Groupe ADE v3.3 — Initial`
4. Upload `dist\FeuilleTemps_ADE.exe` comme asset
5. Publie

### 1.7 Distribuer le .exe
Donne `FeuilleTemps_ADE.exe` à tes collègues.
Ils n'ont rien d'autre à installer.

---

## 2. PUBLIER UNE MISE À JOUR (workflow normal)

Chaque fois que tu veux pousser un update :

### Étape 1 — Modifier le code
Fais tes changements dans `feuille_temps.py`.
Change `APP_VERSION` :
```python
APP_VERSION = "v3.4"   # incrémente à chaque release
```

### Étape 2 — Mettre à jour version.json
```json
{
  "version": "v3.4",
  "notes": "Décris ici ce qui a changé (max ~100 chars).",
  "date": "2025-06-15",
  "author": "Thierry Rouillard"
}
```

### Étape 3 — Rebuilder le .exe
```
build_exe.bat
```

### Étape 4 — Push version.json sur GitHub
```bash
git add version.json feuille_temps.py
git commit -m "Release v3.4 — description du changement"
git push
```
Ou via GitHub Desktop / interface web.

### Étape 5 — Créer le GitHub Release
1. GitHub → ton repo → **Releases** → **Draft a new release**
2. Tag : `v3.4`  (exactement le même que dans APP_VERSION et version.json)
3. Upload `dist\FeuilleTemps_ADE.exe`
4. **Publish release**

**C'est tout.** La prochaine fois que tes collègues ouvrent l'app,
le bouton "🟢 Mise à jour v3.4 disponible" apparaît dans la sidebar.
Ils cliquent, l'app se télécharge et redémarre automatiquement.

---

## 3. COMMENT ÇA MARCHE (technique)

```
App démarre
    └─ 2 secondes après → thread daemon vérifie :
       GET https://raw.githubusercontent.com/USER/REPO/main/version.json
           ├─ version remote > version locale ?
           │       └─ OUI → signal Qt → bouton vert apparaît dans sidebar
           └─ NON / erreur réseau → silencieux, rien ne se passe

Utilisateur clique "Installer"
    └─ Thread télécharge le .exe depuis GitHub Releases :
       GET https://github.com/USER/REPO/releases/latest/download/FeuilleTemps_ADE.exe
           └─ Sauvegarde dans un dossier temporaire
           └─ Écrit un script .bat :
               - attend 2 secondes (app se ferme)
               - copie le nouveau .exe par-dessus l'ancien
               - relance le nouveau .exe
           └─ Lance le .bat en arrière-plan
           └─ App se ferme → .bat s'exécute → nouvelle version démarre
```

---

## 4. STRUCTURE DU REPO GITHUB

```
feuille-temps-ade/
├── feuille_temps.py      ← code source
├── version.json          ← version courante (lue par l'app)
├── build_exe.bat         ← script de build
├── README.md             ← optionnel
└── Releases/
    └── FeuilleTemps_ADE.exe   ← uploadé dans GitHub Releases (pas dans le repo)
```

---

## 5. DÉPANNAGE

**"Fonctionne uniquement depuis le .exe compilé"**
→ Normal si tu lances depuis VS Code / terminal Python.
  L'auto-update ne fonctionne que sur le .exe final.

**Bouton update n'apparaît jamais**
→ Vérifie que GITHUB_USER et GITHUB_REPO sont corrects dans le code.
→ Vérifie que version.json est bien sur la branche `main` du repo.
→ Vérifie que version dans version.json est > APP_VERSION local.
→ Le repo doit être Public.

**Erreur de téléchargement**
→ Vérifie que le Release GitHub existe avec exactement le nom `FeuilleTemps_ADE.exe`.
→ Le nom de l'asset dans GitHub Releases doit matcher EXE_NAME dans le code.

**Changer le nom du .exe**
→ Modifie `EXE_NAME = "FeuilleTemps_ADE.exe"` dans feuille_temps.py
→ Et `--name "FeuilleTemps_ADE"` dans build_exe.bat

---

© 2025 Thierry Rouillard — Groupe ADE
