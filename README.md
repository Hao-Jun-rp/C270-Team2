# 🧼 Sparkle — Cleaning Service App (C270 DevOps, AY2026S1)

A team project built with **Python + Flask**. Each teammate owns one feature, and
everything is combined on GitHub. This README tells you how to run it and how to
work together without breaking each other's code.

---

## 1. One-time setup (do this once on your laptop)

You need **Python 3.10+** and **Git** installed.

```bash
# 1. Get the code
git clone <PASTE-THE-GITHUB-LINK-HERE>
cd cleaning-app

# 2. Create a "virtual environment" (a clean, private box for this project's libraries)
python -m venv venv

# 3. Turn it on
#    Windows:
venv\Scripts\activate
#    Mac / Linux:
source venv/bin/activate

# 4. Install the libraries the app needs
pip install -r requirements.txt

# 5. Create your secret key file
#    Copy .env.example to .env and put any long random text after SECRET_KEY=
```

## 2. Run the app

```bash
python run.py
```

Open the link it prints (usually **http://127.0.0.1:5000**) in your browser.
You should see the Sparkle home page. Try **Sign up → Log in** — that part already works.

To stop the app: press **Ctrl + C** in the terminal.

---

## 3. Where is MY stuff? (folder map)

```
cleaning-app/
├── app/
│   ├── __init__.py        ← builds the app  (SHARED — ask Marcus before editing)
│   ├── config.py          ← settings         (SHARED)
│   ├── extensions.py      ← db + login tools (SHARED)
│   ├── models.py          ← database tables  (SHARED)
│   ├── static/theme.css   ← the design system (SHARED)
│   ├── templates/base.html← shared page layout (SHARED)
│   │
│   ├── auth/          ← Marcus    (login / profile)  ← finished example, copy this pattern
│   ├── dashboard/     ← Tristan
│   ├── listings/      ← Hazirah
│   ├── booking/       ← Ashish
│   ├── reviews/       ← Matthew
│   └── notifications/ ← Hao Jun
└── tests/            ← simple tests
```

**You work inside your own folder.** Each folder has:
- `routes.py` — your pages (the web addresses)
- `templates/<your-feature>/` — your HTML pages

Look at the **`auth/`** folder for a complete working example.

---

## 4. The golden rules (this is what keeps merges smooth)

1. **Only edit your own folder.** Don't touch teammates' folders.
2. **The SHARED files are Marcus's.** Need a new database table or library?
   Tell Marcus — don't edit `models.py`, `config.py`, `__init__.py`, or
   `requirements.txt` yourself.
3. **Always start your work on a fresh branch:**
   ```bash
   git checkout main
   git pull origin main          # get everyone's latest work first
   git checkout -b feature/<your-feature>
   ```
4. **Use the design system.** Style with the classes in `theme.css`
   (`.btn`, `.card`, `.pill`, `.input`) and never hard-code colours — use
   `var(--color-primary)` etc. This keeps every screen looking like one app.
5. **Commit small and often, with real messages:**
   ```bash
   git add .
   git commit -m "Add booking calendar page"
   git push origin feature/<your-feature>
   ```
6. **Merge through a Pull Request** on GitHub (don't push to `main` directly).
   Get one teammate to glance at it before merging.

---

## 5. Daily flow (memorise this)

```
pull main  →  make a branch  →  build in your folder  →  commit  →  push  →  open a Pull Request
```

---

## 6. Run the test (optional, but nice)

```bash
pytest
```
If it says **1 passed**, the app is healthy. This same test becomes part of our
automated pipeline in Phase 2.

Happy building! ✨
