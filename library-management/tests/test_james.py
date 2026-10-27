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


# ============================================================
# COMMIT 2: Checkout, loan lookup, and return behavior
# ============================================================

def test_checkout_creates_loan_and_decreases_available_copies(client):
    book = create_book(client, total_copies=2)
    member = create_member(client)

    response = checkout_book(client, book["id"], member["id"])

    assert response.status_code == 201
    loan = response.get_json()
    assert loan["book_id"] == book["id"]
    assert loan["member_id"] == member["id"]
    assert loan["due_date"] is not None
    assert loan["return_date"] is None

    book_response = client.get(f"/books/{book['id']}")
    updated_book = book_response.get_json()
    assert updated_book["available_copies"] == 1


def test_checkout_fails_when_no_copies_are_available(client):
    """Expected to expose an existing defect in the reference application."""
    book = create_book(client, total_copies=1)
    first_member = create_member(client, name="Member One", email="one@example.com")
    second_member = create_member(client, name="Member Two", email="two@example.com")

    first_checkout = checkout_book(client, book["id"], first_member["id"])
    assert first_checkout.status_code == 201

    second_checkout = checkout_book(client, book["id"], second_member["id"])

    assert second_checkout.status_code == 400

    book_response = client.get(f"/books/{book['id']}")
    updated_book = book_response.get_json()
    assert updated_book["available_copies"] == 0


def test_lookup_loans_by_book_id_returns_only_matching_loans(client):
    first_book = create_book(client, title="Book One", author="A", isbn="1")
    second_book = create_book(client, title="Book Two", author="B", isbn="2")
    member = create_member(client)

    first_loan = checkout_book(client, first_book["id"], member["id"]).get_json()
    checkout_book(client, second_book["id"], member["id"])

    response = client.get(f"/loans?book_id={first_book['id']}")

    assert response.status_code == 200
    loans = response.get_json()
    assert len(loans) == 1
    assert loans[0]["id"] == first_loan["id"]
    assert loans[0]["book_id"] == first_book["id"]


def test_lookup_loans_by_member_id_returns_only_members_loans(client):
    """Expected to expose the member_id filtering defect in loans.py."""
    first_book = create_book(client, title="Book One", author="A", isbn="1")
    second_book = create_book(client, title="Book Two", author="B", isbn="2")
    first_member = create_member(client, name="Member One", email="one@example.com")
    second_member = create_member(client, name="Member Two", email="two@example.com")

    expected_loan = checkout_book(client, second_book["id"], first_member["id"]).get_json()
    checkout_book(client, first_book["id"], second_member["id"])

    response = client.get(f"/loans?member_id={first_member['id']}")

    assert response.status_code == 200
    loans = response.get_json()
    assert len(loans) == 1
    assert loans[0]["id"] == expected_loan["id"]
    assert loans[0]["member_id"] == first_member["id"]


def test_return_book_sets_return_date_and_restores_copy(client):
    book = create_book(client, total_copies=1)
    member = create_member(client)
    loan = checkout_book(client, book["id"], member["id"]).get_json()

    response = client.put(f"/loans/{loan['id']}/return")

    assert response.status_code == 200
    returned_loan = response.get_json()
    assert returned_loan["return_date"] == date.today().isoformat()

    book_response = client.get(f"/books/{book['id']}")
    updated_book = book_response.get_json()
    assert updated_book["available_copies"] == 1


