# ShriKirtan 🙏

A Gujarati bhajan / kirtan web app built with Flask. Displays bhajan lyrics in Gujarati script with English pronunciation, AJAX search, category filters, QR codes, a full admin backend, and a live **"Now Playing"** indicator for temple use.

**Live URL:** https://shrikirtan.fly.dev  
**GitHub:** https://github.com/dharmesp/bhajan-kirtan

---

## Table of Contents

1. [Quick Start — Using the App](#quick-start--using-the-app)
2. [Three Logins Explained](#three-logins-explained)
3. [Public Features (No Login)](#public-features-no-login)
4. [Site Manager Features](#site-manager-features)
5. [Admin Features](#admin-features)
6. [Now Playing Feature](#now-playing-feature)
7. [Tech Stack](#tech-stack)
8. [Project Structure](#project-structure)
9. [Database Models](#database-models)
10. [URL Routes Reference](#url-routes-reference)
11. [Local Development](#local-development)
12. [Making Changes](#making-changes)
13. [Deploy to Fly.io (Single Command)](#deploy-to-flyio-single-command)
14. [Full Deploy Setup (First Time)](#full-deploy-setup-first-time)
15. [Import / Export Data](#import--export-data)
16. [Environment & Secrets](#environment--secrets)
17. [AI Context Summary](#ai-context-summary)

---

## Quick Start — Using the App

| Who you are | Where to go | What you can do |
|---|---|---|
| Devotee / public | https://shrikirtan.fly.dev | Browse, search, read bhajans |
| Temple volunteer / screen operator | https://shrikirtan.fly.dev/manage/login | Toggle visibility, set display order, see Now Playing |
| Temple admin | https://shrikirtan.fly.dev/getmein | Full content management (add/edit/delete bhajans) |

---

## Three Logins Explained

### 1. Public — No Login
Anyone who opens the app URL. No credentials needed. Can browse, search, and read all **active + visible** bhajans.

---

### 2. Site Manager Login
**URL:** `/manage/login`  
**Purpose:** For temple volunteers or someone operating a display screen. They can control *what is shown* to the public without being able to create or delete content.  
**Session:** Persists until logout (uses Flask session cookie).

**How to create a manager account:**  
Only the Admin can do this — log in as Admin, go to `/admin/managers`, and click **Add Manager**. Share the username+password with the volunteer.

**What a manager can do** (details in [Site Manager Features](#site-manager-features)):
- Show or hide individual bhajans from the public list (toggle per row)
- Show All / Hide All with one click
- Change the display order of bhajans (inline number edit)
- Filter by category in the dashboard
- Click the eye icon to view any bhajan exactly as the public sees it
- The navbar shows a "Manage" button only when logged in as manager
- **Now Playing** is automatic — just opening a bhajan page sets it as playing for the public

---

### 3. Admin Login
**URL:** `/getmein`  
**Purpose:** Full content management. Intended for the temple administrator.  
**Session:** 8 hours.

**First-time setup:** Visit `/setup` to create the Admin account (only works if no admin exists yet).

**What the admin can do** (details in [Admin Features](#admin-features)):
- Add, edit, and delete bhajans (Gujarati + English content)
- Manage categories and display order
- Change app title and domain name (used in QR codes)
- Export all data to JSON / Import from JSON
- Create and delete Site Manager accounts

---

## Public Features (No Login)

### Browsing the Bhajan List
- Opens at `/` — shows 30 bhajans per page, sorted by display order
- Only bhajans marked **active** AND **visible** by the manager appear
- Pagination at the bottom: Previous / Page numbers / Next

### Category Filter Chips
- Pill buttons at the top of the list (e.g., "All", "Haveli", "Garba")
- Click any chip to filter the list to that category instantly (no page reload)
- Combines with the search box — filter by category AND search term simultaneously

### AJAX Search
- Type in the search box to search by **English title** (280 ms debounce)
- Results appear instantly without page reload
- Shows count: "5 bhajans for 'govind'"
- Search term is highlighted in yellow in the results
- Clear button (×) to reset search and return to the full list

### Bhajan Detail Page (`/bhajan/<slug>`)
- **Sticky controls bar** at the top (stays visible while scrolling):
  - ← Back to list button
  - Dropdown to jump to any bhajan by name
  - **View toggle**: Both | ગુ (Gujarati only) | EN (English only) — preference saved in browser
  - **Font size A+ / A−** — adjusts size in 2px steps (12px–40px), saved in browser
- Gujarati lyrics section with Gujarati script
- English pronunciation / transliteration section
- **QR Code** at the bottom — scan to open this exact bhajan on any device
- **Share button** — uses native device share sheet (or copies link to clipboard)

### Dark Mode
- Sun/moon toggle in the navbar
- Preference saved in browser (`localStorage`)

### Homepage QR Code
- At the bottom of the home page — scan to open the whole app on another device

---

## Site Manager Features

**Login at:** `/manage/login`

After logging in, you land on the **Manager Dashboard** at `/manage/`.

### Manager Dashboard
The dashboard shows all **active** bhajans in a table with:

| Column | Description |
|---|---|
| Order | Inline editable number — type a new value and press Enter or Tab to save |
| Gujarati Title | As it appears to the public |
| English Title | Used for search |
| Category | Badge showing category name |
| Visible | Toggle switch — green = shown to public, grey = hidden from public |
| View | Eye icon — opens that bhajan page as the public would see it |

### Category Filter (Manager Dashboard)
Chips at the top of the dashboard let you filter which bhajans are shown in the table — same way as the public list. Useful when managing a large collection.

### Show All / Hide All
Two buttons at the top of the dashboard:
- **Show All** — makes every active bhajan visible to the public
- **Hide All** — hides every active bhajan from the public

Use this during a programme to reveal/hide the entire set at once, or to start fresh.

### Visibility Toggle (Per Bhajan)
Click the toggle switch next to any bhajan to instantly show or hide it from the public. The public list refreshes dynamically — visitors already on the page will see the change within 5 seconds (polling interval).

### Display Order
Click the number in the **Order** column, type a new number (lower = earlier in list), and press Enter. The change takes effect immediately. The public list shows bhajans in this order.

### Viewing a Bhajan as Public
Click the eye icon (👁) to open that bhajan's detail page. The back button on the bhajan page returns you to the manager dashboard.

### Manager Navbar
When logged in as manager, the navbar shows a **"Manage" button** (sliders icon) on every page, so you can return to the dashboard at any time.

### Logout
Click **Logout** in the navbar or visit `/manage/logout`.

---

## Admin Features

**Login at:** `/getmein`  
**First run:** `/setup` to create the admin account.

### Bhajan Management
- **Add Bhajan** — fill in Gujarati title, English title, Gujarati content, English pronunciation content, and assign a category
- **Edit Bhajan** — change any field; slug is auto-regenerated
- **Delete Bhajan** — permanent deletion (no undo; export first as backup)
- **is_active toggle** — admin-level hide (different from manager visibility); inactive bhajans never appear publicly even if `is_visible=True`

### Category Management
- **Add Category** — name + display order number
- **Delete Category** — only if no bhajans use it
- Categories appear as filter chips on the public page and manager dashboard

### Settings
At `/admin/settings`:
- **App Title** — text shown in the navbar and browser tab (e.g., "ShriKirtan" or "Shrinathji Haveli")
- **Domain Name** — base URL used in QR codes (e.g., `https://shrikirtan.fly.dev`); if blank, the current request host is used

### Site Manager Accounts
At `/admin/managers`:
- See all manager accounts and their creation dates
- **Add Manager** — set username + password
- **Delete Manager** — removes their login access
- Each manager's login URL is shown for easy sharing

### Export / Import JSON
**Export** (button on dashboard) — downloads a `bhajans_YYYY-MM-DD.json` file with all categories and bhajans. Use as a backup before any major change.

**Import** (upload on dashboard):
- Upload a previously exported `.json`
- Bhajans matched by `slug` → **updated in place**
- New slugs → **added as new bhajans**
- Missing categories → **auto-created**
- Records with missing title fields → **skipped with a warning**

Use this to: back up/restore data, transfer between local and production, or bulk-add bhajans by editing the JSON.

### Logout
`/admin/logout` or the Logout button in the navbar.

---

## Now Playing Feature

This feature lets the public see which bhajan is currently being sung/played in the temple — live, with no manual button.

### How it works

**Manager side (automatic):**
1. Manager opens any bhajan page (e.g., navigates to it from the dashboard)
2. The page **automatically** registers that bhajan as "Now Playing" with a UTC timestamp
3. A **heartbeat** fires every 30 seconds to keep it alive as long as the manager has the page open
4. When the manager navigates away or closes the tab, a `sendBeacon` clears "Now Playing" immediately; if that misses, it **auto-expires after 60 seconds** of no heartbeat

**Public side (live updates):**
- Home page polls `/api/now-playing` every **5 seconds**
- The matching bhajan row highlights with a **green left border**, subtle green tint, and a **pulsing green dot**
- This works in both the static paginated list and live search results
- Bhajan detail page also polls every 5 seconds — if this is the current bhajan, a **"Now Playing" green badge** appears above the title

### Typical temple use
1. Priest or volunteer logs in as **Site Manager** on a tablet/laptop
2. Before the programme: use **Hide All**, then show only today's bhajans using visibility toggles
3. When a bhajan begins, open it on the manager's device — it immediately appears as "Now Playing" on the big screen / devotees' phones
4. Moving to the next bhajan: open the next bhajan page — previous one clears, new one lights up
5. Programme ends: close the tab or navigate away — Now Playing clears automatically

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
    ├── __init__.py           ← app factory: DB init, blueprints, config, migrations
    ├── models.py             ← SQLAlchemy models (see below)
    │
    ├── routes/
    │   ├── public.py         ← public routes: home, bhajan view, search API, QR, now-playing API
    │   ├── admin.py          ← admin routes: login, CRUD, settings, export/import, managers
    │   ├── manage.py         ← site manager routes: login, dashboard, visibility/order/now-playing APIs
    │   └── setup.py          ← /setup first-run admin creation
    │
    ├── static/
    │   ├── css/style.css     ← all custom styles (saffron theme, Bootstrap overrides, now-playing pulse)
    │   └── js/app.js         ← dark/light theme toggle, localStorage persistence
    │
    └── templates/
        ├── base.html             ← navbar, dark mode toggle, flash messages, footer
        ├── index.html            ← home page: list, search, category filters, QR, now-playing polling
        ├── bhajan.html           ← bhajan detail: content, controls, QR, share, now-playing banner
        ├── login.html            ← /getmein admin login page
        ├── setup.html            ← first-run setup page
        ├── admin/
        │   ├── dashboard.html    ← admin table, categories, import/export, managers button
        │   ├── bhajan_form.html  ← add/edit bhajan form
        │   ├── settings.html     ← domain name + app title settings
        │   └── managers.html     ← list/add/delete site manager accounts
        └── manage/
            ├── login.html        ← /manage/login page
            └── dashboard.html    ← manager dashboard: table, toggles, order edit, category chips
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
| is_active | Boolean | admin-level hide — false = never public |
| is_visible | Boolean | manager-level hide — false = hidden from public (default True) |
| created_at / updated_at | DateTime | auto |

### `Setting` (key-value store)
| Key | Default | Purpose |
|---|---|---|
| `domain_name` | `` | Used in QR code URLs (e.g. `https://shrikirtan.fly.dev`) |
| `app_title` | `ShriKirtan` | Shown in navbar and page titles |
| `now_playing_id` | `` | Bhajan ID currently playing (set by manager) |
| `now_playing_at` | `` | UTC ISO timestamp of last heartbeat; expires after 60s |

### `AdminUser`
| Field | Type | Notes |
|---|---|---|
| username | String | unique |
| password_hash | String | PBKDF2-SHA256 via Werkzeug |

### `SiteManager`
| Field | Type | Notes |
|---|---|---|
| id | Integer PK | auto |
| username | String(80) | unique |
| password_hash | String | PBKDF2-SHA256 via Werkzeug |
| created_at | DateTime | auto |

---

## URL Routes Reference

### Public (no login)
| Method | URL | Description |
|---|---|---|
| GET | `/` | Home page, paginated bhajan list |
| GET | `/api/search?q=&cat=` | AJAX search, returns JSON array |
| GET | `/api/now-playing` | Returns current now-playing bhajan or null |
| GET | `/bhajan/<slug>` | Bhajan detail page |
| GET | `/bhajan/<slug>/qrcode.png` | QR code image for that bhajan |
| GET | `/qrcode.png` | QR code for the home page URL |
| GET | `/setup` | First-run admin account creation |

### Admin (require admin login)
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
| GET | `/admin/managers` | List / add / delete site managers |
| POST | `/admin/managers/add` | Create a manager account |
| POST | `/admin/managers/delete/<id>` | Remove a manager account |
| GET | `/admin/logout` | Clear admin session |

### Site Manager (require manager login)
| Method | URL | Description |
|---|---|---|
| GET/POST | `/manage/login` | Manager login |
| GET | `/manage/logout` | Clear manager session |
| GET | `/manage/` | Manager dashboard |
| POST | `/manage/api/toggle/<id>` | Flip `is_visible` for a bhajan |
| POST | `/manage/api/show-all` | Set `is_visible=True` for all active bhajans |
| POST | `/manage/api/hide-all` | Set `is_visible=False` for all active bhajans |
| POST | `/manage/api/order/<id>` | Update `display_order` |
| POST | `/manage/api/now-playing/set/<id>` | Set now-playing + timestamp |
| POST | `/manage/api/now-playing/clear` | Clear now-playing |

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
Admin setup: http://localhost:5000/setup (first run only)  
Admin login: http://localhost:5000/getmein  
Manager login: http://localhost:5000/manage/login

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
| Home page layout / search | `shrikirtan/templates/index.html` |
| Bhajan page layout | `shrikirtan/templates/bhajan.html` |
| Manager dashboard | `shrikirtan/templates/manage/dashboard.html` |
| Admin dashboard | `shrikirtan/templates/admin/dashboard.html` |
| Navbar / footer | `shrikirtan/templates/base.html` |
| Colors / fonts / CSS | `shrikirtan/static/css/style.css` |
| Dark mode JS | `shrikirtan/static/js/app.js` |
| Public page logic | `shrikirtan/routes/public.py` |
| Admin logic | `shrikirtan/routes/admin.py` |
| Manager logic | `shrikirtan/routes/manage.py` |
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

> Read this section to quickly rebuild AI context from scratch.

**Project**: ShriKirtan — a mobile-friendly web app for displaying Gujarati devotional songs (bhajans/kirtans) with transliteration. Used at a Shrinathji Haveli temple.

**Stack in one line**: Flask + SQLite + Bootstrap 5 + Fly.io Docker deployment.

**Key design decisions**:
- SQLite used intentionally (single writer, simple ops, persistent 10 GB Fly.io volume)
- No JavaScript framework — plain Bootstrap 5 with minimal vanilla JS
- AJAX search hits `/api/search?q=&cat=` with 280ms debounce
- All forms have CSRF protection via Flask-WTF; AJAX calls use `X-CSRFToken` header
- Admin is at non-obvious URL `/getmein`; manager at `/manage/login`
- Three roles: public (no auth), site manager (visibility/order/now-playing), admin (full CRUD)
- Now Playing stored in `Setting` table as `now_playing_id` + `now_playing_at` (UTC ISO string); expires 60s after last heartbeat
- Bhajan slugs are auto-generated from `title_english` and guaranteed unique
- Font size buttons work by setting `font-size` in `px` on `#bhajanContent`; child elements use `em` so they scale
- Dark/light mode uses Bootstrap's `data-bs-theme`, persisted in `localStorage sk_theme`
- Color theme: saffron amber (`#b45309` light, `#fbbf24` dark) overrides Bootstrap's primary

**Fly.io specifics**:
- App name: `shrikirtan`, region: `ord` (Chicago)
- 1 machine only (SQLite volumes can only attach to one machine)
- Volume `shrikirtan_data` (10 GB) mounted at `/data`
- Machine: shared-cpu-1x, 256 MB RAM
- Auto-stops when idle; wakes on first request (~2s cold start)

**File to read first** for any change: `shrikirtan/__init__.py` (app factory).

**GitHub repo**: https://github.com/dharmesp/bhajan-kirtan  
**Live app**: https://shrikirtan.fly.dev

