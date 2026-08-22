# SoulSense - Local Setup, Architecture & Testing Guide

## 1. System Architecture Overview

SoulSense is a production-grade Emotional Intelligence (EQ) assessment and emotional wellbeing platform.

- **Backend**: FastAPI (Python 3.10+) running asynchronously on `http://localhost:8000`.
- **Frontend**: Next.js 14 (React 18, Tailwind CSS, Framer Motion, Zustand, React Query) on `http://localhost:3005`.
- **Database**: SQLite with full WAL mode, automated migrations, and schema enforcement (`data/soulsense.db`).
- **AI Intelligence**: Gemini 2.5 Flash via official `google-genai` SDK for dynamic psychometric question generation with fallback to curated question bank.

---

## 2. Quickstart & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Git

### Backend Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install -r backend/fastapi/requirements.txt

# 2. Initialize database & apply migrations
alembic upgrade head

# 3. Seed Question Categories and Curated Question Bank
python scripts/setup/seed_questions_v2.py

# 4. Start FastAPI Server
python -m uvicorn backend.fastapi.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at:
`http://localhost:8000/docs`

### Frontend Setup
```bash
cd frontend-web
npm install
npm run dev
```

Application UI will be available at:
`http://localhost:3005`

---

## 3. End-to-End User Journey

1. **Registration & Login**:
   - Navigate to `/register`, enter your username, email, and password.
   - Login at `/login` to receive JWT access token.
2. **Onboarding**:
   - Fill in personal preferences, age, and tone preferences at `/welcome`.
3. **Take EQ Assessment**:
   - Navigate to `/exam` and click **Start Assessment**.
   - Respond to 20 dynamically generated Likert scale statements covering Self-Awareness, Self-Regulation, Motivation, Empathy, and Social Skills.
4. **View Detailed Results**:
   - Review your overall EQ score, 5-category score breakdown, and personalized recommendations at `/results`.
5. **Daily Wellbeing Journal**:
   - Add journal reflections with sleep, stress, energy, and screen time metrics at `/journal`.
6. **PDF & Data Export**:
   - Download reports in PDF, JSON, or CSV formats from `/settings` or `/api/v1/export/pdf`.
7. **Secure Logout**:
   - Logout cleanly clears credentials and server-side refresh cookies.

---

## 4. Running Automated Tests

```bash
# Run backend pytest suite
pytest backend/fastapi/tests/unit -v

# Run frontend tests
cd frontend-web
npm test
```
