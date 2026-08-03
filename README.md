# 📡 Uptime Pulse

**Uptime Pulse** is an automated, real-time website monitoring and alert platform built with **Django**, **Celery**, **Redis**, and **PostgreSQL**. 

It continuously checks endpoint health, measures latency metrics, maintains pre-aggregated performance caches in Redis, and dispatches incident alerts when monitored sites experience downtime.

---

### 🛠️ Tech Stack & Key Technologies

* **Backend Framework:** Django 5 (Python 3.12+)
* **Asynchronous Task Queue:** Celery
* **Periodic Task Scheduler:** Celery Beat
* **Message Broker & Cache:** Redis
* **HTTP Client:** HTTPX (Async/Sync HTTP library)
* **Database:** PostgreSQL 15
* **Containerization:** Docker & Docker Compose
---

## 🏗️ Architecture & System Flow

Uptime Pulse runs as an orchestrated multi-container Docker stack where each service handles a dedicated responsibility to ensure high throughput and non-blocking performance.

### System Workflow

1. **Periodic Trigger:** `celery_beat` queries active monitored sites every minute and dispatches ping tasks into the Redis queue.
2. **Task Execution:** `celery_worker` picks up the task and executes an HTTP health check using `httpx`.
3. **Log & Metric Update:** The check result and latency metrics are saved to PostgreSQL (`CheckLog`) and cached in Redis.
4. **Failure Threshold Evaluation:** If consecutive checks fail beyond the configured threshold, an `IncidentReport` is generated.
5. **Alert Notification:** The worker triggers an asynchronous email task to notify administrators of downtime.

### Service Responsibilities

* **Django Web API (`web`)**: Hosts the admin interface, manages site configuration models, and serves metric aggregation endpoints.
* **Celery Worker (`celery_worker`)**: Asynchronously executes site health checks using `httpx`, evaluates failure thresholds, updates Redis metrics caches, and sends alert emails.
* **Celery Beat (`celery_beat`)**: Periodically schedules background ping jobs across all active monitored endpoints.
* **Redis (`redis`)**: Serves as the high-speed task broker for Celery and stores pre-aggregated performance metrics for rapid dashboard retrieval.
* **PostgreSQL (`db`)**: Primary relational database storing site definitions (`MonitoredSite`), ping history (`CheckLog`), and failure tracking (`IncidentReport`).

---

## ⚡ Key Engineering Features

* **Non-Blocking Architecture:** Offloads HTTP pings to Celery workers so web request threads never freeze waiting for third-party timeouts.
* **Smart Alerting & Deduplication:** Requires consecutive failed checks before triggering an alert, preventing false alarms and duplicate notification spam.
* **Redis Performance Caching:** Pre-aggregates 24-hour site metrics (uptime %, average response time) in Redis to keep dashboard database queries fast.
* **Robust Docker Health Checks:** Uses `service_healthy` conditions in Docker Compose so workers wait for PostgreSQL and Redis to fully initialize before connecting.

---

## 🚀 Quick Start & Environment Setup

### 1. Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* Git.

### 2. Configure Environment Variables
Create a `.env` file in the project root directory:

```env
# Django Settings
SECRET_KEY=django-insecure-change-this-key-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# PostgreSQL Settings
POSTGRES_DB=uptimepulse_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_HOST=db
DATABASE_PORT=5432

# Redis & Celery Settings
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email Delivery Settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=Uptime Pulse Alert <alerts@uptimepulse.local>
ALERT_RECIPIENT_EMAIL=admin@uptimepulse.local

```
---
#Spin Up the Containers
Build and start all services in detached mode:

docker compose up -d --build

#Run Migrations & Create Admin User
##Initialize the database tables and set up your administrator account:

# Apply database migrations
docker compose exec web python manage.py migrate

# Create admin user
docker compose exec web python manage.py createsuperuser

## 🧪 Verification & Testing

### Access Points

* **Django Admin Dashboard:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

### End-to-End Testing Walkthrough

1. **Log in:** Open the Django Admin panel using your superuser credentials.
2. **Add a Monitored Site:** Create a new site entry:
   * **URL:** `https://httpbin.org/status/200`
   * **Check Interval:** `60` seconds
   * **Expected Status Code:** `200`
3. **Verify Active Checks:** Stream the Celery worker logs to see background pings executing:
   ```bash
   docker compose logs celery_worker -f

## 🛠️ Essential Operational Commands

### Monitoring Logs
```bash
# View live logs for all running services
docker compose logs -f

# Tail logs specifically for Celery workers
docker compose logs celery_worker --tail 50 -f

# Tail logs specifically for Celery Beat scheduler
docker compose logs celery_beat --tail 50 -f

#Container Management
# Check service health status
docker compose ps

# Restart worker (apply Python code changes to background tasks)
docker compose restart celery_worker

# Stop all containers
docker compose down

#Project Structure
├── config/                  # Django project configuration & Celery app initialization
├── monitoring/              # Primary application module
│   ├── tasks.py             # Celery background tasks (pings, cache updates, emails)
│   ├── models.py            # MonitoredSite, CheckLog, and IncidentReport schema definitions
│   ├── views.py             # API endpoints and metric aggregations
│   ├── utils.py             # Redis caching logic and status evaluators
│   └── admin.py             # Custom Django Admin view configurations
├── docker-compose.yml       # Container service declarations and health dependencies
├── Dockerfile               # Python environment setup
├── requirements.txt         # Dependencies (Django, Celery, Redis, HTTPX)
└── README.md                # Project documentation