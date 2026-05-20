# mi_calli

A minimal FastAPI boilerplate with PostgreSQL, NGINX, and Docker Compose, designed for easy local development and future VPS deployment.

## Local setup

1. Build and run the stack:

   docker compose up --build

2. Open the frontend in your browser:

   http://localhost/

3. Test the backend API proxy:

   http://localhost/api/

## Docker compose commands

- Start services: `docker compose up --build`
- Stop services: `docker compose down`
- Rebuild only: `docker compose build`

## Test the app

- Open `http://localhost/` to see the React placeholder.
- Open `http://localhost/api/` to test the backend.

Expected API response:

```json
{"message": "mi_calli running"}
```
