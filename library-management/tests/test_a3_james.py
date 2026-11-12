from datetime import date

from app import store

from unittest.mock import patch


def create_book(client, title="Clean Code", author="Robert C. Martin", isbn="1", total_copies=1):
    response = client.post(
        "/books",
        json={
            "title": title,
            "author": author,
            "isbn": isbn,
            "total_copies": total_copies,
        },
    )
    return response.get_json()


def create_member(client, name, email):
    response = client.post(
        "/members",
        json={
            "name": name,
            "email": email,
        },
    )
    return response.get_json()


def checkout_book(client, book_id, member_id):
    response = client.post(
        "/loans",
        json={
            "book_id": book_id,
            "member_id": member_id,
        },
    )
    return response.get_json()


def create_reservation(client, book_id, member_id):
    response = client.post(
        "/reservations",
        json={
            "book_id": book_id,
            "member_id": member_id,
        },
    )
    return response.get_json()


def test_hold_available_notification_success_with_stub(client, monkeypatch):
    book = create_book(client, total_copies=1)

    borrower = create_member(
        client,
        "Borrower",
        "borrower@example.com",
    )

    waiting_member = create_member(
        client,
        "Waiting Member",
        "waiting@example.com",
    )

    loan = checkout_book(
        client,
        book["id"],
        borrower["id"],
    )

    create_reservation(
        client,
        book["id"],
        waiting_member["id"],
    )

    def successful_notification(recipient, subject, message):
        return True

    monkeypatch.setattr(
        "app.routes.loans.send_notification",
        successful_notification,
    )

    response = client.put(
        f"/loans/{loan['id']}/return"
    )

    assert response.status_code == 200

    returned_loan = response.get_json()

    assert returned_loan["return_date"] == date.today().isoformat()
    assert returned_loan["notification_sent"] is True

    book_response = client.get(
        f"/books/{book['id']}"
    )

    updated_book = book_response.get_json()

    assert updated_book["available_copies"] == 1


def test_hold_available_notification_called_with_expected_details(client):
    book = create_book(client, total_copies=1)

    borrower = create_member(
        client,
        "Borrower",
        "borrower@example.com",
    )

    waiting_member = create_member(
        client,
        "Waiting Member",
        "waiting@example.com",
    )

    loan = checkout_book(
        client,
        book["id"],
        borrower["id"],
    )

    create_reservation(
        client,
        book["id"],
        waiting_member["id"],
    )

    with patch(
        "app.routes.loans.send_notification",
        return_value=True,
    ) as mock_send:
        response = client.put(
            f"/loans/{loan['id']}/return"
        )

    assert response.status_code == 200

    returned_loan = response.get_json()

    assert returned_loan["return_date"] == date.today().isoformat()
    assert returned_loan["notification_sent"] is True

    mock_send.assert_called_once_with(
        "waiting@example.com",
        "Reserved book now available",
        "The book you reserved is now available for pickup.",
    )


def test_update_missing_book_returns_404(client):
    response = client.put(
        "/books/999",
        json={
            "title": "Updated Title",
        },
    )

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Book not found"


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/999")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Book not found"


def test_checkout_missing_book_returns_404(client):
    member = create_member(
        client,
        "James",
        "james@example.com",
    )

    response = client.post(
        "/loans",
        json={
            "book_id": 999,
            "member_id": member["id"],
        },
    )

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Book not found"


def test_return_missing_loan_returns_404(client):
    response = client.put("/loans/999/return")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Loan not found"

def test_return_already_returned_loan_returns_400(client):
    book = create_book(client, total_copies=1)

    member = create_member(
        client,
        "James",
        "james@example.com",
    )

    loan = checkout_book(
        client,
        book["id"],
        member["id"],
    )

    first_return = client.put(
        f"/loans/{loan['id']}/return"
    )

    assert first_return.status_code == 200

    second_return = client.put(
        f"/loans/{loan['id']}/return"
    )

    assert second_return.status_code == 400

    data = second_return.get_json()

    assert data["error"] == "Loan already returned"

def test_renew_missing_loan_returns_404(client):
    response = client.put("/loans/999/renew")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Loan not found"

def test_renew_returned_loan_returns_400(client):
    book = create_book(client, total_copies=1)

    member = create_member(
        client,
        "James",
        "james@example.com",
    )

    loan = checkout_book(
        client,
        book["id"],
        member["id"],
    )

    return_response = client.put(
        f"/loans/{loan['id']}/return"
    )

    assert return_response.status_code == 200

    renew_response = client.put(
        f"/loans/{loan['id']}/renew"
    )

    assert renew_response.status_code == 400

    data = renew_response.get_json()

    assert data["error"] == "Loan already returned"


def test_fine_missing_loan_returns_404(client):
    response = client.get("/loans/999/fine")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Loan not found"

def test_books_page_post_creates_book_and_redirects(client):
    response = client.post(
        "/ui/books",
        data={
            "title": "Refactoring",
            "author": "Martin Fowler",
            "isbn": "978-0201485677",
            "total_copies": "2",
        },
    )

    assert response.status_code == 302

    books_response = client.get("/books")
    books = books_response.get_json()

    assert len(books) == 1
    assert books[0]["title"] == "Refactoring"
    assert books[0]["author"] == "Martin Fowler"
    assert books[0]["total_copies"] == 2
    assert books[0]["available_copies"] == 2

def test_delete_book_page_removes_book_and_redirects(client):
    book = create_book(
        client,
        title="Temporary Book",
        author="Test Author",
        isbn="123",
        total_copies=1,
    )

    response = client.post(
        f"/ui/books/{book['id']}/delete"
    )

    assert response.status_code == 302

    books_response = client.get("/books")
    books = books_response.get_json()

    assert len(books) == 0

def test_return_loan_page_marks_loan_returned_and_restores_copy(client):
    book = create_book(
        client,
        title="Return Test",
        author="Test Author",
        isbn="456",
        total_copies=1,
    )

    member = create_member(
        client,
        "James",
        "james@example.com",
    )

    loan = checkout_book(
        client,
        book["id"],
        member["id"],
    )

    response = client.post(
        f"/ui/loans/{loan['id']}/return"
    )

    assert response.status_code == 302

    returned_loan = store.loans[loan["id"]]

    assert returned_loan.return_date == date.today()

    updated_book = store.books[book["id"]]

    assert updated_book.available_copies == 1

def test_books_page_get_displays_books(client):
    create_book(
        client,
        title="Clean Code",
        author="Robert C. Martin",
        isbn="123",
        total_copies=1,
    )

    response = client.get("/ui/books")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "Clean Code" in page