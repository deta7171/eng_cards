# eng_cards

Карточки для изучения английских слов: spaced repetition (FSRS), синхронизация
прогресса через Google-аккаунт, автоматический перевод и подбор слов по темам.

Дизайн и контракты: [`docs/db_schema.sql`](docs/db_schema.sql), [`docs/api_contract.md`](docs/api_contract.md).

## Стек

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy + Alembic, `fsrs` для алгоритма повторения
- **Frontend**: React (Vite + TS), React Router, React Query
- **Auth**: Google OAuth 2.0 → своя JWT-сессия в httpOnly cookie
- **Перевод**: MyMemory API (бесплатно) · **Словарь**: Free Dictionary API (бесплатно)
- **Деплой**: Render (backend) + Neon (Postgres) + Vercel (frontend), все на бесплатных тарифах

## Локальный запуск

### 1. База данных + backend через Docker

```bash
cp backend/.env.example backend/.env
# впиши GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (console.cloud.google.com) и JWT_SECRET
docker compose up --build
```

Backend поднимется на `http://localhost:8000`, миграции применяются автоматически при старте.

### 2. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Откроется на `http://localhost:5173`.

## Google OAuth (для локальной разработки)

1. В [Google Cloud Console](https://console.cloud.google.com/apis/credentials) создать OAuth 2.0 Client ID (тип: Web application).
2. Authorized redirect URI: `http://localhost:8000/api/auth/google/callback`.
3. Client ID/Secret положить в `backend/.env`.

## Деплой (бесплатные тарифы)

1. **Neon** — создать Postgres-проект, скопировать connection string в `DATABASE_URL`.
2. **Render** — новый Web Service из `render.yaml` (или вручную из `backend/Dockerfile`), заполнить env vars.
3. **Vercel** — импортировать `frontend/` как проект, `VITE_API_URL` → адрес backend на Render.
4. В Google Console добавить продовые redirect URI (`https://<render-app>.onrender.com/api/auth/google/callback`) и обновить `FRONTEND_URL`/`GOOGLE_REDIRECT_URI` в Render.

Примечание: бесплатный план Render "засыпает" после ~15 мин простоя — первый запрос после этого грузится 20-50 сек.

## Структура

```
backend/    FastAPI-приложение, Alembic-миграции
frontend/   React SPA
docs/       схема БД и контракт API (источник истины при разработке)
```
