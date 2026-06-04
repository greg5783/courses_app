# Courses App

A small Flask-based web app for managing sailing regatta courses, waypoints, series types, and out-of-bounds polygons.

## Features

- view and manage course data via a web interface
- simple JSON-backed storage in `courses_data/`
- login-protected API calls for create/update/delete actions
- deployable with `gunicorn` or run locally with Flask

## Requirements

- Python 3.10+ (or compatible)
- `Flask==2.2.2`
- `Werkzeug<3.0`
- `gunicorn>=21.2`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run locally

```bash
export SWSA_SCORE_PASSWORD="your-password"
export SWSA_SCORE_SECRET_KEY="your-secret-key"
python courses_app.py
```

Then open `http://127.0.0.1:8081/`.

## Production

Example using `gunicorn`:

```bash
gunicorn -b 0.0.0.0:8081 courses_app:app
```

## Environment variables

- `SWSA_SCORE_PASSWORD`: password used by the login route
- `SWSA_SCORE_SECRET_KEY`: Flask secret key for session management
- `COURSES_DIR`: optional directory for JSON data files
- `COURSES_PORT`: optional port for local Flask run

## Repository contents

- `courses_app.py` — Flask application
- `requirements.txt` — Python dependencies
- `courses_data/` — JSON data files
- `templates/` — Flask HTML templates
- `static/` — CSS and assets
