"""Seed duomenys. Paleidimas: `docker compose exec backend python seed.py`

Kol kas įrašo tik ženklelius.
TODO(B): ~1000 vartotojų, ~500 eilių, ~20 000 check-in, ~10 000 komentarų,
~100 000 ClickHouse įvykių per 6 mėn. (dalis veiklos – per paskutines kelias valandas).
"""

import asyncio

from app.db import mongo

BADGES = [
    {"name": "Bronzinis eilininkas", "min_likes": 10, "icon": "bronze"},
    {"name": "Sidabrinis eilininkas", "min_likes": 50, "icon": "silver"},
    {"name": "Auksinis eilininkas", "min_likes": 200, "icon": "gold"},
    {"name": "Eilių legenda", "min_likes": 1000, "icon": "legend"},
]


async def seed_badges() -> None:
    db = mongo.get_db()
    for badge in BADGES:
        await db.badges.update_one({"name": badge["name"]}, {"$set": badge}, upsert=True)
    print(f"Ženkleliai: {len(BADGES)}")


async def main() -> None:
    mongo.connect()
    await mongo.ensure_indexes()
    await seed_badges()
    mongo.close()


if __name__ == "__main__":
    asyncio.run(main())
