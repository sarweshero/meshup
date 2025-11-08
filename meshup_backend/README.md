# Meshup Backend

Meshup is an enterprise-grade collaborative team communication and project management platform. This repository contains the backend implementation built with Django REST Framework and PostgreSQL, shipped with Docker-based tooling for local development and production deployment.

## Features
- Real-time ready messaging with channels, direct messaging, threads, reactions, and mentions
- Collaboration toolkit: tasks, notes with version history, events & calendar, polls, and customizable settings
- Role-Based Access Control (RBAC) with granular permissions per server
- JWT authentication with refresh token rotation and password reset workflows
- RESTful, paginated APIs with consistent JSON responses and rich filtering
- Celery-ready project layout for async jobs, Redis integration, and production-ready logging

## Prerequisites
- Python 3.10+
- Docker and Docker Compose
- PostgreSQL 14 (optional when using Docker)
- Redis 7 (optional when using Docker)

## Local Development
1. Clone the repository and copy environment variables:
   ```bash
   cp .env.example .env
   ```
2. Adjust secrets in `.env` as needed.
3. Launch the stack:
   ```bash
   cd docker
   docker compose up --build
   ```
4. Apply migrations and create a superuser inside the web container:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```
5. The API is available at `http://localhost:8000/` and the interactive docs at `http://localhost:8000/swagger/`.

## Running Tests
Use the helper script to run pytest with coverage:
```bash
./scripts/test.sh
```
When using Docker, execute tests inside the `web` service:
```bash
docker compose exec web pytest
```

## Linting and Formatting
Install the development requirements and run tooling:
```bash
pip install -r requirements-dev.txt
black .
flake8
isort .
```

## Project Structure
```
meshup_backend/
├── apps/                 # Domain apps (auth, users, servers, etc.)
├── config/               # Django project configuration
├── docker/               # Container definitions
├── scripts/              # Helper shell scripts
├── tests/                # Unit and integration tests
├── requirements*.txt     # Dependency lists
└── manage.py
```

## API Documentation
Interactive Swagger UI and Redoc are exposed at:
- `http://localhost:8000/swagger/`
- `http://localhost:8000/redoc/`

## Contributing
1. Fork and clone the repository.
2. Create a feature branch: `git checkout -b feature/awesome-change`.
3. Commit your work following conventional commits.
4. Ensure tests and linters pass.
5. Submit a pull request describing your changes and testing steps.

## License
Released under the BSD License. See the `LICENSE` file when available.
