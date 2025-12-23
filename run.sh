#!/bin/bash
# Development server (Flask built-in)
poetry run python -m flask --app memogarden_core.main run --debug

# Or use gunicorn (production)
# poetry run gunicorn memogarden_core.main:app
