# mi_calli

A local property management app for small landlords. Manages properties, rooms, tenants, rental contracts, payments, and contract signing — all from a single `docker compose up`.

**mi_calli** means "my house" in Nahuatl.

> Currently designed for local network use. No public hosting or authentication required for a family-scale operation.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + PostgreSQL |
| Migrations | Alembic |
| Frontend | Vanilla JS + HTML (bilingual EN/ES) |
| Reverse proxy | Nginx |
| PDF generation | ReportLab |
| Email | Gmail SMTP (App Password) |
| Contract signing | Google Forms + Google Sheets polling |
| Containerization | Docker Compose |

---

## Features

**Properties**
- Create and manage rental properties
- Upload multiple photos per property
- Track house expenses (water, electricity, etc.) with paid/unpaid status

**Rooms**
- Each property has many rooms
- Rooms show occupied/vacant status derived from active contracts
- Upload multiple photos per room
- Set default rent amount, pay day, and contract duration per room

**Tenants**
- Create tenant accounts (no password needed — local app)
- Assign tenants to rooms via contracts

**Contracts**
- Assign a tenant to a room with amount, pay day, duration, and inventory notes
- All monthly billing entries generated upfront for the full contract duration
- PDF generated automatically per month
- Admin and tenant signing tracked separately
- Contract termination notifies both parties and removes future months

**Payments**
- Record payments per month per contract
- Mark paid from the yearly grid or room detail view
- Import/export data via Excel (.xlsx)

**Signing flow**
- Admin sends signing link → tenant receives email with PDF + Google Form link
- Tenant submits Google Form with their Contract ID
- Backend polls Google Sheet every 2 minutes and auto-marks as signed
- No public URL or webhook needed

**Reminders**
- Daily email reminders sent 3 days before pay day to both tenant and owner
- Reminders stop automatically once payment is marked as received
- Contract expiry notifications sent to both parties

**Dashboard**
- Yearly overview grid — properties × 12 months, color coded paid/unpaid
- Click any cell to see tenant details and take actions
- Bilingual interface (English / Spanish toggle)

---

## Project Structure

```
mi_calli/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── contracts.py
│   │   │   ├── properties.py
│   │   │   ├── rooms.py
│   │   │   └── users.py
│   │   ├── db/
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── contract.py   # Contract, ContractMonth, Payment
│   │   │   ├── property.py   # Property, PropertyImage, HouseExpense
│   │   │   ├── room.py       # Room, RoomImage
│   │   │   └── user.py
│   │   ├── schemas/
│   │   └── main.py           # Lifespan tasks: sheet polling, daily reminders
│   ├── alembic/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── run_migrations.sh
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   └── app.js
├── nginx/
│   └── nginx.conf
├── uploads/              # Generated PDFs and uploaded images (gitignored)
└── docker-compose.yml
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A Gmail account with 2FA enabled (for sending emails)
- A Google Form + Google Sheet (for contract signing)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/pescamill/mi_calli.git
cd mi_calli
```

### 2. Create the environment file

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
DATABASE_URL=postgresql://mi_calli:mi_calli_password@postgres:5432/mi_calli

# Gmail SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourgmail@gmail.com
SMTP_PASSWORD=your_16_char_app_password
SMTP_FROM=yourgmail@gmail.com

# Google Forms signing
GOOGLE_FORM_URL=https://forms.gle/yourformid
GOOGLE_SHEET_ID=your_google_sheet_id

# Optional: public base URL for PDF links in emails
APP_BASE_URL=http://localhost
```

### 3. Start the app

```bash
docker compose up
```

On first run the migrate service automatically applies all Alembic migrations. Open [http://localhost](http://localhost) in your browser.

---

## Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an app password named `mi_calli`
4. Paste the 16-character password into `SMTP_PASSWORD` in `.env`

---

## Google Forms Signing Setup

### Create the form

1. Go to [forms.google.com](https://forms.google.com)
2. Create a form titled "Rent Contract Signature" with:
   - `ID Contrato` — short answer, required
   - `I agree to the terms of this rental contract` — checkbox, required
3. Go to **Responses** → click the Sheets icon → Create new spreadsheet

### Get the Sheet ID

From the spreadsheet URL:
```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```
Add `SHEET_ID_HERE` to `.env` as `GOOGLE_SHEET_ID`.

### Make the sheet public

Share → Anyone with the link → Viewer.

### How it works

The backend polls the Google Sheet every 2 minutes. When a tenant submits the form with their Contract ID, the backend automatically marks the contract as signed. No webhook or public URL needed.

---

## Local Network Access

To access from any device on the same wifi, change your Mac's local hostname:

**System Settings → General → Sharing → Local hostname** → set to `mi-calli`

Then open `http://mi-calli.local` from any device on your network.

---

## Development

### Rebuild after code changes

```bash
docker compose build backend
docker compose restart backend
```

### Rebuild after model changes (wipes database)

```bash
docker compose down -v
rm ./backend/alembic/versions/*.py
docker compose build backend
docker compose up -d postgres
sleep 5
docker compose run --rm --entrypoint "" backend alembic revision --autogenerate -m "describe_change"
docker compose up
```

### View logs

```bash
docker compose logs backend -f
```

### Swagger API docs

`http://localhost/docs`

### Access database directly

```bash
docker compose exec postgres psql -U mi_calli -d mi_calli
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SMTP_HOST` | Yes | SMTP host (smtp.gmail.com) |
| `SMTP_PORT` | Yes | SMTP port (587) |
| `SMTP_USER` | Yes | Gmail address |
| `SMTP_PASSWORD` | Yes | Gmail App Password |
| `SMTP_FROM` | Yes | Sender address |
| `GOOGLE_FORM_URL` | Yes | Google Form URL sent to tenants |
| `GOOGLE_SHEET_ID` | Yes | Google Sheet ID for polling signatures |
| `APP_BASE_URL` | No | Public base URL for PDF links in emails |

---

## Data Model

```
User (admin / tenant)
Property → PropertyImage[]
         → HouseExpense[]
         → Room → RoomImage[]
                → Contract → ContractMonth → Payment[]
                           → tenant (User)
```

---

## Security Notes

This app has no authentication beyond admin/tenant roles. Do not expose it to the public internet without adding proper auth. It is designed for trusted local network use.

Uploads (PDFs, photos) are stored in `./uploads/` which is gitignored. Back this up separately.

---

## License

MIT