# Eilių sekimo sistema „Low IQueue“

Sistema leidžia vartotojams žemėlapyje matyti, kur šiuo metu yra eilės. Vartotojai registruoja naujas eiles, pasižymi stovintys eilėje (check-in / check-out), rašo komentarus ir vertina eiles. Eilės ryškumas heatmape priklauso nuo jos „svorio“: svoris didėja su kiekvienu veiksmu ir laikui bėgant mažėja. Sistema kaupia įvykius ir pateikia analitines ataskaitas.

---

## 1. Technologijos

| Komponentas | Technologija |
|---|---|
| Backend | Python, FastAPI |
| API dokumentacija | OpenAPI / Swagger (`/docs`, `/redoc`) |
| Frontend | React (Vite), react-leaflet, leaflet.heat, OpenStreetMap |
| Operacinė DB | MongoDB (`2dsphere` geoindeksai) |
| Cache, sesijos, aktyvūs check-in, užraktai, rate limit | Redis |
| Analitika | ClickHouse |
| Paleidimas | Docker Compose |
| Versijų kontrolė | Git |

Bibliotekos: `motor`, `redis.asyncio`, `clickhouse-connect`, `pydantic`, `passlib[bcrypt]`, `faker`.

---

## 2. Architektūra

```
React + Leaflet (frontend)
      │  HTTP / JSON (Authorization: Bearer <session_token>)
      ▼
FastAPI (backend)
      ├── MongoDB     – vartotojai, eilės, check-in, komentarai, įvertinimai
      ├── Redis       – sesijos, aktyvūs check-in, cache, užraktai, rate limit
      └── ClickHouse  – įvykiai ir ataskaitos
```

---

## 3. Reikalavimų atitikimas

| Reikalavimas | Įgyvendinimas |
|---|---|
| 1. Backend + frontend per API, API dokumentacija | FastAPI + React, Swagger |
| 2. Nereliacinė operacinė DB | MongoDB su geoužklausomis |
| 3. Didelis duomenų modelis | 6 kolekcijos (likai įterpti į komentarus), svorio blėsimo modelis, ženkleliai, unikalumo ir kitos verslo taisyklės |
| 4. Cache sudėtingiems endpoint'ams | Redis: žemėlapio duomenys, eilės suvestinė, komentarai su ženkleliais, ataskaitos |
| 5. Laikina saugykla, sinchronizacija | Redis: sesijos, aktyvūs check-in, užraktas check-in metu, svorio „antispam“ raktai, komentarų rate limit |
| 6. Git | Git repozitorija |
| 7.1 Analitika | ClickHouse įvykiai ir ataskaitos |

---

## 4. Rolės

| Rolė | Teisės |
|---|---|
| svečias | Matyti žemėlapį, eilių informaciją ir komentarus |
| `user` | Kurti eiles, check-in / check-out, komentuoti, trinti savo komentarus, vertinti, likinti komentarus |
| `admin` | Peržiūrėti ataskaitas (eilių kurti, pasižymėti, komentuoti ir vertinti negali) |

---

## 5. Funkciniai reikalavimai

- **FR1.** Vartotojai registruojasi (vardas, pavardė, gimimo metai, el. paštas, slaptažodis) ir prisijungia. Po registracijos vartotojas iškart prisijungęs. Sesija saugoma Redis.
- **FR2.** Vartotojas registruoja naują eilę: nurodo pavadinimą ir vietą žemėlapyje.
- **FR3.** Pagrindiniame puslapyje rodomas žemėlapis, jį mato ir neprisijungę vartotojai:
  - toli atitolinus rodomas heatmapas pagal eilių svorį;
  - priartinus rodomi atskirų eilių pinai;
  - eilė, kurios svoris nukrito iki 0, žemėlapyje nerodoma (bet lieka duomenų bazėje).
- **FR4.** Eilės svoris didėja su kiekvienu veiksmu (sukūrimas, check-in, komentaras, įvertinimas) ir tolygiai mažėja laikui bėgant (žr. 6 skyrių).
- **FR5.** Paspaudus ant pino rodoma eilės informacija:
  - pavadinimas;
  - vidutinis įvertinimas ir įvertinimų skaičius;
  - kiek žmonių šiuo metu stovi eilėje;
  - vidutinis laukimo laikas ir matavimų skaičius;
  - naujausi komentarai su autoriaus ženkleliu ir likų skaičiumi.
- **FR6.** Check-in ir check-out:
  - vartotojas gali pasižymėti eilėje (check-in) ir iš jos išeiti (check-out);
  - vartotojas gali būti pasižymėjęs keliose eilėse vienu metu, bet toje pačioje eilėje stovėti galima tik vieną kartą (po check-out iš naujo pasižymėti negalima);
  - jei check-out nepaspaustas, laukimo laikas neskaičiuojamas.
- **FR7.** Vartotojas gali rašyti komentarus po eile ir ištrinti savo komentarus. Per minutę galima parašyti ne daugiau kaip 5 komentarus (kitaip 429). Kito vartotojo komentaro ištrinti negalima (403).
- **FR8.** Vartotojas gali įvertinti eilę (1–5) tik vieną kartą. Įvertinimo pakeisti negalima.
- **FR9.** Vartotojas gali palikinti komentarą tik vieną kartą ir atšaukti savo liką. Savo komentaro likinti negalima.
- **FR10.** Vartotojas gauna ženklelį pagal tai, kiek iš viso likų surinko jo komentarai. Ženklelis rodomas prie kiekvieno komentaro.
- **FR11.** *(Jei spėsim; neįgyvendinta)* Puslapis „Mano eilės“: visos eilės, kuriose vartotojas stovėjo, su stovėjimo trukme (jei žinoma), savo įvertinimu ir komentarais. Šiuo metu `/me/queues` grąžina 501, o nuorodos meniu nėra.
- **FR12.** Sistema kaupia įvykius ClickHouse: registraciją, prisijungimą, eilės sukūrimą, pino paspaudimą (eilės peržiūrą), check-in, check-out, komentarą, įvertinimą, komentaro liką.
- **FR13.** Administratorius mato ataskaitas (žr. 9 skyrių).

---

## 6. Eilės svoris

Taikomas **tiesinis blėsimas**: svoris pasiekia tikslų nulį, todėl lengva nustatyti, kada eilė dingsta iš žemėlapio.

| Veiksmas | Taškai |
|---|---|
| Eilės sukūrimas | +60 |
| Check-in | +5 |
| Įvertinimas | +10 |
| Komentaras | +7 |

- Blėsimas: **k = 1 taškas per minutę**.
- Maksimalus svoris: **360**.

**Dabartinis svoris skaičiuojamas skaitymo metu:**

```
svoris_dabar = max(0, weight − k · (dabar − weight_updated_at))
```

**Kiekvieno veiksmo metu** eilės laukai atnaujinami vienu atominiu MongoDB `update` su aggregation pipeline, todėl užraktas nereikalingas:

```
weight            = min(360, svoris_dabar + taškai)
weight_updated_at = dabar
expires_at        = dabar + weight / k
```

Laukas `expires_at` nurodo, kada svoris pasieks 0. Tad žemėlapio užklausa paprasta: `expires_at > dabar`.

**Apsauga nuo „pumpavimo“.** Tas pats vartotojas tos pačios rūšies veiksmu tai pačiai eilei svorio prideda ne dažniau nei kartą per 15 minučių. Tai tikrinama Redis raktu `weight:{queue_id}:{user_id}:{action}` (`SET NX EX 900`).

**Heatmapo intensyvumas** = `svoris_dabar / 360`.

---

## 7. Duomenų modelis (MongoDB)

### users
```json
{
  "_id": "ObjectId",
  "email": "string (unique)",
  "password_hash": "string",
  "first_name": "string",
  "last_name": "string",
  "birth_year": 1998,
  "role": "user | admin",
  "total_likes": 57,
  "created_at": "datetime"
}
```

### badges
```json
{
  "_id": "ObjectId",
  "name": "Sidabrinis eilininkas",
  "min_likes": 50,
  "icon": "silver"
}
```
Ženkleliai įrašomi per `seed.py`. Pavyzdiniai lygiai: 10 (bronzinis), 50 (sidabrinis), 200 (auksinis), 1000 („Eilių legenda“). Vartotojo ženklelis yra aukščiausias, kurio `min_likes <= users.total_likes`.

### queues
```json
{
  "_id": "ObjectId",
  "title": "Regitra, Liepkalnio g.",
  "location": { "type": "Point", "coordinates": [25.30, 54.67] },
  "created_by": "ObjectId",
  "created_at": "datetime",
  "weight": 42.0,
  "weight_updated_at": "datetime",
  "expires_at": "datetime",
  "rating_sum": 34,
  "rating_count": 9,
  "comment_count": 15
}
```

### checkins
```json
{
  "_id": "ObjectId",
  "queue_id": "ObjectId",
  "user_id": "ObjectId",
  "queue_title": "Regitra, Liepkalnio g.",
  "checked_in_at": "datetime",
  "checked_out_at": "datetime | null"
}
```
- Aktyvus check-in: `checked_out_at == null`.
- Trukmė skaičiuojama tik kai `checked_out_at != null`.
- `queue_title` yra kopija puslapiui „Mano eilės“.

### comments
```json
{
  "_id": "ObjectId",
  "queue_id": "ObjectId",
  "user_id": "ObjectId",
  "text": "string",
  "likes_count": 4,
  "liked_by": ["ObjectId"],
  "created_at": "datetime"
}
```
- `liked_by` – palikinusių vartotojų id, įterpti į komentarą (embedding). Likas ir jo atšaukimas yra vienas atominis update viename dokumente, o ištrynus komentarą jo likai dingsta kartu. `likes_count` laikomas šalia, kad nereikėtų skaičiuoti masyvo.
- `liked_by` neišeina iš backend'o: `CommentOut` jo neturi, todėl jis nepatenka nei į atsakymą, nei į cache. Komentarų sąraše jis net netraukiamas iš Mongo (projekcija), nes gali būti tūkstančiai id.
- `liked_by_me` skaičiuojamas kiekvienai užklausai atskirai (`distinct` pagal puslapio komentarų `_id` ir `liked_by`), nes cache'intas puslapis bendras visiems vartotojams.
- Like'o laikas Mongo nesaugomas – jis yra ClickHouse įvykyje `comment_liked`.

### reviews
```json
{
  "_id": "ObjectId",
  "queue_id": "ObjectId",
  "user_id": "ObjectId",
  "score": 4,
  "created_at": "datetime"
}
```

### Indeksai
- `users.email` (unique)
- `queues`: `{ location: "2dsphere", expires_at: 1 }`, `created_by`
- `checkins`: `{ user_id: 1, checked_in_at: -1 }`, `{ queue_id: 1, user_id: 1, checked_out_at: 1 }`
- `comments`: `{ queue_id: 1, created_at: -1 }`
- `reviews`: `{ queue_id: 1, user_id: 1 }` (unique)

### Verslo taisyklės
- **Vienas įvertinimas:** unikalus indeksas, antras bandymas grąžina 409. Įvertinimas didina `rating_sum` ir `rating_count`.
- **Vienas likas:** atominis update su filtru `liked_by: { $ne: user_id }` (`$push` + `$inc`), antras bandymas grąžina 409. Likas didina `comments.likes_count` ir autoriaus `users.total_likes`, atšaukimas juos sumažina.
- **Savo komentaro likinti negalima:** tame pačiame update filtre (`user_id: { $ne: user_id }`), 400.
- **Liko atšaukimas:** atominis `$pull` + `$inc` su filtru `liked_by: user_id`; jei liko nėra, grąžinama 404.
- **Komentaro trynimas:** trinamas komentaras (likai įterpti, todėl dingsta kartu), mažinamas `queues.comment_count`, o autoriaus `total_likes` sumažinamas komentaro likų skaičiumi. Eilės svoris nemažinamas.

---

## 8. Redis

| Raktas | Tipas | TTL | Paskirtis |
|---|---|---|---|
| `session:{token}` | Hash (`user_id`, `role`) | 24 h (pratęsiama) | Sesija |
| `queue:{id}:active` | Set (`user_id`) | iki eilės `expires_at` | Kas dabar stovi eilėje |
| `lock:checkin:{user_id}:{queue_id}` | String (`SET NX PX 3000`) | 3 s | Apsauga nuo dvigubo check-in paspaudimo |
| `weight:{queue_id}:{user_id}:{action}` | String | 15 min | Svorio pumpavimo apsauga |
| `rl:comment:{user_id}` | Counter | 1 min | Ne daugiau 5 komentarų per minutę |
| `cache:map:{zoom}:{south}:{west}:{north}:{east}` | String (JSON) | 30 s | Žemėlapio taškai ir svoriai (bbox suapvalintas iki tinklelio) |
| `cache:queue:{id}` | String (JSON) | 30 s | Eilės suvestinė (įvertinimas, žmonių skaičius, vid. laukimas) |
| `cache:queue:{id}:comments:{page}` | String (JSON) | 5 s | Komentarai su ženkleliais (be `liked_by_me`) |
| `cache:badges` | String (JSON) | 1 h | Ženklelių lygiai |
| `cache:report:{name}:{params}` | String (JSON) | 10 min | Ataskaitos |

**Žmonių skaičius eilėje:** `SCARD queue:{id}:active`. Kiekvieną kartą atnaujinus eilės svorį, rinkiniui nustatomas `EXPIREAT <expires_at>`, todėl eilei dingus iš žemėlapio dingsta ir jos aktyvių žmonių rinkinys.

**Žemėlapio cache raktas:** `bbox` suapvalinamas iki tinklelio (langelis `360 / 2^zoom` laipsnių), kad skirtingi vartotojai, žiūrintys į tą pačią vietą, naudotų tą patį raktą.

**Žemėlapio užklausa:** `expires_at > dabar` ir `$geoWithin` su bbox kaip GeoJSON poligonu (`$box` nenaudoja 2dsphere indekso). Poligono kraštinės tankinamos kas 1°, kad sektų platumą. Labai atitolinus (bbox platesnis nei 90°) geo filtras nenaudojamas, o bbox tikrinamas backend'e.

**Eilės suvestinė:** bendra dalis imama iš `cache:queue:{id}`, o prisijungusio vartotojo būsena (ar jis eilėje: `SISMEMBER`; ar jau stovėjo šioje eilėje: `has_waited`; ar jau įvertino: `my_score`) pridedama kiekvienai užklausai atskirai. Cache'e laikomi pradiniai `weight` ir `weight_updated_at`, o dabartinis svoris perskaičiuojamas kiekvienai užklausai.

**Cache invalidavimas:** po check-in, check-out, įvertinimo, komentaro sukūrimo ar ištrynimo trinamas `cache:queue:{id}` ir pirmas komentarų puslapis. Po liko ar jo atšaukimo trinamas tik pirmas komentarų puslapis. Žemėlapio cache tiesiog pasibaigia po 30 s.

**Check-in eiga:**
1. `SET lock:checkin:{user}:{queue} NX PX 3000`. Jei nepavyko, grąžinama 409. Užraktą atlaisvina tik jį paėmęs (Lua skriptas lygina reikšmę).
2. Jei eilės nėra, grąžinama 404. Jei ji nematoma (`expires_at <= dabar`), grąžinama 409.
3. Jei `SISMEMBER queue:{id}:active user` grąžina taip, grąžinama 409. Jei `checkins` jau yra šio vartotojo įrašas šiai eilei (jau stovėjo), irgi 409.
4. Sukuriamas `checkins` įrašas ir vienoje transakcijoje vykdoma `SADD queue:{id}:active user`, `EXPIREAT … NX` (naujam rinkiniui) ir `EXPIREAT … GT` (pratęsia esamą).
5. Jei `weight:{queue}:{user}:checkin` nustatomas sėkmingai, pridedamas svoris.
6. Trinamas `cache:queue:{id}`, siunčiamas `checkin` įvykis, užraktas atlaisvinamas.

**Check-out eiga:**
1. Vykdomas `SREM queue:{id}:active user`. Jei grąžina 0 (vartotojo nėra), grąžinama 409. `SREM` atominis, todėl dvigubas paspaudimas antrą kartą gauna 409 ir užraktas nereikalingas.
2. Paskutiniam atviram vartotojo check-in toje eilėje įrašomas `checked_out_at`. Jei atviro įrašo nėra (Redis ir MongoDB išsiskyrė), grąžinama 409.
3. Trinamas `cache:queue:{id}`, siunčiamas `checkout` įvykis su `duration_sec`.

**Žinomas apribojimas:** jei vartotojas nepaspaudžia check-out, jis skaičiuojamas tarp eilėje stovinčių, kol eilė dingsta iš žemėlapio.

---

## 9. ClickHouse

### Lentelė
```sql
CREATE TABLE events (
    event_time    DateTime,
    event_type    LowCardinality(String),  -- register, login, queue_created, queue_view, checkin,
                                           -- checkout, comment_created, review_created, comment_liked
    user_id       String,
    user_age      UInt8,
    queue_id      String,
    lat           Float64,
    lng           Float64,
    score         UInt8,                   -- įvertinimas
    duration_sec  UInt32                   -- tik checkout
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, event_time);
```
Įvykiai rašomi su `async_insert = 1` (`wait_for_async_insert = 0`), kad ClickHouse pats grupuotų smulkius įrašus. `track_event` neblokuoja užklausos: įrašas vykdomas fone (timeout 5 s, ne daugiau 1000 laukiančių), o klaidos tik įrašomos į logą. Jei `user_age` neperduotas, jis apskaičiuojamas iš vartotojo `birth_year`. Svečio `queue_view` įvykis turi tuščią `user_id`.

Ataskaitose dienos, savaitės, savaitės dienos ir valandos skaičiuojamos laiko juostoje `Europe/Vilnius`. Periodų ataskaitose tušti periodai užpildomi nuliais (`WITH FILL`).

### Ataskaitos

| Ataskaita | Šaltinis |
|---|---|
| Nauji vartotojai ir eilės per dieną, savaitę ar mėnesį | `register`, `queue_created` |
| Check-in skaičius per periodą | `checkin` |
| Vidutinis laukimo laikas pagal savaitės dieną ir valandą (visoms arba vienai eilei) | `checkout`, `duration_sec` |
| Populiariausios eilės pagal peržiūras ir check-in | `queue_view`, `checkin` |
| Check-out dalis (kiek check-in užbaigiami check-out) | `checkout` / `checkin` |
| Aktyvumas pagal amžiaus grupes | visi įvykiai, `user_age` |

Pavyzdys (kada geriausia eiti):
```sql
SELECT toDayOfWeek(event_time) AS weekday,
       toHour(event_time)      AS hour,
       avg(duration_sec) / 60  AS avg_wait_min,
       count()                 AS samples
FROM events
WHERE event_type = 'checkout'
GROUP BY weekday, hour
ORDER BY weekday, hour;
```

**Vidutinis laukimo laikas eilės kortelėje** skaičiuojamas MongoDB agregacija iš tos eilės užbaigtų check-in (`checked_out_at − checked_in_at`) ir cache'inamas `cache:queue:{id}`. Kartu rodomas matavimų skaičius.

---

## 10. API prieigos taškai

### Autentifikacija
| Metodas | Kelias | Rolė |
|---|---|---|
| POST | `/auth/register` | – |
| POST | `/auth/login` | – |
| POST | `/auth/logout` | user, admin |
| GET | `/auth/me` | user, admin |

### Eilės ir žemėlapis
| Metodas | Kelias | Rolė |
|---|---|---|
| GET | `/queues/map?min_lat=&min_lng=&max_lat=&max_lng=&zoom=` | visi (cache) |
| POST | `/queues` | user |
| GET | `/queues/{id}` | visi (cache + `queue_view`) |

### Check-in
| Metodas | Kelias | Rolė |
|---|---|---|
| POST | `/queues/{id}/checkin` | user |
| POST | `/queues/{id}/checkout` | user |

### Komentarai ir įvertinimai
| Metodas | Kelias | Rolė |
|---|---|---|
| GET | `/queues/{id}/comments?page=` | visi (cache) |
| POST | `/queues/{id}/comments` | user |
| DELETE | `/comments/{id}` | komentaro autorius |
| POST | `/comments/{id}/like` | user |
| DELETE | `/comments/{id}/like` | user |
| POST | `/queues/{id}/review` | user |

### Vartotojas
| Metodas | Kelias | Rolė |
|---|---|---|
| GET | `/me/queues?page=` | user (*jei spėsim*; dabar 501) |

### Sistema
| Metodas | Kelias | Rolė |
|---|---|---|
| GET | `/health` | visi (MongoDB, Redis ir ClickHouse jungčių būsena) |

### Ataskaitos (visos cache'inamos)
| Metodas | Kelias | Rolė |
|---|---|---|
| GET | `/reports/activity?period=day\|week\|month&from=&to=` | admin |
| GET | `/reports/checkins?period=day\|week\|month&from=&to=` | admin |
| GET | `/reports/wait-times?queue_id=` | admin |
| GET | `/reports/popular-queues?days=7&sort_by=views\|checkins&limit=10` | admin |
| GET | `/reports/checkout-rate?from=&to=` | admin |
| GET | `/reports/activity-by-age` | admin |

---

## 11. Frontend puslapiai

1. **Prisijungimas ir registracija.**
2. **Pagrindinis puslapis (žemėlapis):**
   - heatmapas (`leaflet.heat`), o priartinus nuo zoom 15 rodomi pinai;
   - užklausa `/queues/map` siunčiama pajudinus žemėlapį (su debounce) ir kas 30 s;
   - nauja eilė kuriama paspaudus vietą žemėlapyje: atsidaro iššokantis langas, kuriame įvedamas pavadinimas (tik `user` rolei).
3. **Eilės langas** (atsidaro paspaudus piną): informacija, check-in / check-out mygtukas, žvaigždučių įvertinimas, komentarų sąrašas su ženkleliais ir likais, komentaro forma.
4. **Mano eilės** *(jei spėsim)*: maršrutas `/my-queues` yra, bet puslapis tuščias ir nuorodos meniu nėra.
5. **Ataskaitų puslapis** (tik admin): lentelės ir grafikai, pvz., Recharts.

---

## 12. Projekto struktūra

```
./
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── seed.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db/          # mongo.py, redis.py, clickhouse.py
│       ├── auth/        # sesijos, get_current_user, require_role
│       ├── models/      # Pydantic schemos
│       ├── routers/     # auth, queues, checkins, comments, reviews, me, reports
│       ├── services/    # weight.py, events.py, cache.py, locks.py
│       └── clickhouse/  # init.sql
└── frontend/
    ├── Dockerfile
    └── src/             # pages/, components/Map, components/QueuePanel, api/
```

`docker-compose.yml` servisai: `mongo`, `redis`, `clickhouse`, `backend`, `frontend`.

---

## 13. Darbo pasiskirstymas (2 žmonės)

Darbas dalijamas **pagal funkcijas**: kiekvienas savo dalį daro nuo duomenų bazės iki frontend'o. Taip abu dirba su MongoDB, Redis ir React, o gynime kiekvienas gali paaiškinti savo dalį iki galo.

### Etapas 1. Kartu
- Repozitorija, `docker-compose.yml`, prisijungimas prie MongoDB, Redis ir ClickHouse.
- Projekto skeletas (backend ir frontend).
- Sutartas duomenų modelis (7 skyrius) ir API kontraktas (10 skyrius).
- Bendri helperiai, kurių signatūras sutariama iš anksto:
  - `track_event(event_type, **fields)`: įvykio siuntimas į ClickHouse;
  - `add_weight(queue_id, user_id, action)`: svorio pridėjimas su pumpavimo apsauga.
- Registracija, prisijungimas, sesijos Redis, rolių tikrinimas.

### Etapas 2. Atskirai

**Žmogus A: eilės, žemėlapis, check-in**
- Eilių kūrimas, svorio logika ir `add_weight`.
- `/queues/map` su geoužklausa ir cache.
- Check-in / check-out su Redis (aktyvių rinkinys, užraktas).
- Eilės suvestinė `/queues/{id}`: žmonių skaičius, vidutinis laukimo laikas, vartotojo būsena, cache.
- Frontend: žemėlapis, heatmapas, pinai, „Nauja eilė“ forma, eilės lango karkasas su check-in mygtuku.

**Žmogus B: komentarai, įvertinimai, ženkleliai, analitika**
- Komentarai (kūrimas, trynimas, rate limit), likai, įvertinimai.
- Ženkleliai ir jų rodymas prie komentarų, komentarų cache.
- `track_event` ir ClickHouse lentelė.
- Visos ataskaitos ir jų cache.
- `seed.py`.
- Frontend: komentarų ir įvertinimų komponentai eilės lange, ataskaitų puslapis.

Domas:
- Sesijos, login, registracija, eiliu sukurimas
- Svorio logika, queues map su geouzklaus, track_event ir clickhouse lentele, visos ataskaitos
- comment_created, review_created and comment_liked. The person doing check-in and the queue detail endpoint needs to send  
    checkin, checkout (with duration_sec) and queue_view.
- seed.py

Danielius:
- Komentarai, komentaru cache, likes, ivertinimai, badges rodymas prie komentaru, badges cache
- UI sitiems, UI eilei, likes ideti i komentaru dokumenta kaip masyva, paupdatint plana

### Priklausomybės
- Kol A nebaigė eilių kūrimo, B naudoja kelias eiles, įrašytas tiesiai į MongoDB arba per ankstyvą `seed.py` versiją.
- B kviečia A funkciją `add_weight` komentarams ir įvertinimams.
- Eilės langą sudaro A karkasas, į kurį B įstato `<Comments />` ir `<Rating />` komponentus.

### Etapas 3. Kartu
- Integracija ir testavimas su seed duomenimis.
- „Mano eilės“ (jei spėsim; daro tas, kas pirmas baigs savo dalį).
- README, Swagger aprašymų patikrinimas.
- Pasiruošimas gynimui: kiekvienas papasakoja savo dalį kitam.

### Darbas su Git
- `main` šaka visada veikianti, kiekvienai funkcijai atskira šaka (`feature/checkin`, `feature/comments` ir t. t.).
- Į `main` sujungiama per pull request, kurį peržiūri kitas komandos narys.
- Commit'ai maži ir aiškiai pavadinti, kad istorijoje matytųsi abiejų indėlis.

### Seed duomenys
`seed.py` (`docker compose exec backend python seed.py`) prieš pildydamas išvalo MongoDB kolekcijas, ClickHouse `events` ir Redis eilių / cache raktus (sesijos lieka). Sukuria:
- 1000 vartotojų, tarp jų `user@example.com` ir `admin@example.com` (slaptažodis `password`);
- 500 eilių prie realių gatvių ir prekybos centrų 5 miestuose; 80 jų matomos žemėlapyje dabar;
- 20 000 check-in (400 aktyvių dabar, įrašyti ir į Redis; vienas vartotojas eilėje tik kartą), laukimo laikas ilgesnis piko valandomis;
- 10 000 komentarų su ~25 000 likų, 5000 įvertinimų; skaitikliai (`total_likes`, `comment_count`, `rating_*`) suderinti;
- 4 ženklelius ir ~138 000 ClickHouse įvykių per 6 mėnesius, sugeneruotų iš tų pačių duomenų.