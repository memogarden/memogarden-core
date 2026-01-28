#!/bin/bash
# Development server (Flask built-in)
poetry run python -m flask --app memogarden.main run --debug

# Or use gunicorn (production)
# poetry run gunicorn memogarden.main:app
