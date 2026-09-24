# 🎬 CineBook — Movie Ticket Booking Platform

## Live Demo
https://cine-book-4c52.onrender.com/

CineBook is a full-stack **Django MVT** movie ticket booking platform. Browse
movies, pick a show, choose your seats on a dynamic cinema-style seat map,
pay with a simulated demo payment, and get an instant e-ticket — all backed
by PostgreSQL with proper double-booking protection.

> This is a learning / portfolio project. Payments are **simulated** — no
> real payment gateway, and no real money is ever charged.

---

## Features

- **Authentication** — register, login, logout using Django's built-in `auth` system (hashed passwords, validation for duplicate username/email, password confirmation).
- **Movie browsing** — home page with search (title/genre/language) and sorting, movie detail page with trailer link, genre/language/rating/certificate.
- **Show selection** — shows grouped by theatre and screen, only active & future shows are bookable.
- **Dynamic seat selection** — cinema-style seat map (rows A, B, C, D...) with Available / Selected / Booked states, built with vanilla JavaScript. Maximum 10 seats per booking.
- **Server-trusted booking** — the backend re-validates every seat and recalculates the price from the database. The browser's numbers are for display only.
- **Double-booking protection** — a PostgreSQL partial unique constraint plus an atomic transaction guarantees the same seat can never be sold twice for the same show, even under concurrent requests.
- **Demo payment** — choose UPI / Card / Cash at Counter / Demo Payment. A "simulate a failed payment" option is available for demonstration; a failed payment leaves **no** booking behind.
- **Booking summary → Payment → Confirmation → Ticket** flow with a printable ticket page (`window.print()`).
- **My Bookings** — a user only ever sees their own bookings (enforced at the query level, not just the UI).
- **Cancellation** — cancel a confirmed booking up to 30 minutes before showtime; the seats immediately become available again for other users.
- **Profile page** — update name/email, see total & upcoming booking counts.
- **Admin panel** — all models registered in Django admin for quick data management.
- **Security** — CSRF protection on every form, `login_required` on every private page, friendly 404/403/500 pages.
- **Seed data command** — `python manage.py seed_data` creates demo movies, theatres, screens, seats, shows and demo users in one idempotent step.
- **Automated tests** — 24 tests covering auth, movie/show visibility, seat validation, the full booking flow, double-booking, booking security and cancellation.

## Technologies

- Python / Django
- PostgreSQL
- HTML, CSS, vanilla JavaScript (no React/Vue/Angular)
- Pillow (image handling)

---

## 1. Installation

```bash
git clone <your-repo-url> CineBook
cd CineBook

python -m venv env

# Windows
env\Scripts\activate
# macOS / Linux
source env/bin/activate

pip install -r requirements.txt
```

## 2. PostgreSQL Setup

This project connects directly to a local PostgreSQL database — no `.env`
file or environment variables are needed.

Create the database:

```sql
CREATE DATABASE cine_book1;
```

You can do this from `psql`:

```bash
psql -U postgres
CREATE DATABASE cine_book;
\q
```

The database connection is configured directly in
`cine_book/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cine_book1',
        'USER': 'postgres',
        'PASSWORD': 'Thiru@07',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

If your local PostgreSQL username/password/database name are different,
just edit those values directly in `settings.py` before running migrations.

## 3. Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## 4. Demo Data (recommended)

```bash
python manage.py seed_data
```

This populates every related table, in the correct dependency order
(Movies → Theatres → Screens → Seats → Shows → Demo users → a couple of
sample bookings), so you can test the **entire** app immediately:

- **10 movies** — a realistic mix of English, Tamil and Hindi titles across
  Action, Drama, Thriller, Sci-Fi, Romance, Crime, Comedy, Musical and
  Family genres, each with a description, genre, language, duration,
  rating, certificate (U/UA/A) and release date. Two movies re-use the real
  poster images shipped in `media/movies/`; the rest get a distinct,
  auto-generated poster image (via Pillow) so every movie card looks
  different.
- **5 Chennai theatres** — PVR Ampa Skywalk, INOX Citi Centre, AGS Cinemas
  Villivakkam, Sathyam Cinemas and Luxe Cinemas Vadapalani, each with a
  realistic address.
- **12 screens** — 2–3 screens per theatre (`Screen 1`, `Screen 2`, ...).
- **960 seats** — every screen gets its own 8-row (A–H) × 10-seat layout:
  rows A–C are Regular (₹150), D–F are Premium (₹220), G–H are Recliner
  (₹350) — just like a real multiplex.
- **~190 shows** — each screen plays 2 different movies at their own fixed
  time slots across the next 4 days, so no two shows ever clash on the
  same screen, and every movie has multiple dates/timings/theatres to
  choose from.
- **2 demo login accounts** for testing the booking flow as a real
  customer:

  | Username        | Password      |
  |------------------|---------------|
  | `demo_user`      | `DemoPass123` |
  | `priya_sharma`   | `DemoPass123` |

- **2 sample bookings** (one per demo account) so you can see what an
  already-booked seat and an existing "My Bookings" entry look like —
  everything else is left free so you can test the booking flow yourself.

No admin/superuser account is created by this command — create your own
with `createsuperuser` (see step 5) rather than relying on a hardcoded
password.

**Safe to re-run**: `seed_data` uses `get_or_create` (and explicit
existence checks for the sample bookings) at every step, so running it
again never creates duplicate movies, theatres, screens, seats, shows,
users or bookings — it's a no-op if everything already exists.

## 5. Superuser (for the admin panel)

```bash
python manage.py createsuperuser
```

## 6. Run the Server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/**

Admin panel: **http://127.0.0.1:8000/admin/**

---

## Demo Flow

```text
Admin adds a Movie
      ↓
Admin adds a Theatre
      ↓
Admin adds a Screen (linked to the Theatre)
      ↓
Admin adds Seats (or run `seed_data` to auto-generate a layout)
      ↓
Admin adds a Show (Movie + Screen + Date + Time + Price)
      ↓
A customer registers / logs in
      ↓
Customer browses movies → picks a show → selects seats
      ↓
Customer reviews the booking summary → pays (simulated)
      ↓
Booking is confirmed → e-ticket is generated
      ↓
Customer can view "My Bookings" or cancel up to 30 minutes before showtime
```

## Running Tests

```bash
python manage.py test
```

## Project Structure

```text
CineBook_Final/
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── cine_book/            # Project settings, root URLs
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── app/                  # Main application
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py
│   ├── migrations/
│   └── management/commands/seed_data.py
│
├── templates/             # Django templates (base + all pages)
├── static/
│   ├── css/style.css
│   └── js/{main.js,seat_selection.js}
└── media/movies/          # Uploaded movie posters
```

## Notes on Business Rules

- **Maximum 10 seats** per booking, minimum 1 — enforced on the backend, not just the UI.
- **Convenience fee** is a flat, server-side configured value (`settings.CONVENIENCE_FEE`), applied consistently everywhere the total is shown.
- **Seat pricing is always read from the database** at the moment of booking; the browser's running total is purely cosmetic.
- **Double booking** is prevented by a PostgreSQL partial unique index on `(show, seat)` where `is_cancelled = False`, combined with a `transaction.atomic()` block and an `IntegrityError` safety net — so cancelling a booking correctly frees the seat for someone else, while two people can never simultaneously buy the same seat.
- **Cancellation window**: bookings can be cancelled any time up until `CANCELLATION_CUTOFF_MINUTES` (default 30) before the show starts.

## Disclaimer

This project uses a simulated/demo payment flow for educational and
portfolio purposes only. No real payment gateway credentials are required
or used, and no real transactions take place.
