# 🩺 Pulseline

> *Connecting Patients. Empowering Doctors. Transforming Healthcare.*

**Pulseline** *(codename: MediConnect)* is a real-time technomedical platform I built to close the gap between rural clinics and the specialists patients rarely get to see — secure logins, instant chat, live video, and a one-tap emergency line, all wired into one consultation room.

`FastAPI` · `WebSockets` · `WebRTC` · `JWT + Bcrypt` · `SQLite` · `Vanilla JS`

---

### The problem, in plain terms

| 😩 What usually happens | 💡 What Pulseline does instead |
|---|---|
| Patients show up with no records — reports lost, prescriptions forgotten | One button sends a patient's **entire medical history straight to the doctor's screen**, mid-consultation |
| Emergencies mean phone calls, hold music, and hoping someone picks up | A single **Emergency Button** broadcasts to every free specialist at once — first to accept, connects |
| "Telemedicine" often means a laggy call and nothing else | Real-time **chat + video + vitals**, all in the same room, so it feels like a real consultation |
| Data scattered across paper, WhatsApp, and memory | Everything lives in **one secured place**, and the patient decides who sees what |

---

## 🌍 Why It Exists

In rural clinics, a nurse or local doctor is often the only medical presence for miles — but the patient in front of them might need a cardiologist, a dermatologist, or an emergency specialist who is hours away. Pulseline closes that distance.

A local clinician opens a session, logs vitals, and — when the case calls for it — pulls in a remote specialist instantly, whether routinely or through the emergency pathway. The specialist joins over live video, sees the patient's history the moment it's sent, chats with the on-site team, and helps shape the diagnosis and prescription. No travel for the patient, no idle waiting for the clinic, no lost paperwork — just a faster, cheaper, more human path from symptom to specialist care.

---

## ✨ Feature Spotlight

### 📤 One Button. Entire History. Doctor's Screen.
This is the feature I'm proudest of. Mid-consultation, a patient hits a single **"Send Medical Data"** button in the session room —

> `sendDataActionBtn` → fires a `patient_medical_history` event straight down the live WebSocket connection

— and their complete medical record lands in front of the doctor **instantly**, no forms, no uploads, no "let me email that to you." No more re-diagnosing from scratch because a report got left at home. The doctor sees exactly what they need, exactly when they need it.

### 🚨 One-Tap Emergency Button
When a case can't wait, a local doctor taps **Emergency** and the platform takes over from there:

1. The request **broadcasts live** to every available specialist in the right department over WebSockets
2. **First to accept, connects** — no searching, no dialing, no hold music
3. If nobody responds in time, the doctor gets notified immediately and can **retry on the spot, or tap Emergency again at any point** — nothing is left hanging silently
4. The specialist lands straight into a **live video consultation**, patient context already loaded

In a field where minutes matter, this turns what used to be a phone-tag scramble into a near-instant handoff.

### 📂 One Secure Place for Every Record
All patient history, prescriptions, lab reports, and past sessions live in a **single, centralized datastore** — not scattered across paper, WhatsApp chats, and memory. The patient stays in control of exactly what's visible to which doctor, session by session.

### 🔐 Secure, Role-Aware Authentication
- **JWT-based session management** — short-lived access tokens, longer-lived refresh tokens, no repeated logins
- **Bcrypt password hashing** via `passlib` — credentials never touch the database or the wire in plain text
- **Four distinct roles** — patients, local doctors, nurses, specialist doctors — each routed to their own dashboard
- A guided **registration & login flow** with validation on both ends

### 💬 Real-Time Consultation Chat
Built on a persistent WebSocket connection manager that tracks every active user, session, and connection type in memory for instant delivery.
- Text, read receipts, and file/image attachments — streamed live
- **Session-scoped rooms**, so nothing crosses between consultations
- Live presence signaling (*"user joined"*, *"call started"*, *"user disconnected"*) for an app-like feel

### 📹 Peer-to-Peer Video Consultations
Native **WebRTC** — `RTCPeerConnection`, ICE candidates, offer/answer negotiation — signaled over the very same WebSocket used for chat.
- **Multi-party**: specialists, local doctors, and nurses can share one call
- A **pre-call waiting room** and a purpose-built **in-call UI**, tuned for low-bandwidth clinical settings
- Clean handling of joins, reconnects, and teardown

### 🏥 Full Clinical Workflow, Start to Finish
Session creation → vitals & diagnosis → prescription → final report, all in one pipeline. Includes the rural-to-urban referral bridge, WHO percentile growth-chart intelligence for pediatric BMI tracking, and dedicated dashboards for every role.

---

## 🧠 Engineering Highlights

A few things under the hood that go beyond a typical CRUD app:

- **Geospatial emergency routing** — a custom Haversine distance function is registered directly into SQLite to match patients with specialists within a live radius. If nobody's found nearby within the time window, the search radius opens up automatically — real geo-matching, not a static doctor list.
- **Triple-channel WebSocket architecture** — a custom `ConnectionManager` multiplexes three distinct connection types (`active`, `session`, `call`) per user, so presence, chat, and call signaling can all run concurrently without stepping on each other.
- **Offline-safe delivery** — if a doctor isn't connected when an event fires (a new message, an emergency alert), it's queued in a pending-notifications store with a TTL and delivered the moment they reconnect — nothing gets silently dropped.
- **Dual-token JWT auth** — short-lived access tokens paired with long-lived refresh tokens, backed by bcrypt password hashing, so sessions stay secure without constant re-logins.
- **Structured error handling** — a custom `APIException` layer plus Pydantic-validated request/response schemas across every endpoint, instead of raw stack traces leaking to the client.
- **Clinical data intelligence** — WHO percentile datasets power real-time BMI and pediatric growth-chart calculations directly inside the patient record view.
- **~3,600 lines of backend logic** across a 7-table relational schema (patients, doctors, clinics, sessions, messages, attachments, reads) — a real system, not a prototype.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| **Real-Time Communication** | Native WebSockets (chat & call signaling) |
| **Video Calling** | WebRTC (`RTCPeerConnection`, ICE, `getUserMedia`) |
| **Authentication** | JWT (`python-jose`) + Bcrypt password hashing (`passlib`) |
| **Data Validation** | Pydantic |
| **Database** | SQLite (via `sqlite3`), schema-driven with dedicated tables for patients, clinics, doctors, consultation sessions, messages, and attachments |
| **Frontend** | HTML5, CSS3, vanilla JavaScript |
| **Server** | Uvicorn (ASGI) |

---

## 🏗️ Architecture at a Glance

```
┌──────────────┐        WebSocket (chat + signaling)        ┌──────────────┐
│   Patient /   │ ───────────────────────────────────────── │   Doctor /   │
│  Local Clinic │                                            │  Specialist  │
└──────┬───────┘                                            └──────┬───────┘
       │                                                            │
       │              WebRTC peer-to-peer video stream              │
       └────────────────────────────────────────────────────────────┘
                                    │
                          ┌─────────────────┐
                          │   FastAPI Core   │
                          │  (auth, sessions, │
                          │   chat, signaling)│
                          └─────────┬────────┘
                                    │
                          ┌─────────────────┐
                          │  SQLite Database  │
                          │ (patients, docs,   │
                          │  sessions, msgs)   │
                          └─────────────────┘
```

**Three-module design:**
1. **Clinic Session Flow** — vitals capture, diagnosis, and prescription at the point of care.
2. **Telemedicine Bridge** — rural-to-urban specialist referrals with live video and chat.
3. **Patient-Controlled History Sharing** — selective, consent-driven access to past medical records.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- `pip`

### Installation

```bash
# Clone the repository
git clone https://github.com/naagasaiabhinavtej/pulseline.git
cd pulseline

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn python-jose passlib[bcrypt] pydantic python-multipart

# Initialize the database
python init_db.py

# Run the server
uvicorn main:app --reload
```

Then open `index.html` (or the served frontend route) in your browser to sign in and start a session.

---

## 📁 Project Structure

```
pulseline/
├── main.py                    # FastAPI app, routes, WebSocket + WebRTC signaling
├── auth.py                    # JWT issuance/validation, password hashing
├── crud.py                    # Database access layer
├── schema.py                  # Pydantic request/response models
├── utils.py                   # Helpers (avatars, BMI data, exceptions)
├── init_db.py                 # Database bootstrap
├── database.sql               # Full schema
├── login.html                 # Registration & login
├── doctor_dashboard.html      # Doctor-facing dashboard
├── patient_sessions.html      # Patient portal
├── in_call.html               # Live video consultation UI
├── waiting_room.html          # Pre-call waiting room
├── session_detail.html        # Active session room (chat + vitals)
├── report_submission.html     # Final consultation report
└── Excel/                     # WHO growth/BMI percentile reference data
```

---

## 🗺️ Roadmap

### For Doctors
- [ ] Create and manage consultation sessions
- [ ] View and edit doctor profile
- [ ] Track sessions marked as solved / completed
- [ ] One-tap emergency button for urgent cases

### For Patients
- [ ] Accept sessions initiated by a doctor
- [ ] In-session chat and video call
- [ ] View past session reports
- [ ] View and update personal medical data
- [ ] Graphical dashboard of personal health data

### Platform
- [ ] TURN server integration for WebRTC across restrictive networks
- [ ] Push notifications for emergency referrals

---

## 🤝 Contributing

This started as a personal project, but I'd genuinely love feedback, bug reports, or ideas. If something's broken or you've got a feature in mind, open an issue or fork it and send a pull request — always happy to talk through it.

---

**Pulseline** — a next-generation digital healthcare platform delivering secure telemedicine through real-time video consultations, intelligent emergency response, and centralized medical records.
