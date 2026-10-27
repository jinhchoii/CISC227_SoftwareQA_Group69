from datetime import date, timedelta

from app import store


def create_book(client, title="Clean Code", author="Robert C. Martin", isbn="978-0132350884", total_copies=1):
    response = client.post(
        "/books",
        json={
            "title": title,
            "author": author,
            "isbn": isbn,
            "total_copies": total_copies,
        },
    )
    assert response.status_code == 201
    return response.get_json()


def create_member(client, name="James", email="james@example.com"):
    response = client.post(
        "/members",
        json={
            "name": name,
            "email": email,
        },
    )
    assert response.status_code == 201
    return response.get_json()


def checkout_book(client, book_id, member_id):
    response = client.post(
        "/loans",
        json={
            "book_id": book_id,
            "member_id": member_id,
        },
    )
    return response


# ============================================================
# COMMIT 1: Book listing, searching, creation, viewing, updating
# ============================================================

def test_list_books_returns_all_created_books(client):
    first_book = create_book(
        client,
        title="Clean Code",
        author="Robert C. Martin",
        isbn="1",
    )
    second_book = create_book(
        client,
        title="The Pragmatic Programmer",
        author="Andrew Hunt",
        isbn="2",
    )

    response = client.get("/books")

    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 2
    assert books[0]["id"] == first_book["id"]
    assert books[1]["id"] == second_book["id"]


def test_search_books_by_title_returns_matching_book(client):
    create_book(client, title="Clean Code", author="Robert C. Martin", isbn="1")
    create_book(client, title="Design Patterns", author="Erich Gamma", isbn="2")

    response = client.get("/books?search=clean")

    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Clean Code"


def test_search_books_by_author_returns_matching_book(client):
    create_book(client, title="Clean Code", author="Robert C. Martin", isbn="1")
    create_book(client, title="Design Patterns", author="Erich Gamma", isbn="2")

    response = client.get("/books?search=gamma")

    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 1
    assert books[0]["author"] == "Erich Gamma"


def test_add_book_saves_expected_fields(client):
    response = client.post(
        "/books",
        json={
            "title": "Refactoring",
            "author": "Martin Fowler",
            "isbn": "978-0201485677",
            "total_copies": 3,
        },
    )

    assert response.status_code == 201
    created_book = response.get_json()
    assert created_book["title"] == "Refactoring"
    assert created_book["author"] == "Martin Fowler"
    assert created_book["isbn"] == "978-0201485677"
    assert created_book["total_copies"] == 3
    assert created_book["available_copies"] == 3

    saved_response = client.get(f"/books/{created_book['id']}")
    assert saved_response.status_code == 200
    assert saved_response.get_json()["title"] == "Refactoring"


def test_view_one_book_returns_requested_book(client):
    first_book = create_book(client, title="Book One", author="Author One", isbn="1")
    create_book(client, title="Book Two", author="Author Two", isbn="2")

    response = client.get(f"/books/{first_book['id']}")

    assert response.status_code == 200
    book = response.get_json()
    assert book["id"] == first_book["id"]
    assert book["title"] == "Book One"
    assert book["author"] == "Author One"


def test_update_book_changes_fields_and_persists(client):
    book = create_book(client, title="Old Title", author="Old Author", isbn="1")

    response = client.put(
        f"/books/{book['id']}",
        json={
            "title": "New Title",
            "author": "New Author",
        },
    )

    assert response.status_code == 200
    updated_book = response.get_json()
    assert updated_book["title"] == "New Title"
    assert updated_book["author"] == "New Author"
    assert updated_book["isbn"] == "1"

    saved_response = client.get(f"/books/{book['id']}")
    saved_book = saved_response.get_json()
    assert saved_book["title"] == "New Title"
    assert saved_book["author"] == "New Author"


