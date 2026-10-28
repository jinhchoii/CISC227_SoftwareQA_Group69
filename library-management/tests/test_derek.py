from datetime import datetime, timedelta

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


def create_member(client, name="Derek", email="derek@example.com"):
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
    assert response.status_code == 201
    return response.get_json()


def create_reservation(client, book_id, member_id):
    response = client.post(
        "/reservations",
        json={
            "book_id": book_id,
            "member_id": member_id,
        },
    )
    return response


# ============================================================
# COMMIT 1: Book deletion and member management
# ============================================================

def test_delete_book_removes_book(client):
    book = create_book(client)

    response = client.delete(f"/books/{book['id']}")

    assert response.status_code == 204

    get_response = client.get(f"/books/{book['id']}")
    assert get_response.status_code == 404


def test_list_members_returns_all_created_members(client):
    first_member = create_member(client, name="Alice", email="alice@example.com")
    second_member = create_member(client, name="Bob", email="bob@example.com")

    response = client.get("/members")

    assert response.status_code == 200
    members = response.get_json()
    assert len(members) == 2
    assert members[0]["id"] == first_member["id"]
    assert members[1]["id"] == second_member["id"]


def test_add_member_saves_expected_fields(client):
    response = client.post(
        "/members",
        json={
            "name": "Derek",
            "email": "derek@example.com",
        },
    )

    assert response.status_code == 201
    member = response.get_json()
    assert member["name"] == "Derek"
    assert member["email"] == "derek@example.com"
    assert member["membership_date"] is not None

    saved_response = client.get(f"/members/{member['id']}")
    assert saved_response.status_code == 200
    assert saved_response.get_json()["name"] == "Derek"


def test_view_one_member_returns_requested_member(client):
    first_member = create_member(client, name="Alice", email="alice@example.com")
    create_member(client, name="Bob", email="bob@example.com")

    response = client.get(f"/members/{first_member['id']}")

    assert response.status_code == 200
    member = response.get_json()
    assert member["id"] == first_member["id"]
    assert member["name"] == "Alice"
    assert member["email"] == "alice@example.com"


def test_update_member_changes_fields_and_persists(client):
    member = create_member(client, name="Old Name", email="old@example.com")

    response = client.put(
        f"/members/{member['id']}",
        json={
            "name": "New Name",
            "email": "new@example.com",
        },
    )

    assert response.status_code == 200
    updated_member = response.get_json()
    assert updated_member["name"] == "New Name"
    assert updated_member["email"] == "new@example.com"

    saved_response = client.get(f"/members/{member['id']}")
    saved_member = saved_response.get_json()
    assert saved_member["name"] == "New Name"
    assert saved_member["email"] == "new@example.com"


def test_delete_member_removes_member(client):
    member = create_member(client)

    response = client.delete(f"/members/{member['id']}")

    assert response.status_code == 204

    get_response = client.get(f"/members/{member['id']}")
    assert get_response.status_code == 404


