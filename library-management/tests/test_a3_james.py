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