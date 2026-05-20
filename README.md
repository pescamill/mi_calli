# mi_calli

A containerized property management backend built with Python, FastAPI, PostgreSQL, and Docker Compose.

Designed as a learning-focused but production-style backend project, with future plans for authentication, property management, and cloud deployment on AWS.

---

## Current Features

- FastAPI backend
- PostgreSQL database
- SQLAlchemy ORM integration
- Docker Compose environment
- NGINX reverse proxy
- Swagger/OpenAPI documentation
- Database health check endpoint
- User model and persistence
- User CRUD API endpoints

---

## Architecture

```text
NGINX
  ↓
FastAPI
  ↓
PostgreSQL
```

---

## Local Setup

### 1. Build and run the stack

```bash
docker compose up --build
```

---

### 2. Open the application

Frontend:

```text
http://localhost/
```

Swagger API docs:

```text
http://localhost:8000/docs
```

ReDoc documentation:

```text
http://localhost:8000/redoc
```

---

## API Endpoints

### Health Check

```http
GET /health/db
```

Verifies PostgreSQL connectivity.

---

### Setup Database Tables

```http
POST /setup
```

Creates missing database tables using SQLAlchemy metadata.

---

### Users

```http
POST /users
GET /users
```

Current user model fields:

- id
- username
- password_hash
- role
- created_at

---

## Docker Compose Commands

Start services:

```bash
docker compose up --build
```

Stop services:

```bash
docker compose down
```

Reset database volume completely:

```bash
docker compose down -v
```

Rebuild containers only:

```bash
docker compose build
```

---

## Project Structure

```text
backend/
└── app/
    ├── api/
    ├── db/
    ├── models/
    ├── schemas/
    └── main.py
```

---

## Planned Features

- JWT authentication
- Password hashing
- Property / house management
- Room management
- Rent tracking
- Alembic migrations
- React frontend dashboard
- AWS EC2 deployment
- HTTPS + domain configuration

---

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker Compose
- NGINX
