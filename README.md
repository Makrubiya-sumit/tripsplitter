# ✈️ Trip Expense Splitter

A full-stack Django app that lets you create a trip, add members, log expenses,
and automatically calculates **who owes whom** — with the **minimum number of
settlement transactions**.

Built with: **Python, Django, SQLite, Bootstrap 5**

---

## 1. What's included

```
tripsplitter/
├── manage.py
├── requirements.txt
├── db.sqlite3                 ← created after you run migrations
├── tripsplitter/               ← project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── expenses/                   ← the app (all the real logic lives here)
│   ├── models.py               ← Trip, Member, Expense, Settlement
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py                ← settlement simplification algorithm
│   ├── admin.py
│   ├── migrations/0001_initial.py
│   └── templates/
│       ├── base.html
│       ├── registration/login.html, register.html
│       └── expenses/dashboard.html, trip_list.html, trip_create.html,
│                    trip_detail.html, expense_edit.html
└── static/css/style.css
```

## 2. Prerequisites

- Python 3.10+ installed
- pip (comes with Python)

Check with:
```bash
python3 --version
```

## 3. Step-by-step setup

### Step 1 — Unzip and enter the project
```bash
unzip tripsplitter.zip
cd tripsplitter
```

### Step 2 — Create a virtual environment (recommended)
```bash
python3 -m venv venv

# Activate it:
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Apply database migrations
This creates `db.sqlite3` with all the tables (Trip, Member, Expense, Settlement).
```bash
python manage.py migrate
```

### Step 5 — Create an admin (superuser) account (optional but useful)
```bash
python manage.py createsuperuser
```
Follow the prompts to set username/email/password. This lets you view all data at `/admin/`.

### Step 6 — Run the development server
```bash
python manage.py runserver
```

### Step 7 — Open the app
Visit **http://127.0.0.1:8000/** in your browser.

- Click **Register** to create your account (you don't need the superuser for this).
- Log in, then **Create Trip** → add trip name/destination/dates.
- Open the trip → **Members tab** → add each person going on the trip.
- Switch to the **Expenses tab** → log each expense (title, amount, who paid, date).
- Switch to the **Summary tab** → see the total, each person's fair share, who
  owes/is owed, and the **simplified settlement list** (minimum transactions
  to settle everyone up). Click **Mark Paid** once a payment is actually made
  in real life — it updates everyone's balance.

That's it — fully working locally!

---

## 4. How the settlement algorithm works

For a trip with total expense `T` and `N` members, everyone's fair share is `T / N`.
Each member's raw balance is `amount_they_paid − fair_share`:
- **Positive** → they overpaid, so they're owed money.
- **Negative** → they underpaid, so they owe money.

`expenses/utils.py` then runs a **greedy minimum-cash-flow algorithm**:
repeatedly match the person who owes the most with the person who is owed the
most, settle the smaller of the two amounts, and repeat. This produces the
fewest possible number of payments (instead of everyone paying everyone).

When you click **Mark Paid**, that transaction is saved as a `Settlement`
record, and every balance shown afterwards accounts for it — so the summary
always reflects reality.

---

## 5. Key features implemented

- ✅ User registration & login (Django auth)
- ✅ Create & manage multiple trips (per logged-in user)
- ✅ Add/remove members per trip
- ✅ Add/edit/delete expenses, each tied to who paid
- ✅ Automatic fair-share calculation
- ✅ Minimum-transaction settlement suggestions
- ✅ "Mark Paid" to record real settlements and adjust balances live
- ✅ Dashboard with totals across all your trips
- ✅ Responsive Bootstrap 5 UI (works on mobile & desktop)
- ✅ Django admin panel for raw data management

## 6. Ideas to extend it further (great for a portfolio)

- Add expense categories (Food/Transport/Stay) + a pie chart (Chart.js)
- Export trip summary as PDF or CSV
- Email/WhatsApp reminders for pending settlements
- Multi-currency support
- Invite members by email so they can log in and see their own balance
- Dark mode toggle
- Deploy to Render / Railway / PythonAnywhere so you can share a live link

## 7. Deployment notes

Before deploying anywhere public:
1. Set `DEBUG = False` in `tripsplitter/settings.py`.
2. Set a real `SECRET_KEY` (generate one, don't reuse the dev one in this repo).
3. Set `ALLOWED_HOSTS` to your actual domain.
4. Consider switching to PostgreSQL for production (Render/Railway provide this
   easily) — just swap the `DATABASES` setting.
5. Run `python manage.py collectstatic` and serve static files (e.g. with WhiteNoise).

### Render configuration

The included `render.yaml` deploys the app with the correct production static
asset setup. If you are updating the existing Render service instead of creating
a Blueprint service, set these values in the Render dashboard and deploy again:

- **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command:** `gunicorn tripsplitter.wsgi:application`
- **Environment variables:** `DEBUG=False`, a generated `SECRET_KEY`, and
  `ALLOWED_HOSTS=tripsplitter-f3o7.onrender.com`

The build command is required: it copies and fingerprints `static/css/style.css`
so WhiteNoise can serve the same custom CSS in Render that Django serves locally.

---

Happy building! This project (Django + auth + relational models + a real
calculation algorithm + a clean UI) is genuinely a strong portfolio piece —
it shows backend logic, not just CRUD.
