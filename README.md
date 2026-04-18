# ShriKirtan 🙏

A Gujarati bhajan / kirtan web app built with Flask. Displays bhajan lyrics in Gujarati script with English pronunciation, supports QR codes per bhajan, and includes a full admin backend for managing content.

**Live URL:** https://shrikirtan.fly.dev  
**GitHub:** https://github.com/dharmesp/bhajan-kirtan  
**Admin login:** https://shrikirtan.fly.dev/getmein

---

## Table of Contents

1. [What the App Does](#what-the-app-does)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Database Models](#database-models)
5. [URL Routes](#url-routes)
6. [Local Development](#local-development)
7. [Making Changes](#making-changes)
8. [Deploy to Fly.io (Single Command)](#deploy-to-flyio-single-command)
9. [Full Deploy Setup (First Time)](#full-deploy-setup-first-time)
10. [Import / Export Data](#import--export-data)
11. [Environment & Secrets](#environment--secrets)
12. [AI Context Summary](#ai-context-summary)

---

## What the App Does

- **Public home page** (`/`): Paginated list of all active bhajans (30 per page), with AJAX search by English name, category filter chips, and a QR code at the bottom linking to the app.
- **Bhajan page** (`/bhajan/<slug>`): Shows full Gujarati + English lyrics side by side. Has a dropdown to jump to any bhajan, view toggle (Both / ગુ / EN), font size A+/A− buttons, and a share button. Each bhajan has its own QR code image.
- **Admin dashboard** (`/admin/`): Table of all bhajans with edit/delete, category management, site settings (app title, domain for QR), and Import/Export to JSON.
- **First-run setup** (`/setup`): Creates the admin account. Only works if no admin exists yet.
- **Admin login** (`/getmein`): Username + password login. Session lasts 8 hours.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web Framework | Flask 3.1.3 |
| ORM | Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.x) |
| Database | SQLite (local: `instance/shrikirtan.db`, production: `/data/shrikirtan.db`) |
| Forms / CSRF | Flask-WTF 1.2.2 |
| QR Codes | qrcode[pil] 8.x + Pillow 12.x |
| WSGI Server | Gunicorn 22.x (production) |
| Frontend | Bootstrap 5.3.3 + Bootstrap Icons 1.11.3 (CDN) |
| Fonts | Noto Sans Gujarati + Nunito (Google Fonts) |
| Hosting | Fly.io (Chicago `ord` region) |
| Container | Docker (Python 3.12-slim, 2 gunicorn workers) |
| Version Control | Git → GitHub |

---

## Project Structure

```
shrikirtan/                   ← repo root
├── run.py                    ← entry point (creates app, runs dev server)
├── requirements.txt          ← Python dependencies
├── Dockerfile                ← container build for Fly.io
├── fly.toml                  ← Fly.io app config (region, volume, machine size)
├── .gitignore                ← excludes venv (app/), instance/, .env
├── .dockerignore             ← same exclusions for Docker build
│
├── app/                      ← Python virtual environment (NOT committed to git)
│
├── instance/                 ← runtime data (NOT committed to git)
│   ├── shrikirtan.db         ← local SQLite database
│   └── secret.key            ← auto-generated Flask secret key (local only)
│
└── shrikirtan/               ← Flask application package
    ├── __init__.py           ← app factory: DB init, blueprints, config
    ├── models.py             ← SQLAlchemy models (see below)
    │
    ├── routes/
    │   ├── public.py         ← public routes: home, bhajan view, search API, QR
    │   ├── admin.py          ← admin routes: login, CRUD, settings, export/import
    │   └── setup.py          ← /setup first-run admin creation
    │
    ├── static/
    │   ├── css/style.css     ← all custom styles (saffron theme, Bootstrap overrides)
    │   └── js/app.js         ← dark/light theme toggle, localStorage persistence
    │
    └── templates/
        ├── base.html         ← navbar, dark mode toggle, flash messages, footer
        ├── index.html        ← home page: list, search, category filters, QR
        ├── bhajan.html       ← bhajan detail: content, controls, QR, share
        ├── login.html        ← /getmein login page
        ├── setup.html        ← first-run setup page
        └── admin/
            ├── dashboard.html    ← admin table, categories, import/export
            ├── bhajan_form.html  ← add/edit bhajan form
            └── settings.html    ← domain name + app title settings
```

---

## Database Models

### `Category`
| Field | Type | Notes |
|---|---|---|
| id | Integer PK | auto |
| name | String(100) | unique |
| display_order | Integer | 0 = first |

### `Bhajan`
| Field | Type | Notes |
|---|---|---|
| id | Integer PK | auto |
| title_gujarati | String(300) | required |
| title_english | String(300) | required, used for slug |
| content_gujarati | Text | lyrics in Gujarati script |
| content_english | Text | English pronunciation |
| category_id | FK → Category | nullable |
| slug | String(300) | unique, URL-safe, auto-generated from title_english |
| display_order | Integer | 999 default |
| is_active | Boolean | false = hidden from public |
| created_at / updated_at | DateTime | auto |

### `Setting` (key-value store)
| Key | Default | Purpose |
|---|---|---|
| `domain_name` | `` | Used in QR code URLs (e.g. `https://shrikirtan.fly.dev`) |
| `app_title` | `ShriKirtan` | Shown in navbar and page titles |

### `AdminUser`
| Field | Type | Notes |
|---|---|---|
| username | String | unique |
| password_hash | String | PBKDF2-SHA256 via Werkzeug |

---

## URL Routes

### Public
| Method | URL | Description |
|---|---|---|
| GET | `/` | Home page, paginated bhajan list |
| GET | `/api/search?q=&cat=` | AJAX search, returns JSON array |
| GET | `/bhajan/<slug>` | Bhajan detail page |
| GET | `/bhajan/<slug>/qrcode.png` | QR code image for that bhajan |
| GET | `/qrcode.png` | QR code for the home page URL |
| GET | `/setup` | First-run admin account creation |

### Admin (require login)
| Method | URL | Description |
|---|---|---|
| GET/POST | `/getmein` | Admin login |
| GET | `/admin/` | Dashboard |
| GET/POST | `/admin/bhajan/add` | Add new bhajan |
| GET/POST | `/admin/bhajan/edit/<id>` | Edit bhajan |
| POST | `/admin/bhajan/delete/<id>` | Delete bhajan |
| POST | `/admin/category/add` | Add category |
| POST | `/admin/category/delete/<id>` | Delete category |
| GET/POST | `/admin/settings` | App title + domain settings |
| GET | `/admin/export` | Download all data as JSON |
| POST | `/admin/import` | Upload JSON to import data |
| GET | `/admin/logout` | Clear session |

---

## Local Development

### First time setup
```powershell
# Activate the virtual environment
.\app\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the dev server
python run.py
```

App runs at: http://localhost:5000  
Admin: http://localhost:5000/setup (first run) then http://localhost:5000/getmein

### LAN access (for phones on same Wi-Fi)
The dev server binds to `0.0.0.0:5000` automatically. Find your IP:
```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' }
```
Visit `http://<your-ip>:5000` from any device on the network.

---

## Making Changes

1. Edit files in `shrikirtan/` (Python/templates/CSS/JS)
2. The dev server auto-reloads on save (`debug=True` in `run.py`)
3. Test locally at http://localhost:5000
4. Commit and push:
```powershell
git add .
git commit -m "describe your change"
git push
```
5. Deploy (see next section)

### Common change locations
| What to change | File |
|---|---|
| Home page layout | `shrikirtan/templates/index.html` |
| Bhajan page layout | `shrikirtan/templates/bhajan.html` |
| Navbar / footer | `shrikirtan/templates/base.html` |
| Colors / fonts / CSS | `shrikirtan/static/css/style.css` |
| Dark mode JS | `shrikirtan/static/js/app.js` |
| Public page logic | `shrikirtan/routes/public.py` |
| Admin logic | `shrikirtan/routes/admin.py` |
| Database models | `shrikirtan/models.py` |
| App config / startup | `shrikirtan/__init__.py` |

---

## Deploy to Fly.io (Single Command)

After committing your changes, deploy with:

```powershell
C:\Users\dharm\.fly\bin\flyctl.exe deploy --app shrikirtan
```

That's it. Fly.io builds the Docker image, pushes it, and does a zero-downtime rolling deploy. Takes ~30 seconds.

---

## Full Deploy Setup (First Time Only)

If setting up on a new machine from scratch:

```powershell
# 1. Install flyctl
iwr https://fly.io/install.ps1 -useb | iex

# 2. Add to PATH (current session)
$env:PATH += ";C:\Users\dharm\.fly\bin"

# 3. Login (opens browser)
flyctl auth login

# 4. Deploy (reads fly.toml)
flyctl deploy --app shrikirtan
```

The volume and secrets already exist in Fly.io — no need to recreate them.

---

## Import / Export Data

The admin dashboard has **Export JSON** and **Import JSON** buttons.

**Export**: Downloads a timestamped `.json` file with all categories and bhajans.

**Import**: Upload a previously exported `.json`. Behaviour:
- Bhajans matched by `slug` → **updated**
- New slugs → **added as new bhajans**
- Missing categories → **automatically created**
- Missing title fields → **skipped**

Use this to:
- Back up all content before making risky changes
- Transfer data between local and production
- Bulk-add bhajans by editing the JSON file

---

## Environment & Secrets

| Variable | Where set | Purpose |
|---|---|---|
| `SECRET_KEY` | `fly secrets set SECRET_KEY=...` | Flask session signing |
| `DATABASE_URL` | `fly.toml [env]` | SQLite path on volume: `sqlite:////data/shrikirtan.db` |
| `FLY_APP_NAME` | Fly.io auto-set | Enables `SESSION_COOKIE_SECURE=True` |

Locally, `SECRET_KEY` is auto-generated and saved to `instance/secret.key`.  
The database is at `instance/shrikirtan.db` locally.

**Never commit** the `instance/` folder or `app/` (venv) to git — both are in `.gitignore`.

### Update the secret key on Fly.io
```powershell
$sk = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Max 256) })
C:\Users\dharm\.fly\bin\flyctl.exe secrets set SECRET_KEY=$sk --app shrikirtan
```

---

## AI Context Summary

> Read this section to quickly understand the project when building AI context from scratch.

**Project**: ShriKirtan — a mobile-friendly web app for displaying Gujarati devotional songs (bhajans/kirtans) with transliteration. Used at Shrinathji Haveli, Irvine, CA.

**Stack in one line**: Flask + SQLite + Bootstrap 5 + Fly.io Docker deployment.

**Key design decisions**:
- SQLite is used intentionally (single writer, simple ops, persistent 10 GB Fly.io volume)
- No JavaScript framework — plain Bootstrap 5 with minimal vanilla JS for search debounce, view toggle, font size, dark mode
- AJAX search hits `/api/search?q=` with 280ms debounce; the static paginated list is shown when search is empty
- All forms have CSRF protection via Flask-WTF
- Admin is at non-obvious URL `/getmein` (lightweight security through obscurity)
- Bhajan slugs are auto-generated from `title_english` and guaranteed unique
- Font size buttons work by setting `font-size` in `px` on the `#bhajanContent` container; child elements use `em` units so they scale relative to it
- Dark/light mode uses Bootstrap's `data-bs-theme` attribute, persisted in `localStorage sk_theme`
- Color theme: saffron amber (`#b45309` light, `#fbbf24` dark) overrides Bootstrap's primary

**Fly.io specifics**:
- App name: `shrikirtan`
- Region: `ord` (Chicago)
- 1 machine only (SQLite volumes can only attach to one machine)
- Volume `shrikirtan_data` (10 GB) mounted at `/data`
- Machine: shared-cpu-1x, 256 MB RAM
- Auto-stops when idle to save cost; wakes on first request (~2s cold start)

**File to read first** for any change: `shrikirtan/__init__.py` (app factory — shows config, blueprints, DB init).

**GitHub repo**: https://github.com/dharmesp/bhajan-kirtan  
**Live app**: https://shrikirtan.fly.dev
