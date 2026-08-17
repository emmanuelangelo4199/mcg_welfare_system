# MCG Society Management System

A Django-based **Society Management System** for a Methodist Church Ghana (MCG) local society. It covers the full lifecycle of member welfare cases alongside membership records, attendance, finance, meetings, communications, and reporting — replacing paper-based processes with a structured, auditable web application.

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Django](https://img.shields.io/badge/django-6.0.7-0C4B33)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

---

## Features

- **Member management** — registration, profiles, lifecycle (pending, active, transfer, inactive)
- **Welfare case tracking** — submission, review, approval, disbursement, and closure
- **Attendance recording** — Sunday services, Bible study classes, and guild/organisation meetings
- **Finance** — income ledger, expense vouchers with approval workflow, budget management, cashbook
- **Meetings** — scheduling, minutes, and action-item tracker
- **Communications** — announcements and outgoing message records
- **Reports** — member, finance, and welfare CSV exports
- **Role-based access** — Admin, Treasurer, Class Leader, Welfare Officer, Member
- **Audit trail** — system settings and administrative action log

> **Current database:** SQLite (development only). PostgreSQL migration is a planned roadmap item.
> **Background tasks / messaging delivery:** Not yet implemented. Celery and Redis are roadmap items.

---

## Tech Stack

| Layer     | Technology              |
|-----------|-------------------------|
| Backend   | Python 3.12+, Django 6  |
| Frontend  | Django templates, Tailwind CSS v4 |
| Database  | SQLite (development)    |
| Auth      | Django built-in + custom roles |

---

## Requirements

- **Python 3.12 or 3.13** (Django 6.0 requires Python 3.12+)
- Node.js + npm (for the Tailwind CSS build)
- Git

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/emmanuelangelo4199/mcg_welfare_system.git
cd mcg_welfare_system
```

### 2. Create and activate a virtual environment

**Unix / macOS**
```bash
python3 -m venv e-venv
source e-venv/bin/activate
```

**Windows (PowerShell)**
```powershell
py -3.13 -m venv e-venv
.\e-venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
# Copy the example file
cp .env.example .env        # Unix/macOS
copy .env.example .env      # Windows
```

Open `.env` and replace `SECRET_KEY` with a real secret:

```bash
# Generate a key (run once, paste the output into .env)
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

> **Never commit `.env` to version control.**

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Load demo data (optional, development only)

```bash
python manage.py seed_data
```

> Do **not** run `seed_data` in production — it creates demo accounts with known passwords.

### 7. Build Tailwind CSS

```bash
npm ci
npm run build
```

### 8. Start the development server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Running Tests

```bash
python manage.py test --verbosity 2
```

---

## Verification Commands

Run these from the project root to confirm a clean baseline:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test --verbosity 2
python manage.py collectstatic --noinput
```

---

## Project Structure

```
mcg_welfare_system/
├── accounts/          # Authentication, profiles, and role management
├── members/           # Member records and lifecycle
├── classes/           # Bible study classes
├── organisations/     # Church organisations and dues
├── services/          # Church services and events
├── attendance/        # Attendance recording
├── finance/           # Income, expenses, budgets, cashbook
├── welfare_cases/     # Welfare case lifecycle
├── meetings/          # Committee meetings, minutes, action items
├── communications/    # Announcements and outgoing message records
├── notifications/     # In-app notification records
├── reports/           # Report pages and CSV exports
├── core/              # System settings, role decorator, audit log
├── dashboard/         # Main and role-specific dashboards
├── templates/         # Shared base templates and components
└── static/            # CSS (Tailwind build output) and JS
```

---

## Roadmap

The following items are planned but not yet implemented:

- PostgreSQL support
- Background task processing (Celery + Redis)
- Real SMS / email / WhatsApp delivery
- `notifications/services.py` dispatch service
- PDF report generation
- Production deployment guide

---

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

---

## License

MIT — see [LICENSE](LICENSE) for details.