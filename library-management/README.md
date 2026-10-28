# Library Management System (LMS)

A small Flask REST API for tracking books, members, and loans. Data is stored
**in memory** (plain Python objects, no database) and is reset every time the
app restarts — this project is meant to run before you've covered databases.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Web UI

Open `http://127.0.0.1:5000/` in a browser for a basic HTML front end (plain
forms and tables, no JavaScript) to add/delete books and members, and check
books in/out:

| Page | Path |
|---|---|
| Home | `/` |
| Books | `/ui/books` |
| Members | `/ui/members` |
| Loans | `/ui/loans` |

This UI is separate from the JSON API below — it's there so you can see the
app working without a REST client, and calls the same in-memory store.

## Entities

- **Book**: `id, title, author, isbn, total_copies, available_copies`
- **Member**: `id, name, email, membership_date`
- **Loan**: `id, book_id, member_id, loan_date, due_date, return_date`

## JSON API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/books` | List all books |
| POST | `/books` | Create a book |
| GET | `/books/<id>` | Get one book |
| PUT | `/books/<id>` | Update a book |
| DELETE | `/books/<id>` | Delete a book |
| GET | `/members` | List all members |
| POST | `/members` | Create a member |
| GET | `/members/<id>` | Get one member |
| PUT | `/members/<id>` | Update a member |
| DELETE | `/members/<id>` | Delete a member |
| POST | `/loans` | Check out a book (`book_id`, `member_id`) |
| PUT | `/loans/<id>/return` | Return a loaned book |
| PUT | `/loans/<id>/renew` | Extend an active loan by 14 days if no other member has an unfulfilled reservation for the book |
| GET | `/loans?member_id=&book_id=` | Look up loans |

## Reservation-aware renewal (R23 and R24)

`PUT /loans/<id>/renew` takes no request body. A successful renewal returns
HTTP 200 with the loan, and adds 14 days to its existing due date. The updated
date is saved and appears in subsequent loan lookups.

If another member has an unfulfilled reservation for the same book, renewal
returns HTTP 400 with `{"error": "Another member is waiting for this book"}`.
The loan, book availability, and reservations are unchanged. Fulfilled
reservations, reservations for other books, and the borrower's own reservation
do not block renewal. Any unfulfilled hold by another member blocks renewal,
even if an earlier hold has already been fulfilled.

A missing loan returns HTTP 404 (`Loan not found`); a returned loan returns
HTTP 400 (`Loan already returned`). This enhancement uses the existing API
and reservation `fulfilled` state; it does not add a reservation-fulfillment
endpoint or enforce the checkout hold queue.

This completes renewal requirements R23 (partially exists in Table A) and R24
(does not exist in Table A). Priority classification must be taken from the
group's Assignment 1 requirements when preparing Table C.

## Tests

```bash
python -m pytest -v
```

The Step 3 renewal tests in `tests/test_derek.py` verify blocked renewal state,
fulfilled holds, the borrower's own hold, other books' holds, a later waiting
member, and returned loans. The existing no-hold renewal test also verifies
the 14-day extension. Unrelated documented Step 2 defects may still fail the
full suite; they are not suppressed or marked as expected failures.
