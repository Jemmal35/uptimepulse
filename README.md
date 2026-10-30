# 📡 Uptime Pulse

**Uptime Pulse** is an automated website monitoring and alerting platform built with **Django**, **Celery**, **Redis**, and **PostgreSQL**, with **AI-assisted incident analysis** powered by the Gemini API.

It continuously checks endpoint health, measures latency, keeps pre-aggregated performance metrics in Redis, and when a site goes down it generates an incident report with a plain-language diagnosis and recommended actions, then emails the owner.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Django 5 (Python 3.12+), Django REST Framework |
| Task queue / scheduler | Celery + Celery Beat |
| Broker & cache | Redis |
| HTTP client | HTTPX |
| Database | PostgreSQL 15 |
| AI analysis | Google Gemini API (configurable model) |
| Containerization | Docker & Docker Compose |

---

## 🏗️ Architecture & System Flow

Uptime Pulse runs as a multi-container Docker stack. Each service has one responsibility, so health checks never block the web API.

### System workflow

1. **Periodic trigger:** `celery_beat` queries active monitored sites every minute and queues ping tasks in Redis.
2. **Task execution:** `celery_worker` picks up each task and runs an HTTP health check with `httpx`.
3. **Log & metric update:** The result and latency are saved to PostgreSQL (`CheckLog`) and the Redis metrics cache is refreshed.
4. **Failure threshold:** After 3 consecutive failed checks, an `IncidentReport` is created (one per failure streak, so an ongoing outage does not spam alerts).
5. **AI analysis:** A separate task sends the site's recent check history to the Gemini API and stores the returned diagnosis on the `IncidentReport`.
6. **Alert notification:** An email task notifies the site owner with the analysis. If the AI step fails or is disabled, a rule-based alert is sent instead, so downtime alerts are never delayed by an AI outage.

### Service responsibilities

* **Django web API (`web`)**: Admin interface, site configuration, metrics and incident endpoints.
* **Celery worker (`celery_worker`)**: Runs health checks, evaluates failure thresholds, updates Redis caches, calls the AI service, and sends alert emails.
* **Celery Beat (`celery_beat`)**: Schedules the background ping jobs.
* **Redis (`redis`)**: Celery broker and store for pre-aggregated metrics.
* **PostgreSQL (`db`)**: Stores sites (`MonitoredSite`), ping history (`CheckLog`), and incidents (`IncidentReport`).

---

## ⚡ Key Engineering Features

* **Non-blocking architecture:** HTTP pings run in Celery workers, so web requests never wait on third-party timeouts.
* **Smart alerting & deduplication:** Requires 3 consecutive failures, and creates only one incident per failure streak. A site can alert again after it recovers and fails again.
* **AI-assisted incident analysis:** Summarizes recent check data into a likely cause, confidence estimate, and recommended actions.
* **Graceful degradation:** AI calls have a timeout and targeted retries (rate limits and server errors only). A wrong key or retired model name skips retries and falls back to the rule-based alert.
* **Honest labeling:** Each incident records `is_ai_generated`. Fallback incidents never show a made-up confidence score.
* **Redis performance caching:** Pre-aggregates 24-hour metrics (uptime %, average response time) to keep dashboard queries fast.
* **Docker health checks:** `service_healthy` conditions make workers wait for PostgreSQL and Redis before connecting.

---

## 🤖 AI Incident Analysis

When an incident opens, the worker sends the AI service a compact JSON summary: the site URL, expected status code, timeout setting, and its last 30 check results (status, latency, error message). The system prompt instructs the model to analyze **only** the data provided and to report low confidence when the data is insufficient.

The model returns structured JSON, which is validated and clamped before it is saved:

| Field | Stored in `IncidentReport` |
|---|---|
| Short summary | `summary` |
| Likely cause | `possible_cause` |
| Confidence (0 to 1) | `confidence_score` |
| Up to 4 suggested actions | `recommended_action` |

**Design notes**

* The AI is advisory only. It reads data and writes text; it never takes actions.
* Exactly one AI call is made per incident, not per check, which keeps usage within free-tier limits.
* Failure handling: network errors, `429`, and `5xx` responses are retried; `400/403/404` (bad key or retired model) are not.

### Sample alert email

```text
AI-assisted incident analysis
-----------------------------
Site Name:          HTTPBin Delay Test (Timeout)
Site URL:           https://httpbin.org/delay/6
Summary:            The monitored website is consistently failing health checks
                    due to request timeouts. Every recorded check shows latencies
                    exceeding 5.5 seconds against a 5-second timeout threshold.
Possible Cause:     The target endpoint enforces a 6-second delay, which exceeds
                    the configured 5-second check timeout threshold.
Confidence:         99% (AI estimate)
Recommended Action:
- Increase the health check timeout configuration to greater than 6 seconds.
- Verify the expected delay setting of the monitored endpoint.
```

---

## 🔌 API Endpoints

All endpoints require an authenticated user, and users only ever see their own sites and incidents.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/incidents/` | All incidents across the user's sites, newest first |
| `GET` | `/api/sites/<site_id>/incidents/` | Incidents for one site (404 if the site is not yours) |

> Adjust the `/api/` prefix to match how `monitoring/urls.py` is included in your project.

### Example response

```json
[
  {
    "id": "8fc95e8b-d1e7-49b6-802b-0d25605b06d5",
    "site_name": "HTTPBin Delay Test (Timeout)",
    "detected_at": "2026-10-30T07:24:54Z",
    "status_code": null,
    "error_message": "Request timed out after 5 seconds",
    "summary": "The monitored website is consistently failing health checks due to request timeouts. Every recorded check shows latencies exceeding 5.5 seconds against a 5-second timeout threshold.",
    "possible_cause": "The target endpoint enforces a 6-second delay, which exceeds the configured 5-second check timeout threshold.",
    "confidence_score": 0.99,
    "recommended_actions": [
      "Increase the health check timeout configuration to greater than 6 seconds.",
      "Verify the expected delay setting of the monitored endpoint."
    ],
    "is_ai_generated": true,
    "created_at": "2026-10-30T07:24:54Z"
  }
]
```

`confidence_score` is `null` when `is_ai_generated` is `false`, because rule-based fallback incidents have no real confidence estimate.

---

## 🚀 Quick Start

### 1. Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
* Git
* *(Optional)* a free Gemini API key from [Google AI Studio](https://aistudio.google.com/). Without one, the app still works and sends rule-based alerts.

### 2. Configure environment variables

Create a `.env` file in the project root. **Never commit this file.** Add `.env` to `.gitignore` and share a `.env.example` with placeholder values instead.

```env
# Django
SECRET_KEY=change-this-key-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# PostgreSQL
POSTGRES_DB=uptimepulse_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-this-password
DATABASE_HOST=db
DATABASE_PORT=5432

# Redis & Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email (console backend prints emails in the worker log)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=Uptime Pulse Alert <alerts@uptimepulse.local>

# AI analysis (Gemini)
GEMINI_API_KEY=your-key-here
AI_MODEL=gemini-3.5-flash-lite
AI_ANALYSIS_ENABLED=True
```

> **Model names change.** Google retires models regularly. If incidents fall back to rule-based alerts and the worker log shows `Gemini returned HTTP 404`, set `AI_MODEL` to a currently available Flash or Flash-Lite model from AI Studio.

#### Sending real emails (optional)

To send real emails through Gmail, enable 2-Step Verification, create an **app password**, and use:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-address@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Uptime Pulse Alert <your-address@gmail.com>
```

### 3. Start the containers

```bash
docker compose up -d --build
```

> After editing `.env`, use `docker compose up -d --force-recreate`. A plain `restart` does not reload environment variables.

### 4. Run migrations and create an admin user

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

---

## 🧪 Verification & Testing

### Access points

* **Django Admin:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

### End-to-end walkthrough

1. **Log in** to the Django Admin with your superuser credentials.
2. **Add a monitored site** that should fail:
   * **URL:** `https://httpbin.org/status/500`
   * **Check interval:** `60` seconds
   * **Expected status code:** `200`
3. **Watch the worker:**

   ```bash
   docker compose logs celery_worker -f
   ```

4. After about 3 minutes (3 consecutive failures) you should see the analysis task followed by the alert task, and the email printed in the log.

### Useful test sites

| Name | URL | Expected status | Tests |
|---|---|---|---|
| 500 error | `https://httpbin.org/status/500` | `200` | Wrong status code |
| Timeout | `https://httpbin.org/delay/15` | `200` | Request timeout |
| Dead domain | `https://this-domain-does-not-exist-12345.com` | `200` | DNS / network error |
| Healthy | `https://httpbin.org/status/200` | `200` | No incident |

### Retesting after an incident

An incident stays "open" until the site has a successful check. To retrigger on a site that is still failing, delete its incident reports:

```bash
docker compose exec web python manage.py shell -c "from monitoring.models import IncidentReport; print(IncidentReport.objects.all().delete())"
```

---

## 🛠️ Troubleshooting

| Symptom | Likely cause |
|---|---|
| Email says "Rule-based alert (AI analysis unavailable)" | AI call failed or is disabled. Check `docker compose logs celery_worker` for `AI analysis failed` or `AI analysis skipped`. |
| `Gemini returned HTTP 404` | Model name retired. Update `AI_MODEL`. |
| `Gemini returned HTTP 400/403` | Invalid API key. Create a new one. |
| `Gemini returned HTTP 429` | Free-tier rate limit. Retries handle this; wait a few minutes if it persists. |
| Container ignores `.env` changes | Run `docker compose up -d --force-recreate` (not `restart`). |
| Postman: `socket hang up` | Use `http://` (not `https://`) on `localhost:8000`, and check `docker compose logs web` for a startup error. |

---

## 🧰 Operational Commands

```bash
# Live logs for all services
docker compose logs -f

# Worker or scheduler logs
docker compose logs celery_worker --tail 50 -f
docker compose logs celery_beat --tail 50 -f

# Service health
docker compose ps

# Restart the worker after Python code changes
docker compose restart celery_worker

# Stop everything
docker compose down
```

---

## 🔒 Security Notes

* Change `SECRET_KEY` and the PostgreSQL password, and set `DEBUG=False` before any real deployment.
* Keep API keys and email app passwords only in `.env`. If one is ever exposed, revoke it immediately and create a new one.
* The AI service receives only check metadata (URL, status codes, latencies, error messages), never response bodies or user data.

---

## 📁 Project Structure

```text
├── config/                  # Django project settings & Celery app initialization
├── monitoring/              # Primary application module
│   ├── tasks.py             # Celery tasks: pings, incident handling, AI analysis, alert emails
│   ├── ai.py                # Gemini client, prompt, response validation
│   ├── models.py            # MonitoredSite, CheckLog, IncidentReport
│   ├── serializers.py       # DRF serializers (incident API output)
│   ├── views.py             # API endpoints and metric aggregations
│   ├── utils.py             # Redis caching logic and status evaluators
│   └── admin.py             # Django Admin configuration
├── docker-compose.yml       # Services and health-check dependencies
├── Dockerfile               # Python environment setup
├── requirements.txt         # Dependencies (Django, DRF, Celery, Redis, HTTPX)
└── README.md                # Project documentation
```