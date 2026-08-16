AI Routing Layer — Dashboard (Next.js)

Quick start:

```bash
cd web/dashboard
npm install
npm run dev
```

Open http://localhost:3000

Notes:
- This scaffold uses Next.js. It is intentionally minimal and intended as a starting point for the dashboard and marketing pages.
- Configure proxying or set API_BASE_URL to point to the backend (default assumes backend at http://localhost:8000).

What I added:
- Global app wrapper and styles (`pages/_app.tsx`, `styles/globals.css`)
- API helper (`lib/api.ts`) that calls `/v1/*` endpoints with a dev key
- Dashboard pages: `/dashboard`, `/dashboard/keys`, `/dashboard/playground`
- Components: `ApiKeyList`, `UsageChart`

Try it:
```bash
cd web/dashboard
npm install
npm run dev
```

The playground posts to `/v1/chat/completions` using the default developer key; run the backend locally or adjust the API proxy if needed.

Docker (run as separate microservice):

Build and run the dashboard alongside the backend using the repository root docker-compose:

```bash
# from repo root
docker compose build dashboard
docker compose up dashboard
```

The dashboard will be available at http://localhost:3000 and proxy `/v1/*` to the `api` service at http://api:8000 inside compose.
