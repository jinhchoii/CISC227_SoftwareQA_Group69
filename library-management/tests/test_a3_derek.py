from datetime import date
from unittest.mock import patch

import pytest

from app import store


def member(client, name="Derek"):
    response = client.post("/members", json={"name": name, "email": f"{name}@example.com"})
    assert response.status_code == 201
    return response.get_json()


def book(client):
    response = client.post("/books", json={"title": "Coverage Book", "author": "Author", "isbn": "327", "total_copies": 1})
    assert response.status_code == 201
    return response.get_json()


@pytest.mark.parametrize("method", ["put", "delete"])
def test_missing_member_changes_return_error_without_changing_members(client, method):
    existing = member(client)
    response = getattr(client, method)("/members/999", json={"name": "Changed"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Member not found"}
    assert client.get("/members").get_json() == [existing]


@pytest.mark.parametrize("missing", ["book", "member"])
def test_reservation_missing_reference_does_not_create_reservation(client, missing):
    existing_book = book(client)
    existing_member = member(client)
    response = client.post("/reservations", json={
        "book_id": 999 if missing == "book" else existing_book["id"],
        "member_id": 999 if missing == "member" else existing_member["id"],
    })
    assert response.status_code == 404
    assert response.get_json() == {"error": f"{missing.capitalize()} not found"}
    assert client.get("/reservations").get_json() == []


def test_members_page_creates_and_displays_member(client):
    response = client.post("/ui/members", data={"name": "Page Member", "email": "page@example.com"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/members")
    saved = client.get("/members").get_json()
    assert len(saved) == 1
    assert saved[0]["name"] == "Page Member"
    assert saved[0]["email"] == "page@example.com"
    page = client.get("/ui/members")
    assert page.status_code == 200
    assert b"Page Member" in page.data and b"page@example.com" in page.data


def test_members_page_deletion_preserves_other_member(client):
    removed = member(client, "Remove")
    kept = member(client, "Keep")
    response = client.post(f"/ui/members/{removed['id']}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/members")
    assert client.get("/members").get_json() == [kept]


def test_loans_page_checkout_persists_and_displays_loan(client):
    existing_book = book(client)
    borrower = member(client)
    response = client.post("/ui/loans", data={"book_id": existing_book["id"], "member_id": borrower["id"]})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/loans")
    loans = client.get("/loans").get_json()
    assert len(loans) == 1
    assert loans[0]["book_id"] == existing_book["id"]
    assert loans[0]["member_id"] == borrower["id"]
    assert loans[0]["return_date"] is None
    assert store.books[existing_book["id"]].available_copies == 0
    page = client.get("/ui/loans")
    assert page.status_code == 200
    assert f"/ui/loans/{loans[0]['id']}/return" in page.get_data(as_text=True)


def test_loans_page_missing_book_does_not_create_loan(client):
    borrower = member(client)
    response = client.post("/ui/loans", data={"book_id": 999, "member_id": borrower["id"]})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/loans")
    assert client.get("/loans").get_json() == []


def returned_book_setup(client):
    existing_book = book(client)
    borrower = member(client)
    response = client.post("/loans", json={"book_id": existing_book["id"], "member_id": borrower["id"]})
    assert response.status_code == 201
    return existing_book, response.get_json()


def test_failed_hold_notification_still_returns_book(client, monkeypatch):
    existing_book, loan = returned_book_setup(client)
    waiting = member(client, "Waiting")
    reservation = client.post("/reservations", json={"book_id": existing_book["id"], "member_id": waiting["id"]})
    assert reservation.status_code == 201
    monkeypatch.setattr("app.routes.loans.send_notification", lambda recipient, subject, message: False)
    response = client.put(f"/loans/{loan['id']}/return")
    assert response.status_code == 200
    assert response.get_json()["notification_sent"] is False
    assert response.get_json()["return_date"] == date.today().isoformat()
    assert store.loans[loan["id"]].return_date == date.today()
    assert store.books[existing_book["id"]].available_copies == 1
    assert client.get("/reservations").get_json() == [reservation.get_json()]


@pytest.mark.parametrize("reservation_kind", ["none", "fulfilled", "other_book"])
def test_return_without_eligible_hold_does_not_notify(client, reservation_kind):
    existing_book, loan = returned_book_setup(client)
    if reservation_kind != "none":
        waiting = member(client, "Waiting")
        target = existing_book if reservation_kind == "fulfilled" else book(client)
        response = client.post("/reservations", json={"book_id": target["id"], "member_id": waiting["id"]})
        assert response.status_code == 201
        if reservation_kind == "fulfilled":
            store.reservations[response.get_json()["id"]].fulfilled = True
    with patch("app.routes.loans.send_notification") as send:
        response = client.put(f"/loans/{loan['id']}/return")
    send.assert_not_called()
    assert response.status_code == 200
    assert response.get_json()["return_date"] == date.today().isoformat()
    assert "notification_sent" not in response.get_json()
    assert store.loans[loan["id"]].return_date == date.today()
    assert store.books[existing_book["id"]].available_copies == 1
