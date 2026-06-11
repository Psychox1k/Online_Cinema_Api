import asyncio
import random
from decimal import Decimal

import uuid
from faker import Faker
from sqlalchemy import select

from database import (
    UserGroupModel,
    UserGroupEnum,
    UserModel,
    GenreModel,
    DirectorModel,
    StarModel,
    MovieModel,
    CertificationModel,
)
from database.session import get_postgresql_db_contextmanager

fake = Faker("en_US")

MOVIE_TITLES = [
    "The Last Protocol",
    "Operation: Red Horizon",
    "Vengeance at Dawn",
    "Echoes of Tomorrow",
    "Neon Dystopia",
    "The Quantum Paradox",
    "Whispers in the Wind",
    "The Weight of Silence",
    "A Memory of Us",
    "The House on the Edge",
    "Midnight Awakening",
    "Shadows in the Deep",
    "My Accidental Vacation",
    "The Great Coffee Heist",
    "Too Many Bosses",
]

GENRES_LIST = [
    "Action",
    "Comedy",
    "Drama",
    "Thriller",
    "Sci-Fi",
    "Horror",
    "Mystery",
    "Romance",
    "Documentary",
]

CERTIFICATIONS_LIST = ["G", "PG", "PG-13", "R", "NC-17", "18+"]


async def seed_certifications(db):
    print(f"[*] Generating {len(CERTIFICATIONS_LIST)} certifications...")
    certifications = [CertificationModel(name=name) for name in CERTIFICATIONS_LIST]
    db.add_all(certifications)
    await db.commit()
    print("[+] Certifications successfully created!")


async def seed_users(db, count=20):
    print(f"[*] Generating {count} users...")

    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    result = await db.execute(stmt)
    user_group = result.scalar_one_or_none()

    if not user_group:
        print(
            "[!] Error: 'user' group not found!"
            " Please run the user groups migration first."
        )
        return

    for _ in range(count):
        email = fake.unique.email()
        password = "Password123!"

        user = UserModel.create(
            email=email, raw_password=password, group_id=user_group.id
        )
        user.is_active = True
        db.add(user)

    await db.commit()
    print("[+] Users successfully created!")


async def seed_genres(db):
    print(f"[*] Generating {len(GENRES_LIST)} genres...")
    genres = [GenreModel(name=name) for name in GENRES_LIST]
    db.add_all(genres)
    await db.commit()
    print("[+] Genres successfully created!")


async def seed_directors(db, count=10):
    print(f"[*] Generating {count} directors...")
    directors = []

    for _ in range(count):
        director = DirectorModel(name=fake.name())
        directors.append(director)

    db.add_all(directors)
    await db.commit()

    print("[+] Directors successfully created!")


async def seed_stars(db, count=30):
    print(f"[*] Generating {count} stars...")

    stars = []

    for _ in range(count):
        star = StarModel(name=fake.name())
        stars.append(star)
    db.add_all(stars)
    await db.commit()

    print("[+] Stars successfully created!")


async def seed_movies(db, count=50):
    print(f"[*] Generating {count} movies...")

    directors_result = await db.execute(select(DirectorModel))
    all_directors = directors_result.scalars().all()

    genres_result = await db.execute(select(GenreModel))
    all_genres = genres_result.scalars().all()

    stars_result = await db.execute(select(StarModel))
    all_stars = stars_result.scalars().all()

    certs_result = await db.execute(select(CertificationModel))
    all_certs = certs_result.scalars().all()

    if not all_directors or not all_genres or not all_certs:
        print("[!] Error: You need to create directors," " genres, and certs first!")
        return

    for i in range(count):
        movie = MovieModel(
            uuid=uuid.uuid4(),
            name=random.choice(MOVIE_TITLES) + f" {i + 1}",
            year=random.randint(1990, 2030),
            time=random.randint(80, 180),
            imdb=round(random.uniform(1.0, 10.0), 1),
            votes=random.randint(100, 1000000),
            meta_score=random.choice([None, round(random.uniform(10.0, 100.0), 1)]),
            gross=random.choice(
                [None, round(random.uniform(100000.0, 1000000000.0), 2)]
            ),
            description=fake.text(max_nb_chars=500),
            price=Decimal(str(round(random.uniform(4.99, 29.99), 2))),
            certification_id=random.choice(all_certs).id,
        )

        movie.genres = random.sample(list(all_genres), k=random.randint(1, 3))
        movie.directors = random.sample(list(all_directors), k=random.randint(1, 2))
        movie.stars = random.sample(list(all_stars), k=random.randint(2, 5))

        db.add(movie)

    await db.commit()
    print("[+] Movies successfully created!")


async def main():
    print("=== Starting Database Seeding ===")

    async with get_postgresql_db_contextmanager() as db:
        await seed_users(db, count=10)
        await seed_certifications(db)
        await seed_genres(db)
        await seed_directors(db, count=15)
        await seed_stars(db, count=40)

        await seed_movies(db, count=50)

    print("=== Seeding Complete! 🍿 ===")


if __name__ == "__main__":
    asyncio.run(main())
