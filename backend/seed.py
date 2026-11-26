"""Seed duomenys. Paleidimas: `docker compose exec backend python seed.py`

DĖMESIO: išvalo esamus duomenis (MongoDB kolekcijas, ClickHouse `events`, Redis eilių
ir cache raktus; sesijos lieka) ir sugeneruoja naujus:
~1000 vartotojų, ~500 eilių, ~20 000 check-in, ~10 000 komentarų, ~5000 įvertinimų,
ženklelius ir ~100 000 ClickHouse įvykių per 6 mėnesius. Dalis eilių aktyvios dabar,
kad matytųsi žemėlapyje.

Prisijungimas: `user@example.com` / `admin@example.com`, slaptažodis visiems `password`.
"""

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from faker import Faker

from app.auth.passwords import hash_password
from app.config import settings
from app.db import clickhouse, mongo, redis
from app.services.events import _COLUMN_NAMES, _COLUMN_TYPES

N_USERS = 1000
N_QUEUES = 500
N_ACTIVE_QUEUES = 80  # matomos žemėlapyje dabar
N_CHECKINS = 20_000
N_COMMENTS = 10_000
N_REVIEWS = 5_000
N_LOGINS = 25_000
N_VIEWS = 35_000
DAYS = 180
PASSWORD = "password"

BADGES = [
    {"name": "Grybas", "min_likes": 10, "icon": "bronze"},
    {"name": "Kantrus pilietis", "min_likes": 50, "icon": "silver"},
    {"name": "Ilgų distancijų stovėtojas", "min_likes": 200, "icon": "gold"},
    {"name": "Stulpas", "min_likes": 1000, "icon": "legend"},
]

# Realūs taškai (gatvės ir prekybos centrai), aplink kuriuos dedamos eilės. Eilė pasislenka
# nuo taško ne daugiau kaip ~100 m, kad nepatektų į parką ar upę.
ANCHORS = [  # (lat, lng, pavadinimas, ar prekybos centras)
    # Vilnius
    (54.6871, 25.2700, "Gedimino pr.", False),
    (54.6833, 25.2895, "Pilies g.", False),
    (54.6800, 25.2840, "Vokiečių g.", False),
    (54.6770, 25.2700, "Naugarduko g.", False),
    (54.6740, 25.2750, "Kauno g.", False),
    (54.6700, 25.2840, "Geležinkelio g.", False),
    (54.6650, 25.3050, "Liepkalnio g.", False),
    (54.6720, 25.2450, "Savanorių pr.", False),
    (54.6965, 25.2720, "Konstitucijos pr.", False),
    (54.7010, 25.2880, "Kalvarijų g.", False),
    (54.7090, 25.2990, "Žirmūnų g.", False),
    (54.6970, 25.3100, "Antakalnio g.", False),
    (54.7150, 25.2450, "Ukmergės g.", False),
    (54.7120, 25.2420, "Šeškinės g.", False),
    (54.7050, 25.2250, "Viršuliškių g.", False),
    (54.7180, 25.2150, "Justiniškių g.", False),
    (54.7100, 25.2100, "Laisvės pr.", False),
    (54.7230, 25.3370, "Saulėtekio al.", False),
    (54.7105, 25.2635, "Akropolis", True),
    (54.7154, 25.2797, "Ozas", True),
    (54.6990, 25.2600, "Panorama", True),
    (54.6960, 25.2780, "Europa", True),
    # Kaunas
    (54.8970, 23.9120, "Laisvės al.", False),
    (54.8960, 23.8950, "Vilniaus g.", False),
    (54.9070, 23.9400, "Savanorių pr.", False),
    (54.9020, 23.9700, "Taikos pr.", False),
    (54.8920, 23.9230, "Akropolis", True),
    # Klaipėda
    (55.7160, 21.1330, "H. Manto g.", False),
    (55.7020, 21.1500, "Tilžės g.", False),
    (55.6950, 21.1650, "Taikos pr.", False),
    (55.6850, 21.1550, "Baltijos pr.", False),
    # Šiauliai
    (55.9330, 23.3150, "Vilniaus g.", False),
    (55.9360, 23.3120, "Aušros al.", False),
    # Panevėžys
    (55.7350, 24.3550, "Respublikos g.", False),
    (55.7360, 24.3400, "Klaipėdos g.", False),
]
ANCHOR_JITTER = 0.0006  # ~65 m platumos kryptimi

PLACES = [
    "Regitra", "Maxima", "Lidl", "Iki", "Rimi", "Norfa", "Paštas", "Sodra", "Migracija",
    "Poliklinika", "VMI", "Kebabinė", "Kavinė", "Bankas", "Vaistinė", "Užimtumo tarnyba",
    "Degalinė", "Muziejus", "Kino teatras", "Picerija",
]
# Kas būna prekybos centre
MALL_PLACES = ["Maxima", "Iki", "Rimi", "Kavinė", "Bankas", "Vaistinė", "Kino teatras", "Picerija", "Kebabinė"]

COMMENTS = [
    "Atėjau jaunas, išeisiu su pensija.",
    "Žmogus priešais mane jau trečią kartą švenčia gimtadienį.",
    "Spėjau perskaityti visą „Karą ir taiką“. Du kartus.",
    "Atidarė antrą kasą. Uždarė antrą kasą. Klasika.",
    "Eilė tokia ilga, kad jos gale jau kita laiko juosta.",
    "Kasininkė pažiūrėjo į mane. Manau, tai progresas.",
    "Tas su vežimėliu pilnu agurkų – aš tave matau.",
    "Mano telefonas išsikrovė, mano dvasia – irgi.",
    "Pradėjau eilėje stovėti dėl pieno, dabar jau noriu tik ramybės.",
    "Iš eilės galo matosi Latvija.",
    "Kažkas priekyje moka centais. Iš taupyklės. Kiaulės formos.",
    "Langelis Nr. 3 egzistuoja tik legendose.",
    "Užsisakiau maistą į eilę. Kurjeris irgi atsistojo į eilę.",
    "Susipažinau su žmona čia. Dabar jau ir išsiskyrėm.",
    "Laukiu taip ilgai, kad mano numerėlis tapo antikvaru.",
    "Sistema vėl neveikia. Darbuotojai irgi.",
    "Penktadienį čia ateina tik stipriausieji.",
    "Pasiėmiau kėdutę, termosą ir testamentą.",
    "Žmonės priekyje jau įkūrė bendruomenę ir renka seniūną.",
    "Greičiau gavau atsakymą iš Sodros nei iš šitos eilės.",
    "Įėjau 5 minutėm. Čia buvo prieš 3 valandas.",
    "Pasakė „tuoj“. Nepasakė, kurių metų.",
    "Ateik 8 ryto. Mes ateinam 7:59, tai nebeateik.",
    "Kebabą gavau greitai, bet sielos ramybės – ne.",
    "Apsaugininkas jau žino mano vardą ir alergijas.",
    "Iš nuobodulio pradėjau skaičiuoti plyteles. 1 482.",
    "Jei skaitot tai – bėkit, kol dar galit.",
    "Eilė juda. Geologiniu greičiu, bet juda.",
    "Ačiū programėlei, dabar žinau, kad kenčiu ne vienas.",
    "Darbuotoja išėjo „5 minutėm“ pietų. Aš čia jau pavakarieniavau.",
    "Pamačiau kasą su užrašu „Laisva“. Tai buvo meluojantis užrašas.",
    "Geriausia eilė mano gyvenime. 2/10.",
    "Mano kojos jau pateikė prašymą dėl atostogų.",
    "Močiutė priekyje turi „tik vieną klausimą“. Jau dvidešimtą.",
    "Atsistojau į eilę vienišas. Dabar turiu tris draugus ir vieną priešą.",
    "Darbuotojai pietauja pamainomis. Visi vienu metu.",
    "Kava atšalo, užšalo ir vėl atitirpo. Eilė nepajudėjo.",
    "Jei ši eilė būtų serialas, jau būtų septintas sezonas.",
    "Mačiau, kaip kasininkė pagalvojo apie darbą. Tik pagalvojo.",
    "Žmona paskambino paklausti, kur aš. Pasakiau „beveik priėjau“. Ji nebetiki.",
    "Vyras priekyje moka čekiu. Nežinojau, kad jie dar egzistuoja.",
    "Stoviu taip ilgai, kad mane įrašė į inventorių.",
    "Apsauga paklausė, ar aš čia dirbu.",
    "Pasakė, kad čia ne mano langelis. Kuris mano – niekas nežino.",
    "Priekyje 4 žmonės ir 1 problema, kuri užtruks valandą.",
    "Pasiimkit maisto, vandens ir kompasą.",
    "Paklausiau, ar greitai. Kasininkė juokėsi. Ilgai.",
    "Ši eilė išmokė mane medituoti. Ir keiktis.",
    "Gavau numerėlį 666. Velnias irgi laukia eilėje.",
    "Kažkas priekyje grąžina prekę be čekio. Atsisveikinkit su šeimom.",
    "Mano kaimynas eilėje jau užaugino daigus.",
    "Atėjau su plaukais. Išeisiu su plike.",
    "Eilės gale gimė legenda, kad kažkas kažkada buvo aptarnautas.",
    "Kasininkė pakėlė akis. Visa eilė sulaikė kvapą. Nuleido.",
    "Rašau testamentą. Vietą eilėje palieku sūnui.",
    "Kas nors, praneškit mano darbdaviui, kad aš gyvas.",
    "Užsukau „tik duonos“. Tai buvo prieš dvi valandas ir trejus planus gyvenimui.",
    "Mano batai įaugo į grindis.",
    "Prieš mane stovintis senukas sako, kad atėjo dar jaunuolis.",
    "Kai pagaliau priėjau, paaiškėjo, kad stovėjau ne toje eilėje.",
    "Langelis uždarytas „techninėms priežastims“. Technika – kava.",
    "Kažkas bandė įlįsti be eilės. Jo daugiau niekas nematė.",
    "Paprašiau knygos skundams. Ji irgi su eile.",
    "Pradėjau auginti barzdą eilės pradžioje. Dabar ji ilgesnė už eilę.",
    "Pamiršau, ko atėjau. Bet nuo eilės nepasitrauksiu – per daug investuota.",
    "Vaikai priekyje jau baigė mokyklą.",
    "Elektroninė eilė rodo numerį 47. Mano numeris 46. Nesuprantu.",
    "Darbuotojas sakė: „Ateikit rytoj“. Aš jau iš vakar.",
    "Telefonas sako, kad nuėjau 12 žingsnių per 2 valandas.",
    "Regitroje laukiau tiek, kad mano teisės spėjo pasibaigti.",
    "Migracijoje laukiau tiek, kad spėjau emigruoti ir sugrįžti.",
    "Poliklinikoje kol laukiau, pasveikau. Ir vėl susirgau.",
    "VMI langelyje paklausė, ar deklaravau laiką, praleistą eilėje.",
    "Maximoje veikia tik savitarnos kasos. Ir jos tik „kviečia darbuotoją“.",
    "Ar normalu, kad eilė juda atgal?",
    "Iš pradžių pykau, dabar jau priėmiau. Penkios gedulo stadijos per vieną eilę.",
    "Pasiėmiau numerėlį. Numerėlio aparatas pasiėmė mano viltį.",
    "Turiu 3 % baterijos ir 0 % kantrybės.",
    "Valio! Po 40 min. pagaliau... perkėlė į kitą langelį.",
    "Gyvenu čia. Paštą siųskit į eilę.",
]

rng = random.Random(42)
fake = Faker("lt_LT")
Faker.seed(42)
NOW = datetime.now(timezone.utc).replace(microsecond=0)
START = NOW - timedelta(days=DAYS)


def rand_time(after: datetime, before: datetime = NOW) -> datetime:
    """Atsitiktinis laikas intervale, dažniau darbo valandomis (8–20 val. vietos laiku ~ UTC+2)."""
    span = (before - after).total_seconds()
    if span <= 0:
        return before
    for _ in range(5):
        t = after + timedelta(seconds=rng.uniform(0, span))
        if 6 <= t.hour < 18 or rng.random() < 0.15:
            return t.replace(microsecond=0)
    return t.replace(microsecond=0)


def wait_seconds(t: datetime) -> int:
    """Laukimo trukmė: ilgesnė piko valandomis ir pirmadieniais / penktadieniais."""
    hour = (t.hour + 2) % 24
    peak = 1.0 + 0.8 * math.exp(-((hour - 12) ** 2) / 8) + 0.6 * math.exp(-((hour - 17) ** 2) / 4)
    day = {0: 1.3, 4: 1.2, 5: 1.4}.get(t.weekday(), 1.0)
    minutes = rng.lognormvariate(math.log(12), 0.6) * peak * day
    return int(max(1, min(180, minutes)) * 60)


def age(birth_year: int) -> int:
    return NOW.year - birth_year


# --- Mongo ---


async def reset() -> None:
    db = mongo.get_db()
    for name in ("users", "queues", "checkins", "comments", "reviews", "badges"):
        await db[name].drop()
    await mongo.ensure_indexes()

    r = redis.get_redis()
    for pattern in ("queue:*", "cache:*", "weight:*", "rl:*", "lock:*"):
        keys = [k async for k in r.scan_iter(match=pattern, count=1000)]
        for i in range(0, len(keys), 1000):
            await r.delete(*keys[i : i + 1000])

    await clickhouse.get_clickhouse().command("TRUNCATE TABLE IF EXISTS events")
    print("Išvalyta")


async def seed_badges() -> None:
    await mongo.get_db().badges.insert_many([dict(b) for b in BADGES])
    print(f"Ženkleliai: {len(BADGES)}")


async def seed_users() -> list[dict]:
    pw = await hash_password(PASSWORD)  # vienas hash visiems, kitaip bcrypt užtruktų minutes
    users = [
        {
            "_id": ObjectId(), "email": "admin@example.com", "first_name": "Admin",
            "last_name": "Adminas", "birth_year": 1990, "role": "admin",
        },
        {
            "_id": ObjectId(), "email": "user@example.com", "first_name": "Jonas",
            "last_name": "Jonaitis", "birth_year": 1998, "role": "user",
        },
    ]
    for i in range(N_USERS - len(users)):
        users.append({
            "_id": ObjectId(), "email": f"user{i}@example.com",
            "first_name": fake.first_name(), "last_name": fake.last_name(),
            "birth_year": int(min(2010, max(1945, rng.gauss(1992, 13)))), "role": "user",
        })
    for u in users:
        u.update(password_hash=pw, total_likes=0, created_at=rand_time(START))
    users[0]["created_at"] = users[1]["created_at"] = START
    return users


def make_queues(users: list[dict]) -> list[dict]:
    queues = []
    for _ in range(N_QUEUES):
        lat, lng, street, is_mall = rng.choice(ANCHORS)
        creator = rng.choice(users)
        created_at = rand_time(max(START, creator["created_at"]))
        queues.append({
            "_id": ObjectId(),
            "title": f"{rng.choice(MALL_PLACES if is_mall else PLACES)}, {street}",
            "location": {
                "type": "Point",
                "coordinates": [
                    round(lng + rng.uniform(-1, 1) * ANCHOR_JITTER * 1.7, 6),  # lng laipsnis ~1,7x trumpesnis
                    round(lat + rng.uniform(-1, 1) * ANCHOR_JITTER, 6),
                ],
            },
            "created_by": creator["_id"],
            "created_at": created_at,
            "rating_sum": 0, "rating_count": 0, "comment_count": 0,
        })
    # Aktyvios eilės: sukurtos neseniai arba turi neseną veiklą
    for q in rng.sample(queues, N_ACTIVE_QUEUES):
        q["active"] = True
    return queues


def set_weights(queues: list[dict], last_activity: dict) -> None:
    """Aktyvioms – svoris dabar > 0; kitoms – svoris jau nukritęs iki 0 (expires_at praeityje)."""
    k = settings.weight_decay_per_min
    for q in queues:
        if q.pop("active", False):
            weight = float(rng.randint(30, int(settings.weight_max)))
            updated = NOW - timedelta(minutes=rng.uniform(0, 25))
        else:
            weight = float(rng.randint(20, 120))
            updated = last_activity.get(q["_id"], q["created_at"])
            updated = min(updated, NOW - timedelta(minutes=weight / k + 1))
        q["weight"] = weight
        q["weight_updated_at"] = updated
        q["expires_at"] = updated + timedelta(minutes=weight / k)


def pick_pairs(n: int, users: list[dict], queues: list[dict], seen: set) -> list[tuple[dict, dict]]:
    """Unikalios (vartotojas, eilė) poros – vienas check-in / įvertinimas eilei."""
    pairs = []
    while len(pairs) < n:
        u, q = rng.choice(users), rng.choice(queues)
        if (u["_id"], q["_id"]) in seen or u["role"] != "user":
            continue
        seen.add((u["_id"], q["_id"]))
        pairs.append((u, q))
    return pairs


# --- Main ---


async def main() -> None:
    mongo.connect()
    redis.connect()
    await clickhouse.connect()
    db, r = mongo.get_db(), redis.get_redis()
    try:
        await reset()
        await seed_badges()

        users = await seed_users()
        users_by_id = {u["_id"]: u for u in users}
        queues = make_queues(users)
        queues_by_id = {q["_id"]: q for q in queues}
        active_queues = [q for q in queues if q.get("active")]
        events: list[list] = []

        def ev(t, type_, user=None, queue=None, score=0, duration=0):
            lng, lat = queue["location"]["coordinates"] if queue else (0.0, 0.0)
            events.append([
                t, type_, str(user["_id"]) if user else "", age(user["birth_year"]) if user else 0,
                str(queue["_id"]) if queue else "", lat, lng, score, duration,
            ])

        last_activity: dict = {}

        def touch(q, t):
            last_activity[q["_id"]] = max(last_activity.get(q["_id"], t), t)

        # Check-in
        checkins, active_sets = [], {}
        seen_checkins: set = set()
        n_recent = 400  # aktyvūs dabar (be check-out) aktyviose eilėse
        for u, q in pick_pairs(N_CHECKINS - n_recent, users, queues, seen_checkins):
            t = rand_time(max(q["created_at"], u["created_at"]), NOW - timedelta(hours=4))
            out = t + timedelta(seconds=wait_seconds(t)) if rng.random() < 0.85 else None
            checkins.append({
                "_id": ObjectId(), "queue_id": q["_id"], "user_id": u["_id"], "queue_title": q["title"],
                "checked_in_at": t, "checked_out_at": out,
            })
            touch(q, t)
            ev(t, "checkin", u, q)
            if out:
                ev(out, "checkout", u, q, duration=int((out - t).total_seconds()))
        for u, q in pick_pairs(n_recent, users, active_queues, seen_checkins):
            t = NOW - timedelta(minutes=rng.uniform(1, 40))
            checkins.append({
                "_id": ObjectId(), "queue_id": q["_id"], "user_id": u["_id"], "queue_title": q["title"],
                "checked_in_at": t.replace(microsecond=0), "checked_out_at": None,
            })
            active_sets.setdefault(q["_id"], []).append(str(u["_id"]))
            ev(t, "checkin", u, q)

        # Komentarai: dalis vartotojų rašo daug (kad atsirastų aukštesni ženkleliai)
        user_list = [u for u in users if u["role"] == "user"]
        activity = [1 / (i + 1) ** 0.8 for i in range(len(user_list))]
        comments = []
        for _ in range(N_COMMENTS):
            u = rng.choices(user_list, weights=activity)[0]
            q = rng.choice(active_queues) if rng.random() < 0.15 else rng.choice(queues)
            lo = max(q["created_at"], u["created_at"])
            t = rand_time(lo) if not q.get("active") or rng.random() < 0.5 else rand_time(max(lo, NOW - timedelta(hours=3)))
            n_likes = min(len(user_list) - 1, int(rng.expovariate(1 / 3)))
            likers = [x for x in rng.sample(user_list, n_likes + 1) if x["_id"] != u["_id"]][:n_likes]
            comments.append({
                "_id": ObjectId(), "queue_id": q["_id"], "user_id": u["_id"], "text": rng.choice(COMMENTS),
                "likes_count": len(likers), "liked_by": [x["_id"] for x in likers], "created_at": t,
            })
            u["total_likes"] += len(likers)
            q["comment_count"] += 1
            touch(q, t)
            ev(t, "comment_created", u, q)
            for x in likers:
                ev(rand_time(t), "comment_liked", x, q)

        # Įvertinimai
        reviews = []
        for u, q in pick_pairs(N_REVIEWS, users, queues, set()):
            t = rand_time(max(q["created_at"], u["created_at"]))
            score = rng.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 5, 3])[0]
            reviews.append({"_id": ObjectId(), "queue_id": q["_id"], "user_id": u["_id"], "score": score, "created_at": t})
            q["rating_sum"] += score
            q["rating_count"] += 1
            touch(q, t)
            ev(t, "review_created", u, q, score=score)

        # Registracija, eilių kūrimas, prisijungimai, peržiūros
        for u in users:
            ev(u["created_at"], "register", u)
        for q in queues:
            ev(q["created_at"], "queue_created", users_by_id[q["created_by"]], q)
        for _ in range(N_LOGINS):
            u = rng.choice(users)
            ev(rand_time(u["created_at"]), "login", u)
        for _ in range(N_VIEWS):
            q = rng.choice(active_queues) if rng.random() < 0.3 else rng.choice(queues)
            u = rng.choice(users) if rng.random() < 0.7 else None
            ev(rand_time(max(q["created_at"], u["created_at"] if u else START)), "queue_view", u, q)

        set_weights(queues, last_activity)

        # Įrašymas
        await db.users.insert_many(users)
        await db.queues.insert_many(queues)
        for i in range(0, len(checkins), 5000):
            await db.checkins.insert_many(checkins[i : i + 5000])
        for i in range(0, len(comments), 5000):
            await db.comments.insert_many(comments[i : i + 5000])
        await db.reviews.insert_many(reviews)

        async with r.pipeline(transaction=False) as pipe:
            for qid, members in active_sets.items():
                key = f"queue:{qid}:active"
                pipe.sadd(key, *members)
                pipe.expireat(key, queues_by_id[qid]["expires_at"])
            await pipe.execute()

        events.sort(key=lambda e: e[0])
        ch = clickhouse.get_clickhouse()
        for i in range(0, len(events), 20_000):
            await ch.insert(
                "events", events[i : i + 20_000],
                column_names=_COLUMN_NAMES, column_type_names=_COLUMN_TYPES,
            )

        print(f"Vartotojai: {len(users)}")
        print(f"Eilės: {len(queues)} (aktyvios dabar: {len(active_queues)})")
        print(f"Check-in: {len(checkins)} (stovi dabar: {sum(map(len, active_sets.values()))})")
        print(f"Komentarai: {len(comments)}, likai: {sum(c['likes_count'] for c in comments)}")
        print(f"Įvertinimai: {len(reviews)}")
        print(f"ClickHouse įvykiai: {len(events)}")
        print(f"Prisijungimas: admin@example.com / user@example.com, slaptažodis „{PASSWORD}“")
    finally:
        await clickhouse.close()
        await redis.close()
        mongo.close()


if __name__ == "__main__":
    asyncio.run(main())
