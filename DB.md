# Prisijungimas prie Redis ir ClickHouse

Prieš tai turi veikti `docker compose up`. Numatytieji prisijungimo duomenys: ClickHouse `app` / `app`, DB `queues`. Redis slaptažodžio neturi.

## Redis

Interaktyvi konsolė:

```bash
docker compose exec redis redis-cli
```

Viena komanda be konsolės:

```bash
docker compose exec redis redis-cli DBSIZE
```

Naudingos komandos (raktų schema – `plan.md` §8):

```
SCAN 0 MATCH queue:*:active COUNT 100   # raktų paieška (KEYS * nenaudok)
SMEMBERS queue:<id>:active              # kas dabar stovi eilėje
SCARD queue:<id>:active                 # kiek žmonių eilėje
HGETALL session:<token>                 # sesija (user_id, role)
GET cache:queue:<id>                    # eilės suvestinės cache (JSON)
TTL cache:queue:<id>                    # kiek sekundžių liko iki pabaigos
TYPE <raktas>                           # rakto tipas
```

Visų raktų sąrašas pagal šabloną: `docker compose exec redis redis-cli --scan --pattern 'cache:*'`.

Iš host'o (jei įdiegtas `redis-cli` ar GUI, pvz. RedisInsight): `localhost:6379`.

## ClickHouse

Interaktyvi konsolė:

```bash
docker compose exec clickhouse clickhouse-client -u app --password app -d queues
```

Viena užklausa:

```bash
docker compose exec clickhouse clickhouse-client -u app --password app -d queues \
  -q "SELECT event_type, count() FROM events GROUP BY event_type"
```

Per HTTP (nereikia jokio kliento):

```bash
curl -u app:app "http://localhost:8123/?database=queues" \
  --data-binary "SELECT count() FROM events"
```

Naršyklėje: http://localhost:8123/play (vartotojas `app`, slaptažodis `app`).

Naudingos užklausos (lentelė – `plan.md` §9):

```sql
SHOW TABLES;
DESCRIBE events;
SELECT * FROM events ORDER BY event_time DESC LIMIT 10;
SELECT toDate(event_time) d, count() FROM events
WHERE event_type = 'checkin' GROUP BY d ORDER BY d DESC LIMIT 7;
```

GUI klientams (DBeaver, DataGrip): host `localhost`, HTTP portas `8123` (native – `9000`), DB `queues`.
