# MCG Welfare

A Django-based **Welfare Management Module** for a Methodist Church Ghana (MCG) Society Management System. It handles the end-to-end lifecycle of member welfare cases — from submission and review to approval, disbursement, and notification — within a church society context.

## Overview

MCG Welfare digitizes the welfare support process for church societies, replacing manual, paper-based tracking with a structured, auditable system. At its core is the `WelfareCase` model, which acts as the central hub connecting members, case types, approvals, disbursements, and notifications.

## Key Features

- **Welfare case management** — submit, track, and resolve welfare requests from society members
- **Centralized notifications** — a unified `notify()` dispatch pattern (`notifications/services.py`) for in-app, email, and/or SMS alerts across the system
- **Role-based workflows** — case handling routed through appropriate society leadership/approval chains
- **Background task processing** — Celery-powered async jobs for notifications, reports, and scheduled tasks
- **Responsive UI** — built with Tailwind CSS for a clean, mobile-friendly experience

## Tech Stack

| Layer            | Technology         |
|-------------------|---------------------|
| Backend           | Django              |
| Styling           | Tailwind CSS         |
| Async/Background  | Celery               |
| Database          | PostgreSQL (or SQLite3 for development) |

## Project Structure

The project is organized into a modular, multi-app Django structure (14 apps), with `welfare_cases` serving as the central hub. Each app is scoped to a single responsibility (e.g., members, notifications, disbursements) to keep the codebase maintainable as the system grows.

```
mcg_welfare/
├── accounts/          # User authentication, login, and account management
├── welfare_cases/     # Central hub: WelfareCase model and core logic
├── notifications/     # Centralized notify() dispatch service
├── members/           # Member profiles and society records
├── ...                # Additional supporting apps
```

## Getting Started

### Prerequisites
- Python 3.x
- PostgreSQL
- Redis (for Celery)

### Installation

```bash
git clone https://github.com/emmanuelangelo4199/mcg_welfare.git
cd mcg_welfare
py -m venv e-venv
source e-venv/bin/activate  # On Windows: e-venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file with the required environment variables (database credentials, secret key, Celery broker URL, etc.).

### Run Migrations & Start the Server

```bash
python manage.py migrate
python manage.py runserver
```

### Start Celery Worker

```bash
celery -A mcg_welfare worker -l info
```

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

## License

[MIT](LICENSE)


<!-- pip freeze > requirements.txt -->