# Eilių sekimo sistema

Žemėlapis, kuriame matyti, kur šiuo metu yra eilės: check-in / check-out, komentarai, įvertinimai ir analitika.

FastAPI · React (Vite, Leaflet) · MongoDB · Redis · ClickHouse

## Paleidimas

```bash
docker compose up --build
```

| Kas | Adresas |
|---|---|
| Frontend | http://localhost:5173 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| DB jungčių būsena | http://localhost:8000/health |

Seed duomenys:

```bash
docker compose exec backend python seed.py
```

Numatytuosius DB slaptažodžius galima pakeisti nukopijavus `.env.example` į `.env`.

## Struktūra

```
backend/
  seed.py
  app/
    main.py        # FastAPI app, jungtys, routeriai
    config.py      # nustatymai ir konstantos (svoris, cache TTL)
    db/            # mongo.py (+ indeksai), redis.py, clickhouse.py
    auth/          # sessions.py (Redis sesijos), deps.py (CurrentUser, UserOnly, AdminOnly)
    models/        # Pydantic schemos
    routers/       # auth, queues, checkins, comments, reviews, me, reports
    services/      # weight (add_weight), events (track_event), cache, locks
    clickhouse/    # init.sql
frontend/
  src/
    api/           # client.js (fetch + Bearer token), index.js (visi endpoint'ai)
    auth/          # AuthContext
    pages/         # Map, Login, Register, MyQueues, Reports
    components/    # Map/MapView, QueuePanel/QueuePanel
```

## Būsena

Skeletas: visi endpoint'ai aprašyti Swagger'yje, bet grąžina `501`. Kode pažymėta, kas kieno:
`TODO(A)` – eilės, žemėlapis, check-in; `TODO(B)` – komentarai, įvertinimai, ženkleliai, analitika.
