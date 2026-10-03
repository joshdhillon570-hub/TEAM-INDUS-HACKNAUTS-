# SmartCare — GNDEC Hackathon Prototype

**Less waiting. More care.**

SmartCare is a student-built healthcare workflow prototype for the GNDEC Hackathon. Its central idea is simple: hospitals lose time when appointments, queues, patient information and follow-up steps are disconnected. SmartCare connects those steps into one patient-to-doctor journey.

## Problem → Solution

| Problem | SmartCare solution |
|---|---|
| Patients wait without knowing when they will be seen. | Live appointment and queue tracking. |
| Doctors waste time searching for patient information. | Connected patient records. |
| Urgent patients can get lost in a normal queue. | Preliminary symptom-based triage for staff review. |
| Patients are unsure what happens after consultation. | Connected status and follow-up journey. |

## Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask
- Database: SQLite
- No external APIs or complicated frameworks

## Run locally

Python 3.9+ is recommended.

```bash
cd smartcare
python -m venv venv
```

Activate the environment:

**Windows**
```bash
venv\Scripts\activate
```

**macOS/Linux**
```bash
source venv/bin/activate
```

Install Flask and run:

```bash
pip install flask
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

`database.db` is created automatically and seeded with fictional demo patients on first run.

## Demo doctor login

- Doctor ID: `doctor`
- Password: `smartcare`

## Judge demo flow

1. Open the homepage and explain the **Problem → Solution** cards.
2. Click **Book Appointment**.
3. Create a patient appointment. The app stores it in SQLite and creates a token such as `A28`.
4. Open **Doctor Dashboard** in another tab and log in with the demo credentials.
5. The new appointment appears in the same queue used by the patient side.
6. Click **View Patient** to show symptoms, preliminary triage and the shared patient record.
7. Click **Call Patient**. The patient's confirmation page updates automatically through polling and changes to **Please proceed to consultation.**
8. Click **Mark Consultation Complete**. The patient page changes to **Consultation completed.**
9. Add a demo doctor note or prescription to show the connected record.

## How live connection works

Both interfaces read and update the same SQLite `appointments` table. The patient confirmation page polls its appointment endpoint every four seconds. The doctor dashboard polls the queue endpoint every four seconds. This keeps the prototype simple enough for a first-year engineering team to explain while still demonstrating a real two-sided workflow.

## Triage logic

SmartCare uses a deliberately simple preliminary rule:

- **HIGH:** chest pain or breathing difficulty
- **MEDIUM:** fever, cough, headache, injury/pain or stomach pain
- **LOW:** routine/other cases

This is **not a diagnosis or medical decision system**. The UI clearly states that final priority is decided by healthcare staff.

## Project structure

```text
smartcare/
├── app.py
├── database.db
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── patient.html
│   ├── appointment.html
│   ├── confirmation.html
│   ├── doctor_login.html
│   ├── doctor_dashboard.html
│   └── patient_details.html
├── static/
│   ├── style.css
│   └── script.js
└── README.md
```

`patient.html` is reserved for a future standalone patient portal route; the current prototype uses the landing page, appointment page and confirmation/queue page for the patient side.

## Important demo note

All patient names, phone numbers and medical information in the seeded database are fictional. This prototype is not connected to a real hospital and should not be used with real patient information.
