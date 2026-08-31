# MCG Society Management System

A Django-based **Society Management System** for a Methodist Church Ghana (MCG) local society. It digitises the full lifecycle of member welfare cases alongside membership records, attendance, finance, committee meetings, communications, and reporting — replacing paper-based processes with a structured, auditable web application.

![Python](https://img.shields.io/badge/python-3.13-blue)
![Django](https://img.shields.io/badge/django-6.0.7-0C4B33)
![Tailwind CSS](https://img.shields.io/badge/tailwind-v4-38BDF8)
![Tests](https://img.shields.io/badge/tests-307%20passing-brightgreen)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

---

## Features

| Module | What it covers |
|---|---|
| **Members** | Registration, profiles, lifecycle (pending → active → transfer / inactive), regularisation |
| **Welfare Cases** | Submission, review, approval, disbursement, visits, closure |
| **Attendance** | Sunday services, Bible-study classes, guild / organisation meetings, absentee follow-up |
| **Finance** | Income ledger, expense vouchers with approval workflow, budget management, cashbook, payment tracker |
| **Meetings** | Scheduling, agenda, minutes editor, action-item tracker |
| **Communications** | Compose messages, announcement board, birthday messages, reminder/due notices |
| **Classes** | Bible-study class list, class details, attendance records |
| **Organisations** | Guild / organisation directory, dues and contributions |
| **Services** | Upcoming events, event calendar, service programmes, service attendance |
| **Reports** | Member, finance, welfare, and attendance report pages |
| **Notifications** | In-app notification board |
| **Core** | System settings, role-based access, administrative audit log |
| **Dashboard** | Main overview dashboard with key KPIs |

> **Database:** SQLite (development). PostgreSQL is a planned roadmap item.
> **Background tasks / messaging delivery:** Not yet implemented. Celery + Redis are roadmap items.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Django 6.0.7 |
| Frontend | Django templates, Tailwind CSS v4 |
| Database | SQLite (development) |
| Auth | Django built-in + custom `UserProfile` role model |
| Env config | `python-decouple` |
| CSS build | Node.js / npm + Tailwind CLI |

---

## Project Stats

| Item | Count |
|---|---|
| Django apps | 14 |
| Models | 42 |
| Automated tests | 307 |
| Template files | ~80 |

---

## Requirements

- **Python 3.12 or 3.13** — Django 6 requires Python 3.12+
- **Node.js + npm** — for the Tailwind CSS build step
- **Git**

---

## Getting Started

### 1 · Clone the repository

```bash
git clone https://github.com/emmanuelangelo4199/mcg_welfare_system.git
cd mcg_welfare_system
```

### 2 · Create and activate a virtual environment

**Windows (PowerShell)**
```powershell
py -3.13 -m venv e-venv
.\e-venv\Scripts\Activate.ps1
```

**Unix / macOS**
```bash
python3 -m venv e-venv
source e-venv/bin/activate
```

### 3 · Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4 · Set up environment variables

```bash
# Windows
copy .env.example .env

# Unix / macOS
cp .env.example .env
```

Open `.env` and set a real `SECRET_KEY`:

```bash
# Generate a secure key — paste the output into .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`.env` variables:

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | *(required)* | Django secret key — must be unique and private |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames |

> **Never commit `.env` to version control.** It is already listed in `.gitignore`.

### 5 · Run database migrations

```bash
python manage.py migrate
```

### 6 · Build Tailwind CSS

```bash
npm ci
npm run build
```

> The compiled CSS is written to `static/css/dist.css` and referenced by `base.html`.

### 7 · Start the development server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) — the login page will appear.

---

## Running Tests

```bash
python manage.py test --verbosity 2
```

**307 tests** across all apps — expected output: `Ran 307 tests … OK`

| App | Tests |
|---|---|
| `members` | 49 |
| `accounts` | 30 |
| `reports` | 26 |
| `welfare_cases` | 22 |
| `communications` | 21 |
| `attendance` | 20 |
| `services` | 19 |
| `classes` | 18 |
| `finance` | 18 |
| `core` | 15 |
| `meetings` | 5 |
| `dashboard` | 4 |
| **Total** | **307** |

---

## Verification Commands

Run these from the project root after any change to confirm a clean baseline:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test --verbosity 2
python manage.py collectstatic --noinput
```

All five commands should exit with code `0`.

---

## Project Structure

```
mcg_welfare_system/
├── accounts/          # Authentication, UserProfile, role management
├── members/           # Member records and lifecycle
├── classes/           # Bible-study class management
├── organisations/     # Guild / organisation directory and dues
├── services/          # Church services, events, programmes
├── attendance/        # Attendance recording for services / classes / orgs
├── finance/           # Income, expenses, budget, cashbook
├── welfare_cases/     # Welfare case lifecycle (submission → closure)
├── meetings/          # Committee meetings, minutes, action-item tracker
├── communications/    # Messages, announcements, birthday notices
├── notifications/     # In-app notification records
├── reports/           # Report pages and export views
├── core/              # System settings, role decorator, audit log
├── dashboard/         # Main KPI dashboard
├── templates/         # Shared base templates and UI components
│   └── components/    # sidebar.html, nav_item.html, etc.
├── static/
│   └── css/dist.css   # Compiled Tailwind CSS output
├── mcg_welfare_system/ # Django project settings and root URL config
├── .env.example       # Environment variable template
├── requirements.txt   # Python dependencies (UTF-8, pinned versions)
├── package.json       # Tailwind CSS build config
└── manage.py
```

---

## Security Notes

- Logout uses a **CSRF-protected POST form** — GET requests to `/accounts/logout/` are rejected.
- `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are all read from the `.env` file via `python-decouple`.
- `ALLOWED_HOSTS` defaults to `localhost,127.0.0.1` only — no wildcard `*` in code.
- `DEFAULT_AUTO_FIELD = BigAutoField` is set explicitly to suppress `W042` system warnings.
- `STATIC_ROOT` is configured — `collectstatic` works for staging / production deployments.

---

## Roadmap

The following items are planned but not yet implemented:

- [ ] PostgreSQL support
- [ ] Background task processing (Celery + Redis)
- [ ] Real SMS / email / WhatsApp message delivery
- [ ] `notifications/services.py` — centralised `notify()` dispatch
- [ ] Django `forms.py` modules (replacing raw `request.POST` parsing)
- [ ] PDF report generation
- [ ] Production deployment guide (Gunicorn + Nginx)
- [ ] Welfare case state machine with full audit trail

---

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

---

## License

MIT — see [LICENSE](LICENSE) for details.

