import pytest
from fastapi import status

# ==============================================================================
# CREATE (POST) TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_movie_success_as_admin(
    admin_client,
    create_test_director,
    create_test_star,
    create_test_genre,
    create_test_certification,
):
    """
    Test that an admin user can successfully create a new movie.
    We use factories to create the required related entities first.
    :param admin_client:
    :param create_test_director:
    :param create_test_star:
    :param create_test_genre:
    :param create_test_certification:
    :return:
    """
    director = await create_test_director(name="Christopher Nolan")
    star = await create_test_star(name="Matthew McConaughey")
    genre = await create_test_genre(name="Sci-Fi")
    certification = await create_test_certification(name="PG-13")
    payload = {
        "name": "Interstellar",
        "year": 2014,
        "time": 169,
        "imdb": 8.6,
        "votes": 1500000,
        "price": 14.99,
        "description": "A team of explorers travel through" " a wormhole in space.",
        "certification_id": certification.id,
        "directors": [director.id],
        "stars": [star.id],
        "genres": [genre.id],
    }

    response = await admin_client.post("movies/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Interstellar"
    assert data["year"] == 2014
    assert "id" in data


@pytest.mark.asyncio
async def test_create_movie_success_as_moderator(
    moderator_client,
    create_test_director,
    create_test_star,
    create_test_genre,
    create_test_certification,
):
    """
    Test that a moderator user can successfully create a new movie.
    Using factories to create the required related entities first.
    :param moderator_client:
    :param create_test_director:
    :param create_test_star:
    :param create_test_genre:
    :param create_test_certification:
    :return:
    """

    director = await create_test_director(name="James Cameron")
    star = await create_test_star(name="Arnold Schwarzenegger")
    genre = await create_test_genre(name="Sci-Fi")
    certification = await create_test_certification(name="PG-13")
    payload = {
        "name": "Terminator",
        "year": 1984,
        "time": 169,
        "imdb": 8.6,
        "votes": 1500000,
        "price": 14.99,
        "description": "It follows an indestructible cyborg assassin sent"
        " back in time to assassinate Sarah Connor",
        "certification_id": certification.id,
        "directors": [director.id],
        "stars": [star.id],
        "genres": [genre.id],
    }

    response = await moderator_client.post("movies/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Terminator"
    assert data["year"] == 1984
    assert "id" in data


@pytest.mark.asyncio
async def test_create_movie_forbidden_for_user(auth_client, create_test_certification):
    """
    Test that a regular authenticated user cannot
    create a movie (403 Forbidden).
    :param auth_client:
    :param create_test_certification:
    :return:
    """
    certification = await create_test_certification()

    payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 2000000,
        "price": 9.99,
        "description": "A thief who steals corporate secrets through "
        "the use of dream-sharing technology.",
        "certification_id": certification.id,
        "director_ids": [],
        "star_ids": [],
        "genre_ids": [],
    }

    response = await auth_client.post("movies/", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_movie_conflict(admin_client, create_test_movie):
    """
    Test that creating a movie that violates the UniqueConstraint
    returns a 409 Conflict.
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    existing_movie = await create_test_movie(name="The Dark Knight", year=2008)
    payload = {
        "name": existing_movie.name,
        "year": existing_movie.year,
        "time": existing_movie.time,
        "imdb": existing_movie.imdb,
        "votes": existing_movie.votes,
        "price": float(existing_movie.price),
        "description": existing_movie.description,
        "certification_id": existing_movie.certification_id,
        "director_ids": [],
        "star_ids": [],
        "genre_ids": [],
    }
    response = await admin_client.post("movies/", json=payload)

    assert response.status_code == status.HTTP_409_CONFLICT


# ==============================================================================
# READ (GET) & FILTERING TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_filter_movies_by_year(client, create_test_movie):
    """
    Test filtering movies by release year.
    Matches the 'movie filtering' requirement in the technical task.
    :param client:
    :param create_test_movie:
    :return:
    """

    await create_test_movie(name="Old Movie", year=1999)
    await create_test_movie(name="New Movie", year=2023)

    response = await client.get("movies/?year=1999")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Old Movie"
    assert data["items"][0]["year"] == 1999


@pytest.mark.asyncio
async def test_get_movie_by_id_success(client, create_test_movie):
    """
    Test retrieving a specific movie by its ID.
    :param client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Pulp Fiction", year=2000)
    response = await client.get(f"movies/{movie.id}/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == movie.id
    assert data["name"] == "Pulp Fiction"


async def test_get_movie_by_id_not_found(client):
    """
    Test retrieving a non-existent movie returns a 404 Not Found.
    :param client:
    :return:
    """
    response = await client.get("movies/99999/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# UPDATE (PATCH) TESTS
# ==============================================================================


async def test_update_movie_success(admin_client, create_test_movie):
    """
    Test that an admin can successfully update a movie's details.
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Original Title")

    movie.price = 25.00

    updated_payload = {"name": "Updated name", "price": 15.99}

    response = await admin_client.patch(f"movies/{movie.id}/", json=updated_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated name"
    assert float(data["price"]) == 15.99


async def test_update_movie_success_as_moderator(moderator_client, create_test_movie):
    """
    Test that an admin can successfully update a movie's details.
    :param moderator_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Original Title")

    movie.price = 25.00

    updated_payload = {"name": "Updated name", "price": 15.99}

    response = await moderator_client.patch(f"movies/{movie.id}/", json=updated_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated name"
    assert float(data["price"]) == 15.99


@pytest.mark.asyncio
async def test_update_movie_forbidden_for_user(auth_client, create_test_movie):
    """
     Test that a regular user cannot update a movie.
    :param auth_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="Untouchable Movie")

    response = await auth_client.patch(f"movies/{movie.id}/", json={"name": "Hacked"})
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# DELETE TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_movie_success(admin_client, create_test_movie):
    """
    Test that an admin can successfully delete a movie.
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="To Be Deleted")
    delete_response = await admin_client.delete(f"movies/{movie.id}/")
    assert delete_response.status_code == status.HTTP_200_OK

    get_response = await admin_client.get(f"movies/{movie.id}/")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_movie_forbidden_for_moderator(
    moderator_client, create_test_movie
):
    """
    Test that a regular user cannot delete a movie.
    :param moderator_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="To Be Deleted")
    delete_response = await moderator_client.delete(f"movies/{movie.id}/")
    assert delete_response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_movie_forbidden_for_user(auth_client, create_test_movie):
    """
    Test that a regular user cannot delete a movie.
    :param admin_client:
    :param create_test_movie:
    :return:
    """
    movie = await create_test_movie(name="To Be Deleted")
    delete_response = await auth_client.delete(f"movies/{movie.id}/")
    assert delete_response.status_code == status.HTTP_403_FORBIDDEN
