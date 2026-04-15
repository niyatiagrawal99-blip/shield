# ╔══════════════════════════════════════════════════════════════════╗
# ║   SHIELD — Police Health Monitor v6.0                           ║
# ║   Smart Health Intelligence & Emergency Life-care Dashboard     ║
# ║   Full Stack: Auth · Health Tracker · Hospital Network · Reports ║
# ║   + AI Extraction · SQLite Database · Clean Light UI            ║
# ║   FIXED: Data saving · Report sidebar · All tabs use DB data    ║
# ╚══════════════════════════════════════════════════════════════════╝

import streamlit as st
import json, os, datetime, re, hashlib, uuid, random, time
import sqlite3
import smtplib
from email.message import EmailMessage
from contextlib import contextmanager
import pandas as pd
import io

# ── Tesseract (optional – OCR) ────────────────────────────────────
import platform

try:
    import pytesseract

    OS_TYPE = platform.system()

    if OS_TYPE == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        POPPLER_PATH = r"C:\poppler\Library\bin"
    else:
        # Linux (Render / Cloud)
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        POPPLER_PATH = None

    TESSERACT_AVAILABLE = True

except ImportError:
    TESSERACT_AVAILABLE = False
    POPPLER_PATH = None
# ── Password hashing ──────────────────────────────────────────────
def hash_pw(password):
    """Hash a password using SHA-256 with salt."""
    salt = "SHIELD_SALT_2024"  # Simple salt for demo
    return hashlib.sha256((salt + password).encode()).hexdigest()

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="SHIELD — Police Health Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  SQLITE DATABASE BACKEND                                        ║
# ╚══════════════════════════════════════════════════════════════════╝
DB_PATH = "shield_v6.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            badge           TEXT PRIMARY KEY,
            password_hash   TEXT NOT NULL,
            name            TEXT,
            rank            TEXT,
            dept            TEXT,
            state           TEXT,
            gender          TEXT DEFAULT 'Male',
            dob             TEXT,
            age             INTEGER DEFAULT 30,
            phone           TEXT,
            blood_group     TEXT DEFAULT 'O+',
            allergies       TEXT,
            conditions      TEXT,
            medications     TEXT,
            email           TEXT,
            emergency_contact TEXT,
            emergency_phone TEXT,
            role            TEXT DEFAULT 'officer',
            uid             TEXT,
            registered      TEXT,
            reminder_months INTEGER DEFAULT 6,
            last_checkup    TEXT
        );

        CREATE TABLE IF NOT EXISTS admins (
            email           TEXT PRIMARY KEY,
            password_hash   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS health_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            badge           TEXT NOT NULL,
            record_date     TEXT NOT NULL,
            bp_systolic     REAL,
            bp_diastolic    REAL,
            heart_rate      REAL,
            sugar           REAL,
            cholesterol     REAL,
            haemoglobin     REAL,
            spo2            REAL,
            weight          REAL,
            height          REAL,
            bmi             REAL,
            ldl             REAL,
            hdl             REAL,
            triglycerides   REAL,
            creatinine      REAL,
            urea            REAL,
            uric_acid       REAL,
            tsh             REAL,
            wbc             REAL,
            rbc             REAL,
            platelets       REAL,
            hba1c           REAL,
            lab_name        TEXT,
            doctor_name     TEXT,
            diagnosis       TEXT,
            medicines       TEXT,
            notes           TEXT,
            source          TEXT DEFAULT 'Manual',
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (badge) REFERENCES users(badge)
        );

        CREATE TABLE IF NOT EXISTS hospitals (
            id       TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            address  TEXT,
            pincode  TEXT,
            phone    TEXT,
            type     TEXT DEFAULT 'General'
        );

        CREATE TABLE IF NOT EXISTS live_readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            badge       TEXT NOT NULL,
            reading_ts  TEXT,
            bp_sys      REAL,
            bp_dia      REAL,
            heart_rate  REAL,
            spo2        REAL,
            sugar       REAL,
            steps       INTEGER,
            device      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_health_badge ON health_records(badge);
        CREATE INDEX IF NOT EXISTS idx_live_badge   ON live_readings(badge);
        """)

def seed_hospitals():
    hospitals = [
        ("H1","G.T. Hospital (Government)","Near Police Commissioner Office, Fort, Mumbai – 400001","400001","022-22620000","Government"),
        ("H2","J.J. Hospital","Nagpada, Mumbai Central, Mumbai – 400008","400008","022-23735555","Government"),
        ("H3","K.E.M. Hospital","Parel, Mumbai – 400012","400012","022-24136051","Government"),
        ("H4","Saifee Hospital","Opera House, Girgaon, Mumbai – 400004","400004","022-67570111","Private"),
        ("H5","St. George Hospital (Government)","Fort (near CST), Mumbai – 400001","400001","022-22620343","Government"),
        ("H6","Bombay Hospital and Medical Research Centre","Marine Lines, Mumbai – 400020","400020","022-22067676","Private"),
        ("H7","Breach Candy Hospital","Breach Candy, Mumbai – 400026","400026","022-23667888","Private"),
        ("H8","Jaslok Hospital and Research Centre","Pedder Road, Mumbai – 400026","400026","022-66573333","Private"),
        ("H9","Lilavati Hospital and Research Centre","Bandra Reclamation, Bandra West, Mumbai – 400050","400050","022-26751000","Private"),
        ("H10","Nanavati Super Speciality Hospital","Vile Parle West, Mumbai – 400056","400056","022-26182222","Private"),
        ("H11","Kokilaben Dhirubhai Ambani Hospital","Four Bungalows, Andheri West, Mumbai – 400053","400053","022-30999999","Private"),
        ("H12","Fortis Hospital Mulund","Mulund West, Mumbai – 400078","400078","022-67971111","Private"),
        ("H13","Global Hospital Parel","Dr Ernest Borges Road, Parel, Mumbai – 400012","400012","022-67670101","Private"),
        ("H14","Wockhardt Hospital Mumbai Central","Agripada, Mumbai Central, Mumbai – 400011","400011","022-61784444","Private"),
        ("H15","SevenHills Hospital","Marol Maroshi Road, Andheri East, Mumbai – 400059","400059","022-33222222","Private"),
        ("H16","Cooper Hospital","Juhu, Vile Parle West, Mumbai – 400056","400056","022-26208888","Government"),
        ("H17","Holy Spirit Hospital","Mahakali Caves Road, Andheri East, Mumbai – 400093","400093","022-66955000","Private"),
        ("H18","S.L. Raheja Hospital","Raheja Raghunalaya Marg, Mahim, Mumbai – 400016","400016","022-66529999","Private"),
        ("H19","Smt. S.R. Mehta Hospital","Road No.31, Sion, Mumbai – 400019","400019","022-24017000","Government"),
        ("H20","Criticare Hospital","Gulmohar Road, Juhu, Mumbai – 400049","400049","022-26289999","Private"),
        ("H21","P.D. Hinduja Hospital","Veer Savarkar Marg, Mahim, Mumbai – 400016","400016","022-24447000","Private"),
    ]
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO hospitals(id,name,address,pincode,phone,type) VALUES(?,?,?,?,?,?)",
            hospitals
        )

def save_admin(email, password_hash):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO admins(email, password_hash) VALUES(?, ?)",
            (email, password_hash)
        )

def get_admin(email):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM admins WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

def send_admin_otp_email(to_email, otp):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    if not smtp_host or not smtp_user or not smtp_pass:
        return False, "SMTP is not configured. OTP will be shown in the app for demo login."
    try:
        msg = EmailMessage()
        msg["Subject"] = "SHIELD Admin OTP"
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg.set_content(
            f"Your SHIELD admin OTP is: {otp}\n\n" \
            "Use this OTP to complete admin login."
        )
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "OTP email sent successfully."
    except Exception as exc:
        return False, f"OTP email send failed: {exc}"

# ── User CRUD ─────────────────────────────────────────────────────
def normalize_badge(badge):
    return badge.strip().upper() if badge and isinstance(badge, str) else None

def get_user(badge):
    badge = normalize_badge(badge)
    if not badge:
        return None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE badge=?", (badge,)).fetchone()
        return dict(row) if row else None

def save_user(data: dict):
    if not data.get("badge"):
        return
    data["badge"] = normalize_badge(data["badge"])
    cols = list(data.keys())
    vals = [data[c] for c in cols]
    placeholders = ",".join("?" * len(cols))
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "badge")
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO users({','.join(cols)}) VALUES({placeholders}) "
            f"ON CONFLICT(badge) DO UPDATE SET {updates}",
            vals
        )

def update_user_field(badge, **kwargs):
    badge = normalize_badge(badge)
    if not badge or not kwargs:
        return
    sets = ",".join(f"{k}=?" for k in kwargs)
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {sets} WHERE badge=?", (*kwargs.values(), badge))


def send_admin_otp_email(to_email, otp):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    if not smtp_host or not smtp_user or not smtp_pass:
        return False, "SMTP is not configured. OTP will be shown in the app for demo login."
    try:
        msg = EmailMessage()
        msg["Subject"] = "SHIELD Admin OTP"
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg.set_content(
            f"Your SHIELD admin OTP is: {otp}\n\n" \
            "Use this OTP to complete admin login."
        )
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "OTP email sent successfully."
    except Exception as exc:
        return False, f"OTP email send failed: {exc}"


def seed_admin_user():
    with get_conn() as conn:
        row = conn.execute("SELECT badge FROM users WHERE role='admin' LIMIT 1").fetchone()
        if row:
            return
    save_user({
        "badge": "ADMIN-0001",
        "password_hash": hash_pw("Admin@123"),
        "name": "System Administrator",
        "rank": "Administrator",
        "dept": "Executive",
        "state": "Maharashtra",
        "gender": "Other",
        "dob": str(datetime.date.today()),
        "age": 30,
        "phone": "",
        "blood_group": "O+",
        "allergies": "",
        "conditions": "",
        "medications": "",
        "email": "admin@example.com",
        "emergency_contact": "",
        "emergency_phone": "",
        "role": "admin",
        "uid": str(uuid.uuid4()),
        "registered": str(datetime.date.today()),
        "reminder_months": 6,
        "last_checkup": str(datetime.date.today()),
    })

# ── Health Records CRUD ───────────────────────────────────────────
def get_health_records(badge):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM health_records WHERE badge=? ORDER BY record_date ASC, id ASC",
            (badge,)
        ).fetchall()
        return [dict(r) for r in rows]

def save_health_record(badge, record: dict):
    """FIX: Explicitly commits to DB and clears the record cache."""
    fields = {
        "badge": badge,
        "record_date":   record.get("record_date", str(datetime.date.today())),
        "bp_systolic":   _to_float(record.get("bp_systolic")),
        "bp_diastolic":  _to_float(record.get("bp_diastolic")),
        "heart_rate":    _to_float(record.get("heart_rate")),
        "sugar":         _to_float(record.get("sugar")),
        "cholesterol":   _to_float(record.get("cholesterol")),
        "haemoglobin":   _to_float(record.get("haemoglobin")),
        "spo2":          _to_float(record.get("spo2")),
        "weight":        _to_float(record.get("weight")),
        "height":        _to_float(record.get("height")),
        "bmi":           _to_float(record.get("bmi")),
        "ldl":           _to_float(record.get("ldl")),
        "hdl":           _to_float(record.get("hdl")),
        "triglycerides": _to_float(record.get("triglycerides")),
        "creatinine":    _to_float(record.get("creatinine")),
        "urea":          _to_float(record.get("urea")),
        "uric_acid":     _to_float(record.get("uric_acid")),
        "tsh":           _to_float(record.get("tsh")),
        "wbc":           _to_float(record.get("wbc")),
        "rbc":           _to_float(record.get("rbc")),
        "platelets":     _to_float(record.get("platelets")),
        "hba1c":         _to_float(record.get("hba1c")),
        "lab_name":      record.get("lab_name", "") or "",
        "doctor_name":   record.get("doctor_name", "") or "",
        "diagnosis":     record.get("diagnosis", "") or "",
        "medicines":     record.get("medicines", "") or "",
        "notes":         record.get("notes", "") or "",
        "source":        record.get("source", "Manual"),
    }
    cols = list(fields.keys())
    vals = [fields[c] for c in cols]
    placeholders = ",".join("?" * len(cols))
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO health_records({','.join(cols)}) VALUES({placeholders})",
                vals
            )
            row_id = cur.lastrowid
        # Clear the st.cache_data so all tabs refresh immediately
        get_health_records_cached.clear()
        return row_id
    except Exception as e:
        st.error(f"Failed to save health record: {e}")
        return None

def _to_float(v):
    """Safely convert to float, extract number if mixed text."""
    if v is None:
        return None
    try:
        import re
        match = re.findall(r'\d+\.?\d*', str(v))
        if not match:
            return None
        f = float(match[0])
        return f if not (f != f) else None
    except:
        return None
@st.cache_data(ttl=0)
def get_health_records_cached(badge):
    """Cached wrapper — cleared on every save to force refresh."""
    return get_health_records(badge)

def get_all_health_records():
    """Get all health records from all users for admin dashboard."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT hr.*, u.name, u.dept, u.rank
            FROM health_records hr
            JOIN users u ON hr.badge = u.badge
            ORDER BY hr.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

# ── Hospital queries ──────────────────────────────────────────────
def get_hospitals(search=""):
    with get_conn() as conn:
        if search:
            rows = conn.execute(
                "SELECT * FROM hospitals WHERE name LIKE ? OR address LIKE ? ORDER BY id",
                (f"%{search}%", f"%{search}%")
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM hospitals ORDER BY id").fetchall()
        return [dict(r) for r in rows]

# ── Init ──────────────────────────────────────────────────────────
# ╔══════════════════════════════════════════════════════════════════╗
# ║  GLOBAL CSS — TRUE LIGHT THEME + PROFESSIONAL DESIGN           ║
# ╚══════════════════════════════════════════════════════════════════╝
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

:root {
  --bg:           #f4f6fb;
  --bg2:          #eaeff8;
  --bg3:          #dde5f5;
  --panel:        #ffffff;
  --border:       #cdd7ee;
  --border2:      #b8c8e8;
  --navy:         #0d1e4a;
  --navy2:        #1a3280;
  --gold:         #b8720a;
  --gold2:        #d9880c;
  --gold3:        #f0a020;
  --goldbg:       #fef3e2;
  --teal:         #0b6e62;
  --teal2:        #0f9a8a;
  --blue:         #1a4fd6;
  --blue2:        #3d6ef5;
  --text:         #0d1e4a;
  --text2:        #2d3f6b;
  --text3:        #5a6f99;
  --ok:           #0a6b3e;
  --ok-bg:        #e8faf2;
  --ok-border:    #7adcb0;
  --warn:         #895008;
  --warn-bg:      #fff8eb;
  --warn-border:  #f5cc72;
  --danger:       #a81515;
  --danger-bg:    #fef1f1;
  --danger-border:#f4a0a0;
  --shadow-sm:    0 1px 4px rgba(13,30,74,.07);
  --shadow-md:    0 4px 18px rgba(13,30,74,.12);
  --shadow-lg:    0 10px 40px rgba(13,30,74,.16);
  --r:            14px;
}

/* ── RESET EVERYTHING TO LIGHT ── */
html, body, [class*="css"], .main, .block-container,
.stApp, section.main, div[data-testid="stAppViewContainer"],
div[data-testid="stAppViewBlockContainer"] {
  background: var(--bg) !important;
  color: var(--text) !important;
}

.main .block-container {
  background: var(--bg) !important;
  padding: 1.4rem 2rem 2.5rem !important;
  max-width: 1380px !important;
}

/* ── Force all text to be dark ── */
p, li, span, div, label,
.stMarkdown p, .stMarkdown li, .stMarkdown span,
.element-container div, .stText {
  color: var(--text) !important;
}
h1, h2, h3, h4, h5, h6 {
  color: var(--navy) !important;
  font-family: 'Rajdhani', sans-serif !important;
  font-weight: 700 !important;
}

/* ── SIDEBAR (light theme) ── */
section[data-testid="stSidebar"] {
  background: #f8fafc !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] label {
  color: var(--navy) !important;
}
section[data-testid="stSidebar"] .stButton > button {
  background: #ffffff !important;
  color: var(--navy) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 9px !important;
  text-align: left !important;
  font-size: .88rem !important;
  font-weight: 500 !important;
  padding: .5rem .9rem !important;
  margin-bottom: .18rem !important;
  transition: all .18s !important;
  width: 100% !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--goldbg) !important;
  border-color: var(--gold2) !important;
  color: var(--navy) !important;
}
section[data-testid="stSidebar"] .stButton > button.active-nav,
section[data-testid="stSidebar"] .stButton > button[aria-pressed="true"] {
  background: rgba(240,160,32,.15) !important;
  border-color: rgba(240,160,32,.5) !important;
  color: var(--navy) !important;
}

/* ── Report sidebar panel ── */
.report-panel {
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 14px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow-sm);
}
.report-panel-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--gold2) !important;
  margin-bottom: .7rem;
  padding-bottom: .5rem;
  border-bottom: 1.5px solid var(--border);
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stSelectbox select, div[data-baseweb="select"] {
  background: #fff !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 9px !important;
  color: var(--text) !important;
  font-size: .9rem !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: var(--gold2) !important;
  box-shadow: 0 0 0 3px rgba(217,136,12,.12) !important;
}
.stDateInput input {
  background: #fff !important;
  color: var(--text) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 9px !important;
}
.stSlider [data-baseweb="slider"] div {
  background: var(--border2) !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: var(--gold2) !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(135deg, var(--gold2), var(--teal2)) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 10px !important;
  font-family: 'Rajdhani', sans-serif !important;
  font-weight: 700 !important;
  font-size: .95rem !important;
  letter-spacing: .5px !important;
  padding: .65rem 1.5rem !important;
  transition: all .2s !important;
  box-shadow: 0 3px 14px rgba(240,160,32,.18) !important;
}
.stButton > button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
  background: linear-gradient(135deg, var(--teal2), var(--gold2)) !important;
  box-shadow: 0 6px 20px rgba(240,160,32,.24) !important;
  transform: translateY(-1px) !important;
}

/* ── Secondary button (main area) ── */
.stButton > button {
  background: #fff !important;
  color: var(--navy) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  transition: all .18s !important;
}
.stButton > button:hover {
  border-color: var(--gold2) !important;
  color: var(--gold2) !important;
  background: var(--goldbg) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg2) !important;
  border-radius: 12px !important;
  padding: .3rem !important;
  gap: .2rem !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text2) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: .88rem !important;
  border: none !important;
  padding: .45rem 1rem !important;
  transition: all .18s !important;
}
.stTabs [aria-selected="true"] {
  background: #fff !important;
  color: var(--navy) !important;
  box-shadow: var(--shadow-sm) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  background: transparent !important;
  padding: 1rem 0 0 !important;
}

/* ── Alerts ── */
.stAlert { border-radius: 10px !important; }
.stSuccess { background: var(--ok-bg) !important; border-color: var(--ok-border) !important; }
.stWarning { background: var(--warn-bg) !important; }
.stInfo    { background: var(--bg2) !important; border-color: var(--border2) !important; }
.stError   { background: var(--danger-bg) !important; }

/* ── Expander ── */
.stExpander { border: 1.5px solid var(--border) !important; border-radius: 12px !important; background: #fff !important; }
.stExpander summary { font-weight: 600 !important; color: var(--navy) !important; }

/* ── Dataframe ── */
.stDataFrame { border-radius: 12px !important; border: 1.5px solid var(--border) !important; overflow: hidden; }
.stDataFrame th { background: var(--bg3) !important; color: var(--navy) !important; font-weight: 700 !important; }

/* ── Cards ── */
.card {
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 16px;
  padding: 1.4rem 1.5rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow-sm);
}
.card-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: .76rem;
  font-weight: 700;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--gold2) !important;
  margin-bottom: .9rem;
  padding-bottom: .6rem;
  border-bottom: 1.5px solid var(--border);
}

/* ── Page header ── */
.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.4rem;
  padding: 1.2rem 1.6rem;
  background: linear-gradient(135deg, #fff 60%, var(--bg2) 100%);
  border: 1.5px solid var(--border);
  border-left: 5px solid var(--gold2);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
}
.page-header-icon { font-size: 2.2rem; }
.page-header h1 {
  font-family: 'Rajdhani', sans-serif;
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--navy) !important;
  margin: 0;
  line-height: 1.1;
}
.page-header p {
  font-size: .84rem;
  color: var(--text3) !important;
  margin: .2rem 0 0;
  font-weight: 500;
}

/* ── Welcome card (dark) ── */
.welcome-card {
  background: linear-gradient(135deg, #ffffff 0%, #f4f6fb 100%);
  border: 1.5px solid var(--border);
  border-radius: 20px;
  padding: 1.8rem 2.2rem;
  margin-bottom: 1.4rem;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}
.welcome-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, var(--gold3), var(--teal2), var(--gold3));
}
.wc-greet { font-family: 'Rajdhani', sans-serif; font-size: .85rem; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: var(--gold3) !important; margin-bottom: .3rem; }
.wc-name  { font-family: 'Rajdhani', sans-serif; font-size: 2.2rem; font-weight: 700; color: #fff !important; line-height: 1.1; }
.wc-sub   { font-size: .86rem; color: var(--text2) !important; margin-top: .5rem; font-weight: 400; }

/* ── Metric cards ── */
.mc {
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 14px;
  padding: 1.1rem 1.2rem;
  text-align: center;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: box-shadow .2s;
}
.mc::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 3px;
  background: var(--mc-accent, var(--gold2));
}
.mc:hover { box-shadow: var(--shadow-md); }
.mc-lbl  { font-size: .66rem; font-weight: 700; letter-spacing: 1.3px; text-transform: uppercase; color: var(--text3) !important; margin-bottom: .45rem; }
.mc-val  { font-family: 'Rajdhani', sans-serif; font-size: 2.2rem; font-weight: 700; color: var(--navy) !important; line-height: 1; }
.mc-unit { font-size: .68rem; color: var(--text3) !important; margin-bottom: .5rem; font-weight: 600; }

/* ── Pills ── */
.pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .4px;
  text-transform: uppercase;
}
.p-ok     { background: var(--ok-bg);     color: var(--ok)    !important; border: 1px solid var(--ok-border); }
.p-warn   { background: var(--warn-bg);   color: var(--warn)  !important; border: 1px solid var(--warn-border); }
.p-danger { background: var(--danger-bg); color: var(--danger)!important; border: 1px solid var(--danger-border); }
.p-navy   { background: var(--bg3);       color: var(--navy)  !important; border: 1px solid var(--border2); }
.p-blue   { background: #eff4ff;          color: var(--blue)  !important; border: 1px solid #c3d3f8; }
.p-teal   { background: #e8faf6;          color: var(--teal)  !important; border: 1px solid #9de8d8; }
.p-gold   { background: var(--goldbg);    color: var(--gold)  !important; border: 1px solid #f5cc72; }

/* ── Data row ── */
.dr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .55rem .1rem;
  border-bottom: 1px solid var(--border);
  font-size: .88rem;
}
.dr:last-child { border-bottom: none; }
.dr-k { color: var(--text3) !important; font-weight: 600; font-size: .82rem; }
.dr-v { color: var(--navy) !important; font-weight: 700; font-family: 'Rajdhani', sans-serif; font-size: .95rem; }

/* ── Nav label ── */
.nl {
  font-family: 'Rajdhani', sans-serif;
  font-size: .6rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(184,114,10,.7) !important;
  padding: .6rem .5rem .2rem;
  margin-top: .3rem;
}

/* ── Profile box (sidebar) ── */
.pb {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: .9rem 1rem;
  margin: .5rem 0 .8rem;
}
.pb-rank { font-family: 'Rajdhani', sans-serif; font-size: .68rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--gold2) !important; margin-bottom: .2rem; }
.pb-name { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--navy) !important; }
.pb-dept { font-size: .76rem; color: var(--text2) !important; margin-top: .2rem; font-weight: 500; }

/* ── Donut widget ── */
.dw {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: .4rem;
  padding: .8rem;
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
}
.dl { font-family: 'Rajdhani', sans-serif; font-size: .78rem; font-weight: 700; color: var(--text2) !important; letter-spacing: .5px; text-align: center; }

/* ── Stat bar ── */
.sb-wrap { margin-bottom: .7rem; }
.sb-head { display: flex; justify-content: space-between; margin-bottom: .3rem; }
.sb-name { font-size: .82rem; font-weight: 600; color: var(--text2) !important; }
.sb-val  { font-family: 'Rajdhani', sans-serif; font-size: .88rem; font-weight: 700; color: var(--navy) !important; }
.sb-bg   { background: var(--bg3); border-radius: 100px; height: 8px; overflow: hidden; }
.sb-fill { height: 100%; border-radius: 100px; transition: width .6s ease; }

/* ── Hero banner ── */
.hero-banner {
  background: linear-gradient(135deg, #ffffff 0%, #f4f6fb 100%);
  border: 1.5px solid var(--border);
  border-radius: 22px;
  padding: 3.5rem 3rem 2.5rem;
  margin-bottom: 1.6rem;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  color: var(--navy) !important;
}
.hero-banner::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, var(--gold3), var(--teal2), var(--gold3));
}
.hero-deco {
  position: absolute; right: 3rem; top: 50%; transform: translateY(-50%);
  font-size: 8rem; opacity: .08;
  color: var(--gold3);
}
.hero-badge {
  display: inline-block;
  background: rgba(240,160,32,.12);
  border: 1px solid rgba(240,160,32,.18);
  border-radius: 20px;
  padding: .3rem 1rem;
  font-family: 'Rajdhani', sans-serif;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--gold2) !important;
  margin-bottom: .9rem;
}
.hero-stats {
  display: flex; gap: 2rem; flex-wrap: wrap; margin-top: 1.8rem;
}
.hero-stat-val { font-family: 'Rajdhani', sans-serif; font-size: 1.8rem; font-weight: 700; color: #f0a020 !important; }
.hero-stat-lbl { font-size: .7rem; color: #7a96c4 !important; letter-spacing: .5px; font-weight: 500; }

/* ── Info card ── */
.ic {
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 14px;
  padding: 1.3rem;
  box-shadow: var(--shadow-sm);
  transition: all .2s;
}
.ic:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: var(--gold2); }
.ic-icon  { font-size: 1.7rem; margin-bottom: .6rem; }
.ic-title { font-family: 'Rajdhani', sans-serif; font-size: .95rem; font-weight: 700; color: var(--navy) !important; margin-bottom: .35rem; }
.ic-text  { font-size: .84rem; color: var(--text2) !important; line-height: 1.7; font-weight: 400; }

/* ── Schedule row ── */
.sr {
  display: flex; justify-content: space-between; align-items: center;
  padding: .85rem 1.2rem; border-radius: 10px;
  background: #fff; border: 1.5px solid var(--border);
  margin-bottom: .5rem; box-shadow: var(--shadow-sm);
}

/* ── Auth card ── */
.auth-card {
  background: #fff; border: 1.5px solid var(--border);
  border-radius: 20px; padding: 2.2rem 2rem;
  box-shadow: var(--shadow-lg);
}

/* ── Report param card ── */
.rpc {
  background: #fff; border: 1.5px solid var(--border);
  border-radius: 12px; padding: .9rem 1rem; text-align: center;
  position: relative; overflow: hidden; margin-bottom: .5rem;
  box-shadow: var(--shadow-sm); transition: box-shadow .2s;
}
.rpc:hover { box-shadow: var(--shadow-md); border-color: var(--gold2); }
.rpc::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--param-color, var(--gold2));
}
.rpc-label { font-size: .64rem; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; color: var(--text3) !important; margin-bottom: .35rem; }
.rpc-value { font-family: 'Rajdhani', sans-serif; font-size: 1.8rem; font-weight: 700; color: var(--navy) !important; }
.rpc-unit  { font-size: .7rem; color: var(--text3) !important; margin-bottom: .45rem; font-weight: 600; }

/* ── AI extraction table ── */
.ai-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.ai-table th {
  background: var(--bg3); color: var(--navy) !important;
  font-family: 'Rajdhani', sans-serif; font-size: .78rem; font-weight: 700;
  letter-spacing: 1.2px; text-transform: uppercase;
  padding: .7rem .9rem; text-align: left;
  border-bottom: 2px solid var(--border2);
}
.ai-table td {
  padding: .65rem .9rem; border-bottom: 1px solid var(--border);
  color: var(--text) !important; font-weight: 500; vertical-align: top;
}
.ai-table tr:last-child td { border-bottom: none; }
.ai-table tr:hover td { background: var(--bg2); }
.ai-table td:first-child { color: var(--text2) !important; font-weight: 700; min-width: 160px; }
.ai-table td.val { font-family: 'Rajdhani', sans-serif; color: var(--navy) !important; font-weight: 700; font-size: 1rem; }

/* ── History table ── */
.hist-table { width: 100%; border-collapse: collapse; }
.hist-table th {
  background: var(--bg3); color: var(--navy) !important;
  font-family: 'Rajdhani', sans-serif; font-size: .76rem; font-weight: 700;
  letter-spacing: 1.2px; text-transform: uppercase;
  padding: .65rem .85rem; text-align: left;
  border-bottom: 2px solid var(--border2);
}
.hist-table td {
  padding: .65rem .85rem; border-bottom: 1px solid var(--border);
  font-size: .87rem; color: var(--text) !important; font-weight: 500; vertical-align: middle;
}
.hist-table tr:last-child td { border-bottom: none; }
.hist-table tr:hover td { background: var(--bg2); }
.hist-table td.num { font-family: 'Rajdhani', sans-serif; font-weight: 700; color: var(--navy) !important; font-size: .95rem; }

/* ── Summary card (light) ── */
.sumcard {
  background: #ffffff;
  border: 1.5px solid var(--border);
  border-radius: 18px; padding: 1.8rem 2rem;
  position: relative; overflow: hidden;
  box-shadow: var(--shadow-lg);
}
.sumcard::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, var(--gold3), var(--teal2), var(--gold3));
}
.sumcard-name { font-family: 'Rajdhani', sans-serif; font-size: 1.6rem; font-weight: 700; color: var(--navy) !important; }
.sumcard-diag { font-size: .87rem; color: var(--text2) !important; font-weight: 400; margin-top: .3rem; }

/* ── Section divider label ── */
.sec-label {
  font-family: 'Rajdhani', sans-serif; font-size: .76rem;
  font-weight: 700; color: var(--gold2) !important;
  letter-spacing: 2px; text-transform: uppercase;
  margin: 1.5rem 0 .8rem; padding-bottom: .5rem;
  border-bottom: 1.5px solid var(--border);
  display: flex; align-items: center; gap: 8px;
}

/* ── Footer ── */
.af {
  text-align: center; padding: 1.2rem 0 .5rem;
  border-top: 1.5px solid var(--border);
  margin-top: 2.5rem;
  font-size: .76rem; letter-spacing: .3px; font-weight: 500;
}
.af, .af * { color: var(--text3) !important; }
.af b { color: var(--gold2) !important; font-weight: 700 !important; }

/* ── Landing Feature Cards ── */
.feat-card {
  background: #fff; border: 1.5px solid var(--border);
  border-radius: 16px; padding: 1.5rem;
  box-shadow: var(--shadow-sm); transition: all .22s;
  height: 100%; position: relative; overflow: hidden;
}
.feat-card::before {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
  background: var(--feat-color, var(--gold2)); opacity: 0;
  transition: opacity .22s;
}
.feat-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); border-color: var(--gold2); }
.feat-card:hover::before { opacity: 1; }
.feat-card-icon { font-size: 2.2rem; margin-bottom: .7rem; }
.feat-card-title { font-family: 'Rajdhani', sans-serif; font-size: 1.05rem; font-weight: 700; color: var(--navy) !important; margin-bottom: .4rem; }
.feat-card-text  { font-size: .84rem; color: var(--text2) !important; line-height: 1.75; font-weight: 400; }

/* ── Step cards ── */
.step-card {
  background: #fff; border: 1.5px solid var(--border);
  border-radius: 16px; padding: 1.8rem 1.5rem;
  box-shadow: var(--shadow-sm); text-align: center;
  position: relative; overflow: hidden; transition: all .22s;
}
.step-card:hover { box-shadow: var(--shadow-md); border-color: var(--gold2); transform: translateY(-3px); }
.step-card::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: var(--step-color, var(--gold2));
}
.step-num {
  font-family: 'Rajdhani', sans-serif;
  font-size: 3.5rem; font-weight: 700;
  color: rgba(13,30,74,.06) !important; line-height: 1; margin-bottom: .3rem;
}
.step-icon { font-size: 2rem; margin-bottom: .6rem; }
.step-title { font-family: 'Rajdhani', sans-serif; font-size: 1rem; font-weight: 700; color: var(--navy) !important; margin-bottom: .35rem; }
.step-text  { font-size: .83rem; color: var(--text2) !important; line-height: 1.7; font-weight: 400; }

/* ── Stats strip (light) ── */
.stats-strip {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 16px; padding: 1.7rem 2.5rem;
  display: flex; justify-content: space-around; align-items: center;
  flex-wrap: wrap; gap: 1rem;
  box-shadow: var(--shadow-lg);
  margin-bottom: 2.5rem; position: relative; overflow: hidden;
}
.stats-strip::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--gold3), var(--teal2), var(--gold3));
}
.stats-strip-item { text-align: center; }
.stats-strip-val { font-family: 'Rajdhani', sans-serif; font-size: 2.2rem; font-weight: 700; color: #f0a020 !important; }
.stats-strip-lbl { font-size: .73rem; color: #7a96c4 !important; letter-spacing: .6px; font-weight: 500; }

/* ── Quote/Testimonial ── */
.quote-card {
  background: #fff; border: 1.5px solid var(--border);
  border-top: 4px solid var(--gold2);
  border-radius: 14px;
  padding: 1.4rem 1.5rem; margin-bottom: .8rem;
  box-shadow: var(--shadow-sm); transition: all .2s;
}
.quote-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.quote-mark { font-size: 2.5rem; color: rgba(184,114,10,.2) !important; line-height: .5; margin-bottom: .5rem; font-family: Georgia, serif; }
.quote-text { font-size: .9rem; color: var(--text2) !important; line-height: 1.75; font-weight: 400; font-style: italic; }
.quote-author { font-size: .78rem; color: var(--gold2) !important; font-weight: 700; margin-top: .7rem; letter-spacing: .3px; }
.quote-rank { font-size: .72rem; color: var(--text3) !important; font-weight: 500; }

/* ── Alert banner on landing ── */
.stat-alert {
  background: linear-gradient(135deg, #fff7ed, #fffaf0);
  border: 1.5px solid var(--warn-border);
  border-left: 5px solid var(--gold2);
  border-radius: 12px; padding: 1.1rem 1.4rem;
  margin-bottom: 1.2rem; display: flex; align-items: center; gap: 1rem;
}
.stat-alert-icon { font-size: 1.8rem; }
.stat-alert-text { font-size: .9rem; color: var(--warn) !important; font-weight: 600; line-height: 1.6; }

/* ── OCR Error box ── */
.ocr-error {
  background: var(--danger-bg);
  border: 1.5px solid var(--danger-border);
  border-left: 5px solid var(--danger);
  border-radius: 12px; padding: 1rem 1.3rem;
  margin: .8rem 0; font-size: .88rem; color: var(--danger) !important; font-weight: 600;
}
.ocr-error pre { background: transparent !important; color: var(--danger) !important; font-size: .82rem; margin-top: .5rem; white-space: pre-wrap; }

/* ── Save success banner ── */
.save-success {
  background: linear-gradient(135deg, #e8faf2, #f0fdf6);
  border: 2px solid #7adcb0;
  border-left: 6px solid #059669;
  border-radius: 14px; padding: 1.2rem 1.5rem;
  margin: 1rem 0; display: flex; align-items: center; gap: 1rem;
  box-shadow: 0 4px 16px rgba(5,150,105,.12);
}
.save-success-icon { font-size: 2rem; }
.save-success-text { font-size: .95rem; color: #064e30 !important; font-weight: 700; line-height: 1.6; }

/* ── Alert boxes ── */
.alert-box {
  border-radius: 12px; padding: .9rem 1.2rem; margin: .5rem 0;
  font-size: .88rem; font-weight: 600;
}
.alert-ok     { background: var(--ok-bg);     border: 1.5px solid var(--ok-border);     color: var(--ok)     !important; border-left: 5px solid #059669; }
.alert-warn   { background: var(--warn-bg);   border: 1.5px solid var(--warn-border);   color: var(--warn)   !important; border-left: 5px solid #d97706; }
.alert-danger { background: var(--danger-bg); border: 1.5px solid var(--danger-border); color: var(--danger) !important; border-left: 5px solid #dc2626; }

/* ── Hospital card ── */
.hosp-card {
  background: #fff; border: 1.5px solid var(--border);
  border-radius: 14px; padding: 1.1rem 1.3rem;
  margin-bottom: .7rem; box-shadow: var(--shadow-sm);
  transition: all .2s;
}
.hosp-card:hover { box-shadow: var(--shadow-md); border-color: var(--gold2); transform: translateY(-2px); }
.hosp-name { font-family: 'Rajdhani', sans-serif; font-size: 1.05rem; font-weight: 700; color: var(--navy) !important; }
.hosp-addr { font-size: .82rem; color: var(--text2) !important; margin-top: .2rem; line-height: 1.5; }

/* ── Sidebar report summary ── */
.sb-report-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: .3rem 0; border-bottom: 1px solid var(--border); font-size: .76rem;
}
.sb-report-k { color: var(--text3) !important; font-weight: 500; }
.sb-report-v { color: var(--navy) !important; font-weight: 700; font-family: 'Rajdhani', sans-serif; font-size: .88rem; }


/* ── BMI Gauge ── */
.bmi-gauge-wrap { background:#fff; border:1.5px solid var(--border); border-radius:14px; padding:1.2rem; box-shadow:var(--shadow-sm); text-align:center; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Fix dropdown / expander dark background */
div[data-baseweb="select"],
div[data-baseweb="popover"],
div[data-baseweb="menu"] {
    background-color: #ffffff !important;
}

/* Fix expander */
details, details summary {
    background: #ffffff !important;
}

/* Fix general container override issue */
[class*="css"] {
    background: unset !important;
}
</style>
""", unsafe_allow_html=True)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  HEALTH CLASSIFICATION LOGIC                                    ║
# ╚══════════════════════════════════════════════════════════════════╝
def classify_bp(s, d):
    s, d = float(s or 0), float(d or 0)
    if s < 120 and d < 80: return "Normal", "p-ok"
    if s < 130 and d < 80: return "Elevated", "p-warn"
    if s < 140 or d < 90:  return "High Stg.1", "p-warn"
    return "High Stg.2", "p-danger"

def classify_sugar(v):
    v = float(v or 0)
    if v < 100: return "Normal", "p-ok"
    if v < 126: return "Pre-Diabetic", "p-warn"
    return "Diabetic", "p-danger"

def classify_chol(v):
    v = float(v or 0)
    if v < 200: return "Desirable", "p-ok"
    if v < 240: return "Borderline", "p-warn"
    return "High", "p-danger"

def classify_hb(v, gender="Male"):
    v = float(v or 0)
    low = 13.5 if gender == "Male" else 12.0
    if v >= low: return "Normal", "p-ok"
    if v >= low - 1: return "Mild Anaemia", "p-warn"
    return "Anaemia", "p-danger"

def classify_spo2(v):
    v = float(v or 0)
    if v >= 95: return "Normal", "p-ok"
    if v >= 90: return "Low", "p-warn"
    return "Critical", "p-danger"

def classify_bmi(v):
    v = float(v or 0)
    if v < 18.5: return "Underweight", "p-warn"
    if v < 25:   return "Normal", "p-ok"
    if v < 30:   return "Overweight", "p-warn"
    return "Obese", "p-danger"

def classify_hr(v):
    v = float(v or 0)
    if 60 <= v <= 100: return "Normal", "p-ok"
    if v < 60: return "Low (Brady)", "p-warn"
    return "High (Tachy)", "p-danger"

def fitness_score(bs, bd, sg, ch, hb, spo2, age, gender="Male"):
    s = 100
    bs, bd = float(bs or 120), float(bd or 80)
    sg, ch = float(sg or 90),  float(ch or 190)
    hb     = float(hb or 14);  spo2 = float(spo2 or 98)
    if bs >= 140 or bd >= 90: s -= 20
    elif bs >= 130: s -= 10
    elif bs >= 120: s -= 4
    if sg >= 126: s -= 15
    elif sg >= 100: s -= 7
    if ch >= 240: s -= 15
    elif ch >= 200: s -= 7
    low_hb = 13.5 if gender == "Male" else 12.0
    if hb < low_hb - 1: s -= 10
    elif hb < low_hb:   s -= 5
    if spo2 < 90: s -= 20
    elif spo2 < 95: s -= 10
    if age > 50: s -= 5
    elif age > 40: s -= 2
    return max(0, min(100, s))

def get_suggestions(bs, bd, sg, ch):
    tips = []
    if float(bs or 0) >= 130 or float(bd or 0) >= 80:
        tips += ["Limit sodium to under 2,300 mg/day.",
                 "Practice 4-7-8 breathing: inhale 4s, hold 7s, exhale 8s.",
                 "Avoid overtime shifts when BP is elevated."]
    if float(sg or 0) >= 100:
        tips += ["Avoid sugary drinks and white rice during night shifts.",
                 "Walk 10 minutes after every meal, even during duty."]
    if float(ch or 0) >= 200:
        tips += ["Eat oats, flaxseed, and walnuts regularly.",
                 "Replace fried canteen food with boiled/grilled options."]
    if not tips:
        tips = ["Outstanding health metrics — maintain your discipline.",
                "Share your healthy habits with fellow officers."]
    tips += ["Drink water every hour on duty — dehydration affects judgement.",
             "Sleep 7h minimum; avoid screens 1 hour before bed.",
             "Annual eye and dental checkup are free at police hospital."]
    return tips

def stress_score(sleep, workload, exercise, social):
    s = max(0, (7 - sleep) * 10) + workload * 7 + max(0, (3 - exercise) * 8) + max(0, (5 - social) * 4)
    return min(100, s)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  OCR ENGINE                                                     ║
# ╚══════════════════════════════════════════════════════════════════╝
def preprocess_image(img):
    from PIL import ImageEnhance, ImageFilter
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if w < 1200:
        scale = 1200 / w
        from PIL import Image
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return img

def extract_text_ocr(uploaded):
    if not TESSERACT_AVAILABLE:
        return "", "Tesseract is not installed or not found at the configured path."
    try:
        from PIL import Image
        import io
        file_bytes = uploaded.getvalue()
        file_type  = uploaded.type.lower()
        is_pdf     = "pdf" in file_type or uploaded.name.lower().endswith(".pdf")
        if is_pdf:
            try:
                from pdf2image import convert_from_bytes
            except ImportError:
                return "", "pdf2image is not installed.\nRun: pip install pdf2image"
            try:
                if POPPLER_PATH:
                  pages = convert_from_bytes(file_bytes, dpi=300, poppler_path=POPPLER_PATH)
                else:   
                  pages = convert_from_bytes(file_bytes, dpi=300)
            except Exception as e:
                return "", f"pdf2image conversion failed:\n{str(e)}"
            all_text = []
            for page_num, page_img in enumerate(pages, 1):
                try:
                    processed  = preprocess_image(page_img)
                    page_text  = pytesseract.image_to_string(processed, config="--oem 3 --psm 6")
                    all_text.append(page_text)
                except Exception as e:
                    all_text.append(f"[Page {page_num} OCR error: {e}]")
            combined = "\n".join(all_text).strip()
            if not combined:
                return "", "OCR ran but extracted no text from the PDF."
            return combined, None
        else:
            try:
                img = Image.open(io.BytesIO(file_bytes))
            except Exception as e:
                return "", f"Could not open image file: {str(e)}"
            try:
                processed = preprocess_image(img)
                text = pytesseract.image_to_string(processed, config="--oem 3 --psm 6")
            except Exception as e:
                return "", f"Tesseract OCR failed on image: {str(e)}"
            if not text.strip():
                return "", "OCR extracted no text from the image."
            return text.strip(), None
    except Exception as e:
        return "", f"Unexpected OCR error: {str(e)}"

def clean_ocr_text(raw: str) -> str:
    lines = raw.splitlines()
    clean = []
    for line in lines:
        line = line.strip()
        if len(line) < 2: continue
        if re.match(r'^[\W_]+$', line): continue
        clean.append(line)
    return "\n".join(clean)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  AI REPORT EXTRACTION ENGINE                                    ║
# ╚══════════════════════════════════════════════════════════════════╝
def extract_all_fields(text: str) -> dict:
    import re
    result = {}
    t = re.sub(r'\s+', ' ', text.lower())

    # ── PATIENT INFO ──
    for pat in [
        r'(?:patient(?:\s+name)?|name\s+of\s+patient|pt\.?\s+name)[:\s]+([a-z][a-z\s\.]{2,35})',
        r'(?:mr\.|mrs\.|ms\.|dr\.)\s+([a-z][a-z\s\.]{2,30})',
        r'(?:^|\n)name\s*[:\-]\s*([a-z][a-z\s\.]{2,30})',
    ]:
        m = re.search(pat, t, re.I | re.MULTILINE)
        if m:
            result["Patient Name"] = m.group(1).strip().title()
            break

    m = re.search(r'(?:age|patient\s+age)[:\s]*(\d{1,3})', t)
    if m:
        result["Age"] = m.group(1)

    m = re.search(r'(?:gender|sex)[:\s]*(male|female|m|f)', t)
    if m:
        g = m.group(1)
        result["Gender"] = "Male" if g in ["m", "male"] else "Female"

    # ── BLOOD PRESSURE ──
    for pat in [
        r'(?:blood\s*pressure|b\.?p\.?)[:\s=]+(\d{2,3})\s*/\s*(\d{2,3})',
        r'(\d{2,3})\s*/\s*(\d{2,3})'
    ]:
        m = re.search(pat, t)
        if m:
            result["BP Systolic (mmHg)"] = m.group(1)
            result["BP Diastolic (mmHg)"] = m.group(2)
            break

    # ── SUGAR ──
    m = re.search(r'(?:sugar|glucose)[^\d]*(\d{2,3})', t)
    if m:
        result["Fasting Blood Sugar (mg/dL)"] = m.group(1)

    # ── CHOLESTEROL ──
    m = re.search(r'cholesterol[^\d]*(\d{2,3})', t)
    if m:
        result["Cholesterol (mg/dL)"] = m.group(1)

    # ── HAEMOGLOBIN ──
    m = re.search(r'(?:hb|hemoglobin)[^\d]*(\d{1,2}\.?\d?)', t)
    if m:
        result["Haemoglobin (g/dL)"] = m.group(1)

    # ── HEART RATE ──
    m = re.search(r'(?:pulse|heart rate)[^\d]*(\d{2,3})', t)
    if m:
        result["Heart Rate (bpm)"] = m.group(1)

    # ── SPO2 ──
    m = re.search(r'(?:spo2|oxygen)[^\d]*(\d{2,3})', t)
    if m:
        result["SpO2 (%)"] = m.group(1)

    # ── FALLBACK (IMPORTANT) ──
    numbers = re.findall(r'\b\d{1,3}(?:\.\d+)?\b', t)
    if numbers:
        result["Detected Numbers"] = ", ".join(numbers[:10])

    return result
# ╔══════════════════════════════════════════════════════════════════╗
# ║  SESSION STATE                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝
DEFAULTS = {
    "logged_in": False, "username": "", "page": "Landing",
    "role": "officer", "forgot_pw_mode": False,
    "admin_mode": False, "admin_otp_sent": False,
    "admin_signup_mode": False,
    "record_just_saved": False,
    "save_ts": 0,  # timestamp of last save — used to force refresh
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def logout():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v

# ╔══════════════════════════════════════════════════════════════════╗
# ║  UI HELPERS                                                     ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_header(icon, title, sub=""):
    st.markdown(f"""<div class="page-header">
      <div class="page-header-icon">{icon}</div>
      <div><h1>{title}</h1><p>{sub}</p></div>
    </div>""", unsafe_allow_html=True)

def card_open(title=""):
    if title:
        st.markdown(f'<div class="card"><div class="card-title">{title}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)

def card_close():
    st.markdown("</div>", unsafe_allow_html=True)

def metric_card(lbl, val, unit, status_txt, status_cls, accent="#d9880c"):
    return f"""<div class="mc" style="--mc-accent:{accent}">
      <div class="mc-lbl">{lbl}</div>
      <div class="mc-val">{val}</div>
      <div class="mc-unit">{unit}</div>
      <span class="pill {status_cls}">{status_txt}</span>
    </div>"""

def data_row(k, v):
    return f'<div class="dr"><span class="dr-k">{k}</span><span class="dr-v">{v}</span></div>'

def stat_bar(name, val, mx, color):
    pct = min(100, int(val / mx * 100)) if mx else 0
    return f"""<div class="sb-wrap"><div class="sb-head">
      <span class="sb-name">{name}</span><span class="sb-val">{val}</span></div>
      <div class="sb-bg"><div class="sb-fill" style="width:{pct}%;background:{color}"></div></div>
    </div>"""

def donut(val, mx, color, label, unit):
    r = 38; cx = cy = 48; circ = 2 * 3.14159 * r; fill = circ * min(val / mx, 1) if mx else 0
    return f"""<div class="dw">
      <svg viewBox="0 0 96 96" width="96">
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e8eef8" stroke-width="12"/>
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="12"
          stroke-dasharray="{fill:.1f} {circ:.1f}"
          stroke-dashoffset="{circ*0.25:.1f}" stroke-linecap="round"/>
        <text x="48" y="44" text-anchor="middle" font-size="14" fill="#0d1e4a"
              font-family="Rajdhani,sans-serif" font-weight="700">{val}</text>
        <text x="48" y="56" text-anchor="middle" font-size="7" fill="#5a6f99">{unit}</text>
      </svg>
      <div class="dl">{label}</div></div>"""

def _load_records():
    """Always-fresh record loader that respects save_ts to bust cache."""
    return get_health_records(st.session_state.username)

def get_selected_record(recs):
    """Return the currently selected report, or default to the latest saved record."""
    if not recs:
        return None
    selected_id = st.session_state.get("report_selector")
    current = st.session_state.get("current_report_data")
    if current and current.get("id") == selected_id:
        return current
    if selected_id is not None:
        for rec in recs:
            if rec.get("id") == selected_id:
                return rec
    return recs[-1]


def get_officers_with_latest_records():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.badge, u.name, u.rank, u.dept, u.state, u.conditions,
                   u.medications, u.email, u.phone, u.last_checkup,
                   hr.record_date AS latest_record_date,
                   hr.bp_systolic, hr.bp_diastolic, hr.sugar,
                   hr.cholesterol, hr.haemoglobin, hr.spo2,
                   hr.bmi, hr.hba1c, hr.source
            FROM users u
            LEFT JOIN (
              SELECT badge, MAX(id) AS max_id
              FROM health_records
              GROUP BY badge
            ) latest ON latest.badge = u.badge
            LEFT JOIN health_records hr ON hr.badge = latest.badge AND hr.id = latest.max_id
            WHERE u.role = 'officer'
            ORDER BY u.dept, u.name
        """).fetchall()
        return [dict(r) for r in rows]

def delete_health_record(record_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM health_records WHERE id=?", (record_id,))
    get_health_records_cached.clear()

def generate_analysis(extracted):
    analysis = {"status": "Normal", "concerns": [], "suggestions": []}
    bp_sys = extracted.get("BP Systolic (mmHg)")
    bp_dia = extracted.get("BP Diastolic (mmHg)")
    sugar = extracted.get("Fasting Blood Sugar (mg/dL)") or extracted.get("Random Blood Sugar (mg/dL)") or extracted.get("Blood Glucose (mg/dL)")
    chol = extracted.get("Total Cholesterol (mg/dL)") or extracted.get("Cholesterol (mg/dL)")
    hb = extracted.get("Haemoglobin (g/dL)")
    spo2 = extracted.get("SpO2 (%)")
    if bp_sys and bp_dia and (int(bp_sys) >= 140 or int(bp_dia) >= 90):
        analysis["status"] = "High Blood Pressure"
        analysis["concerns"].append("High BP")
        analysis["suggestions"].append("Reduce salt intake, exercise daily, monitor BP regularly")
    if sugar and int(sugar) >= 126:
        if analysis["status"] == "Normal":
            analysis["status"] = "High Sugar"
        else:
            analysis["status"] += ", High Sugar"
        analysis["concerns"].append("High Sugar")
        analysis["suggestions"].append("Follow low-carb diet, walk daily, check sugar levels")
    if chol and int(chol) >= 240:
        if analysis["status"] == "Normal":
            analysis["status"] = "High Cholesterol"
        else:
            analysis["status"] += ", High Cholesterol"
        analysis["concerns"].append("High Cholesterol")
        analysis["suggestions"].append("Eat healthy fats, avoid fried food, get regular checkups")
    if hb and float(hb) < 12:
        analysis["concerns"].append("Low Haemoglobin")
        analysis["suggestions"].append("Eat iron-rich foods, take vitamin C, consult doctor")
    if spo2 and int(spo2) < 95:
        analysis["concerns"].append("Low Oxygen")
        analysis["suggestions"].append("Rest well, avoid smoke, see doctor immediately")
    return analysis

# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: LANDING (public, pre-login)                              ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_landing():
    st.markdown("""
    <div class="hero-banner">
      <div class="hero-deco">🛡️</div>
      <div style="max-width:700px;position:relative;z-index:1;color:var(--navy) !important;">
        <div class="hero-badge" style="color:var(--gold2) !important;">
          🛡️ &nbsp; Mumbai Police Wellness Division · Est. 2024
        </div>
        <div style="font-family:'Rajdhani',sans-serif;font-size:3.8rem;font-weight:700;
                    line-height:1.05;margin-bottom:.6rem;color:var(--navy) !important;">
          Smart Health for<br><span style="color:var(--gold3) !important;">Brave Officers</span>
        </div>
        <div style="color:var(--text2) !important;font-size:1.02rem;max-width:600px;line-height:1.8;margin-bottom:1.8rem;">
          SHIELD is Mumbai Police's dedicated health intelligence platform.
          Track vitals, upload lab reports, receive AI-powered analysis and stay
          connected to 21 empanelled hospitals — all in one secure dashboard.
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <div class="hero-stat-val" style="color:#f0a020 !important;">21</div>
            <div class="hero-stat-lbl" style="color:#7a96c4 !important;">Empanelled Hospitals</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-val" style="color:#f0a020 !important;">₹300</div>
            <div class="hero-stat-lbl" style="color:#7a96c4 !important;">6-Test Package</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-val" style="color:#f0a020 !important;">AI</div>
            <div class="hero-stat-lbl" style="color:#7a96c4 !important;">PDF + Image OCR</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-val" style="color:#f0a020 !important;">100%</div>
            <div class="hero-stat-lbl" style="color:#7a96c4 !important;">Confidential</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("🔐  Officer Login", use_container_width=True):
            st.session_state.admin_mode = False
            st.session_state.admin_signup_mode = False
            st.session_state.admin_otp_sent = False
            st.session_state.admin_otp = None
            st.session_state.page = "Auth"; st.rerun()
    with c2:
        if st.button("🔑  Admin Login", use_container_width=True):
            st.session_state.admin_mode = True
            st.session_state.admin_signup_mode = False
            st.session_state.admin_otp_sent = False
            st.session_state.admin_otp = None
            st.session_state.page = "Auth"; st.rerun()
    with c3:
        if st.button("📋  Register Now", use_container_width=True):
            st.session_state.admin_mode = False
            st.session_state.admin_signup_mode = False
            st.session_state.admin_otp_sent = False
            st.session_state.admin_otp = None
            st.session_state.page = "Auth"; st.rerun()

    st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="stat-alert">
      <div class="stat-alert-icon">⚠️</div>
      <div class="stat-alert-text" style="color:#895008 !important;">
        Studies show <strong>68% of police officers</strong> have undetected high blood pressure, and are
        <strong>2–3× more likely</strong> to develop cardiovascular disease than the general population.
        Regular monitoring with SHIELD can catch issues before they become emergencies.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="stats-strip">
      <div class="stats-strip-item">
        <div class="stats-strip-val" style="color:#f0a020 !important;">68%</div>
        <div class="stats-strip-lbl" style="color:#7a96c4 !important;">Officers with undetected BP</div>
      </div>
      <div class="stats-strip-item">
        <div class="stats-strip-val" style="color:#f0a020 !important;">2–3×</div>
        <div class="stats-strip-lbl" style="color:#7a96c4 !important;">Higher cardiovascular risk</div>
      </div>
      <div class="stats-strip-item">
        <div class="stats-strip-val" style="color:#f0a020 !important;">₹80</div>
        <div class="stats-strip-lbl" style="color:#7a96c4 !important;">Diabetes prevention test</div>
      </div>
      <div class="stats-strip-item">
        <div class="stats-strip-val" style="color:#f0a020 !important;">20 min</div>
        <div class="stats-strip-lbl" style="color:#7a96c4 !important;">For a full checkup</div>
      </div>
      <div class="stats-strip-item">
        <div class="stats-strip-val" style="color:#f0a020 !important;">21</div>
        <div class="stats-strip-lbl" style="color:#7a96c4 !important;">Mumbai hospitals linked</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-label">🚀 &nbsp; Platform Features</div>', unsafe_allow_html=True)
    feats = [
        ("#d9880c","🤖","AI Report Analysis","Upload any lab report (JPG, PNG, PDF). OCR + AI extracts every parameter automatically — no manual typing."),
        ("#0f9a8a","📊","Health Dashboard","Monitor BP, Sugar, Cholesterol, Haemoglobin, SpO2 and Fitness Score with colour-coded visual alerts."),
        ("#1a4fd6","🏥","Hospital Network","Pre-linked directory of 21 empanelled Mumbai hospitals — Government and Private — with contact numbers."),
        ("#7c3aed","📅","Smart Reminders","Configurable checkup reminders every 3 or 6 months with a live countdown calendar."),
        ("#d9880c","💡","Personalised Advice","Evidence-based diet and lifestyle tips tailored to your specific vital readings and risk profile."),
        ("#0f9a8a","🧠","Stress Assessment","Occupational stress calculator designed for police duty patterns — sleep, workload, exercise."),
        ("#1a4fd6","📋","Health History","Complete longitudinal log of all records, securely stored with full detail view and export."),
        ("#7c3aed","📄","Health Reports","Sidebar report panel — instant snapshot of your latest vitals visible from every page."),
    ]
    for i in range(0, len(feats), 4):
        cols = st.columns(4)
        for col, (color, ico, title, text) in zip(cols, feats[i:i+4]):
            with col:
                st.markdown(f"""<div class="feat-card" style="--feat-color:{color}">
                  <div class="feat-card-icon">{ico}</div>
                  <div class="feat-card-title" style="color:#0d1e4a !important;">{title}</div>
                  <div class="feat-card-text" style="color:#2d3f6b !important;">{text}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sec-label">📌 &nbsp; How SHIELD Works</div>', unsafe_allow_html=True)
    steps = [
        ("#d9880c","01","📝","Register & Login","Create your profile with Badge No., rank, department and health baseline. Takes under 2 minutes."),
        ("#0f9a8a","02","🔬","Get a Checkup","Visit any empanelled hospital or govt. lab. 6 core tests, under ₹300, 20 minutes. No appointment needed."),
        ("#1a4fd6","03","📤","Upload Your Report","Scan or photograph your lab report and upload to SHIELD. AI OCR reads the entire document instantly."),
        ("#7c3aed","04","📊","Review & Act","See complete analysis, risk scores, trends and personalised recommendations — all in your dashboard."),
    ]
    cols = st.columns(4)
    for col, (color, num, ico, title, text) in zip(cols, steps):
        with col:
            st.markdown(f"""<div class="step-card" style="--step-color:{color}">
              <div class="step-num" style="color:rgba(13,30,74,.08) !important;">{num}</div>
              <div class="step-icon">{ico}</div>
              <div class="step-title" style="color:#0d1e4a !important;">{title}</div>
              <div class="step-text" style="color:#2d3f6b !important;">{text}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sec-label">💬 &nbsp; Officer Voices</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="quote-card">
          <div class="quote-mark" style="color:rgba(184,114,10,.25) !important;">"</div>
          <div class="quote-text" style="color:#2d3f6b !important;">SHIELD detected my high BP before I even felt symptoms. Got treated in time. I owe this system a great deal.</div>
          <div class="quote-author" style="color:#d9880c !important;">Inspector R. Patil</div>
          <div class="quote-rank" style="color:#5a6f99 !important;">Bandra Division, Mumbai</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="quote-card">
          <div class="quote-mark" style="color:rgba(184,114,10,.25) !important;">"</div>
          <div class="quote-text" style="color:#2d3f6b !important;">The AI report upload is incredible. I photographed my lab report and all my vitals were sorted within seconds.</div>
          <div class="quote-author" style="color:#d9880c !important;">Sub-Inspector S. Mehta</div>
          <div class="quote-rank" style="color:#5a6f99 !important;">Andheri West Station</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="quote-card">
          <div class="quote-mark" style="color:rgba(184,114,10,.25) !important;">"</div>
          <div class="quote-text" style="color:#2d3f6b !important;">The hospital directory alone saved me 30 minutes during an emergency. Every officer in Mumbai needs this platform.</div>
          <div class="quote-author" style="color:#d9880c !important;">DSP A. Kulkarni</div>
          <div class="quote-rank" style="color:#5a6f99 !important;">Mumbai North Region</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="af">
      <b>SHIELD</b> v6.0 — Smart Health Intelligence &amp; Emergency Life-care Dashboard &nbsp;|&nbsp;
      Police Wellness Division &nbsp;|&nbsp; Confidential &amp; Secure &nbsp;|&nbsp;
      &copy; 2026 Police Welfare Division &nbsp;|&nbsp; Emergency: <b>112</b>
    </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  AUTH PAGE                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_auth():
    if st.button("← Back to Home"):
        st.session_state.page = "Landing"; st.rerun()

    st.markdown("""
    <div style="text-align:center;padding:1.5rem 0 1rem">
      <div style="font-size:3.5rem">🛡️</div>
      <div style="font-family:'Rajdhani',sans-serif;font-size:2.4rem;font-weight:700;
                  color:#0d1e4a !important;letter-spacing:-1px;margin:.5rem 0 .2rem">SHIELD</div>
      <div style="font-size:.84rem;color:#5a6f99 !important;font-weight:500;letter-spacing:.5px">
        Police Health Intelligence Portal · Secure Access
      </div>
      <div style="width:60px;height:3px;background:linear-gradient(90deg,#d9880c,#0f9a8a);
                  margin:.9rem auto;border-radius:2px"></div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.7, 1])
    with col:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.session_state.get("forgot_pw_mode"):
            st.markdown("""<div style="text-align:center;margin-bottom:1.2rem">
              <div style="font-family:'Rajdhani',sans-serif;font-size:1.2rem;font-weight:700;color:#0d1e4a !important;">🔑 Reset Password</div>
              <div style="font-size:.84rem;color:#5a6f99 !important;margin-top:.3rem">Enter your Badge No. and registered email</div>
            </div>""", unsafe_allow_html=True)
            fp_badge = st.text_input("Badge No.", placeholder="e.g. MH-IPS-1042", key="fp_badge")
            fp_email = st.text_input("Registered Email", placeholder="your@email.com", key="fp_email")
            fp_pw1   = st.text_input("New Password", type="password", key="fp_pw1")
            fp_pw2   = st.text_input("Confirm New Password", type="password", key="fp_pw2")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Reset Password", use_container_width=True):
                    u = get_user(fp_badge)
                    if not u: st.error("Badge not found.")
                    elif u.get("email", "").strip().lower() != fp_email.strip().lower(): st.error("Email mismatch.")
                    elif not fp_pw1 or len(fp_pw1) < 6: st.warning("Min 6 characters.")
                    elif fp_pw1 != fp_pw2: st.error("Passwords don't match.")
                    else:
                        update_user_field(fp_badge, password_hash=hash_pw(fp_pw1))
                        st.success("Password reset! Please login.")
                        st.session_state.forgot_pw_mode = False; st.rerun()
            with c2:
                if st.button("← Back to Login", use_container_width=True):
                    st.session_state.forgot_pw_mode = False; st.rerun()
        elif st.session_state.get("admin_mode"):
            # Check if any admins exist
            with get_conn() as conn:
                admin_count = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
            
            if admin_count == 0:
                st.info("No admin accounts found. Please create the first admin account.")
                st.session_state.admin_signup_mode = True
            else:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔐 Login", use_container_width=True):
                        st.session_state.admin_signup_mode = False
                with col2:
                    if st.button("📝 Sign Up", use_container_width=True):
                        st.session_state.admin_signup_mode = True
            
            if st.session_state.get("admin_signup_mode"):
                st.markdown("### 📝 Admin Signup")
                email = st.text_input("Email (will be used as login ID)", placeholder="admin@example.com", key="su_email")
                pw = st.text_input("Password", type="password", key="su_pw")
                pw_confirm = st.text_input("Confirm Password", type="password", key="su_pw_confirm")
                if st.button("CREATE ADMIN →", use_container_width=True, key="btn_su_admin"):
                    if not email or not pw:
                        st.error("Please fill all fields.")
                    elif pw != pw_confirm:
                        st.error("Passwords do not match.")
                    elif len(pw) < 6:
                        st.warning("Password must be at least 6 characters.")
                    else:
                        existing = get_admin(email)
                        if existing:
                            st.error("This email is already registered as admin.")
                        else:
                            save_admin(email, hash_pw(pw))
                            st.success("Admin account created successfully! You can now login.")
                            st.session_state.admin_signup_mode = False
                            st.rerun()
            else:
                st.markdown("### 🔐 Admin Login")
                email = st.text_input("Email/Login ID", placeholder="admin@example.com", key="li_b")
                pw    = st.text_input("Password", type="password", key="li_p")
                if st.button("LOGIN →", use_container_width=True, key="btn_li"):
                    admin = get_admin(email)
                    if admin and admin.get("password_hash") == hash_pw(pw):
                        st.session_state.logged_in = True
                        st.session_state.username = email
                        st.session_state.role = "admin"
                        st.session_state.page = "Admin Dashboard"
                        st.rerun()
                    else:
                        st.error("Invalid admin credentials.")
        else:
            tab_li, tab_su = st.tabs(["🔐  Login", "📋  Register New Officer"])

            with tab_li:
                st.markdown("### 🔐 Officer Login")
                badge = st.text_input("Badge No.", placeholder="e.g. MH-IPS-1042", key="li_b")
                pw    = st.text_input("Password", type="password", key="li_p")
                if st.button("LOGIN →", use_container_width=True, key="btn_li"):
                    u = get_user(badge)
                    if u and u.get("password_hash") == hash_pw(pw):
                        st.session_state.logged_in = True
                        st.session_state.username  = badge
                        st.session_state.role      = u.get("role", "officer")
                        st.session_state.page      = "Welcome"
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                if st.button("Forgot?", use_container_width=True, key="btn_forgot"):
                    st.session_state.forgot_pw_mode = True; st.rerun()

            with tab_su:
                with st.expander("📘 Personal Details", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        su_badge = st.text_input("Badge Number *", key="su_bad")
                        su_name  = st.text_input("Full Name *", key="su_nm")
                        su_dob   = st.date_input("Date of Birth", datetime.date(1985, 1, 1), min_value=datetime.date(1960, 1, 1), key="su_dob")
                        su_gen   = st.selectbox("Gender", ["Male", "Female", "Other"], key="su_gen")
                    with c2:
                        su_rank  = st.selectbox("Rank *", ["Constable","Head Constable","ASI","Sub-Inspector","Inspector","DSP","SP","SSP","DIG","IG","ADG","DGP"], key="su_rk")
                        su_dept  = st.text_input("Station / District *", key="su_dp")
                        su_state = st.selectbox("State", ["Maharashtra","Delhi","Uttar Pradesh","Tamil Nadu","Karnataka","Gujarat","Rajasthan","West Bengal","Telangana","Other"], key="su_st")
                        su_phone = st.text_input("Mobile Number", key="su_ph")
                with st.expander("🏥 Medical Baseline"):
                    c3, c4 = st.columns(2)
                    with c3:
                        su_blood   = st.selectbox("Blood Group", ["A+","A-","B+","B-","AB+","AB-","O+","O-"], key="su_bg")
                        su_allergy = st.text_input("Known Allergies", key="su_al")
                    with c4:
                        su_cond = st.text_area("Pre-existing Conditions", height=68, key="su_co")
                        su_meds = st.text_area("Current Medications", height=68, key="su_me")
                with st.expander("🔐 Account Security"):
                    c5, c6 = st.columns(2)
                    with c5:
                        su_em  = st.text_input("Email Address *", key="su_em")
                        su_pw  = st.text_input("Create Password *", type="password", key="su_pw")
                    with c6:
                        su_ecc = st.text_input("Emergency Contact Name", key="su_ec")
                        su_cf  = st.text_input("Confirm Password *", type="password", key="su_cf")
                    su_ecph = st.text_input("Emergency Contact Phone", key="su_ep")

                if st.button("REGISTER OFFICER →", use_container_width=True, key="btn_su"):
                    if not su_badge or not su_name or not su_pw:
                        st.warning("Badge number, name and password are required.")
                    elif su_pw != su_cf:
                        st.error("Passwords do not match.")
                    elif len(su_pw) < 6:
                        st.warning("Password must be at least 6 characters.")
                    elif get_user(su_badge):
                        st.error("Badge number already registered.")
                    else:
                        age = int((datetime.date.today() - su_dob).days / 365.25)
                        save_user({
                            "badge": su_badge, "password_hash": hash_pw(su_pw),
                            "name": su_name, "rank": su_rank, "dept": su_dept,
                            "state": su_state, "gender": su_gen, "dob": str(su_dob),
                            "age": age, "phone": su_phone, "blood_group": su_blood,
                            "allergies": su_allergy, "conditions": su_cond,
                            "medications": su_meds, "email": su_em,
                            "emergency_contact": su_ecc, "emergency_phone": su_ecph,
                            "role": "officer", "uid": str(uuid.uuid4()),
                            "registered": str(datetime.date.today()),
                            "reminder_months": 6,
                            "last_checkup": str(datetime.date.today()),
                        })
                        st.success(f"Officer {su_name} registered! Please login.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""<div class="af"><b>SHIELD</b> v6.0 — Police Health Intelligence
      | Confidential &amp; Secure | &copy; 2026 Police Welfare Division
      | Emergency: <b>112</b></div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  SIDEBAR (logged-in) — with REPORT PANEL                       ║
# ╚══════════════════════════════════════════════════════════════════╝
NAV = [
    ("MAIN",     [("🏠","Welcome"), ("ℹ️","Importance")]),
    ("HEALTH",   [("💉","Upload Health Data"), ("🤖","AI Upload Report"),
                  ("🔮","Prediction & Results"), ("💡","Suggestions")]),
    ("ANALYSIS", [("📈","Health Charts"), ("🏅","Fitness Score"), ("🧠","Stress Calculator")]),
    ("RECORDS",  [("📋","Health History"), ("⏰","Reminders"), ("📤","Export Data")]),
    ("NETWORK",  [("🏥","Hospital Network")]),
]

def render_sidebar():
    user = get_user(st.session_state.username) or {}
    recs = _load_records()

    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;padding:1.1rem 0 .7rem">
          <div style="font-size:2.6rem">🛡️</div>
          <div style="font-family:'Rajdhani',sans-serif;font-size:1.2rem;font-weight:700;
                      letter-spacing:5px;margin-top:.3rem;
                      background:linear-gradient(135deg,#f0a020,#0f9a8a);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      background-clip:text;">SHIELD</div>
          <div style="font-size:.63rem;color:#7a96c4 !important;letter-spacing:1px;font-weight:500">v6.0 · Secure Portal</div>
          <div style="width:50px;height:2px;background:linear-gradient(90deg,#f0a020,#0f9a8a);margin:.6rem auto;border-radius:2px"></div>
        </div>""", unsafe_allow_html=True)

        # ── Profile box ────────────────────────────────────────────
        st.markdown(f"""<div class="pb">
          <div class="pb-rank" style="color:var(--gold2) !important;">🏅 {user.get('rank','Officer')}</div>
          <div class="pb-name" style="color:var(--navy) !important;">{user.get('name','Officer')}</div>
          <div class="pb-dept" style="color:var(--text2) !important;">📍 {user.get('dept','Police Department')}</div>
        </div>""", unsafe_allow_html=True)

        # ── REPORT SELECTION PANEL (NEW) ─────────────────────────────
        if recs:
            record_ids = [r["id"] for r in recs]
            if st.session_state.get("force_select_id") and st.session_state.force_select_id in record_ids:
                selected_id = st.session_state.force_select_id
                del st.session_state.force_select_id
                default_idx = record_ids.index(selected_id)
            else:
                if "report_selector" not in st.session_state or st.session_state.report_selector not in record_ids:
                    st.session_state.report_selector = record_ids[-1]
                default_idx = record_ids.index(st.session_state.report_selector) if st.session_state.report_selector in record_ids else len(record_ids) - 1
            report_labels = {r["id"]: f"{r['record_date']} · {r.get('source','Manual')}" for r in recs}
            st.selectbox(
                "Select Report",
                record_ids,
                format_func=lambda rid: report_labels.get(rid, str(rid)),
                index=default_idx,
                key="report_selector",
                help="Choose which saved report should be used across all dashboard tabs."
            )

            selected = get_selected_record(recs)
            if selected:
                st.markdown(f"**Selected Report:** {selected['record_date']} - {selected['source']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📊 View Charts for This Report"):
                        st.session_state.page = "Health Charts"
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete This Report", key=f"delete_{selected['id']}"):
                        delete_health_record(selected['id'])
                        st.success("Report deleted successfully.")
                        # Clear related session state
                        if st.session_state.get("report_selector") == selected['id']:
                            if "report_selector" in st.session_state:
                                del st.session_state.report_selector
                        if st.session_state.get("current_report_data") and st.session_state.current_report_data.get('id') == selected['id']:
                            del st.session_state.current_report_data
                        st.rerun()

            selected = get_selected_record(recs) or recs[-1]
            bs  = int(selected.get("bp_systolic") or 0)
            bd  = int(selected.get("bp_diastolic") or 0)
            sg  = int(selected.get("sugar") or 0)
            ch  = int(selected.get("cholesterol") or 0)
            hb  = selected.get("haemoglobin") or 0
            spo = int(selected.get("spo2") or 0)
            fit = fitness_score(bs, bd, sg, ch, hb, spo, user.get("age",30), user.get("gender","Male"))
            bp_s, bp_c   = classify_bp(bs, bd)
            sg_s, sg_c   = classify_sugar(sg)
            spo_s, spo_c = classify_spo2(spo)
            fit_s = "Excellent" if fit >= 80 else "Good" if fit >= 65 else "Average" if fit >= 50 else "Poor"
            fit_c = "p-ok" if fit >= 65 else "p-warn" if fit >= 50 else "p-danger"

            def _sp(cls): return {"p-ok":"🟢","p-warn":"🟡","p-danger":"🔴"}.get(cls,"⚪")

            st.markdown(f"""
            <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
                        border-radius:12px;padding:.8rem .9rem;margin-bottom:.6rem">
              <div style="font-family:'Rajdhani',sans-serif;font-size:.6rem;font-weight:700;
                          letter-spacing:2px;text-transform:uppercase;color:#d9880c !important;
                          border-bottom:1px solid rgba(255,255,255,.08);padding-bottom:.4rem;margin-bottom:.5rem">
                📄 Selected Report · {selected.get('record_date','—')}
              </div>
              <div class="sb-report-row"><span class="sb-report-k">Source</span>
                <span class="sb-report-v">{selected.get('source','Manual')}</span></div>
              <div class="sb-report-row"><span class="sb-report-k">BP</span>
                <span class="sb-report-v">{_sp(bp_c)} {bs}/{bd}</span></div>
              <div class="sb-report-row"><span class="sb-report-k">Sugar</span>
                <span class="sb-report-v">{_sp(sg_c)} {sg} mg/dL</span></div>
              <div class="sb-report-row"><span class="sb-report-k">SpO2</span>
                <span class="sb-report-v">{_sp(spo_c)} {spo}%</span></div>
              <div class="sb-report-row" style="border:none"><span class="sb-report-k">Fitness</span>
                <span class="sb-report-v">{_sp(fit_c)} {fit}/100 — {fit_s}</span></div>
            </div>
            <div style="font-size:.64rem;color:#5a7099 !important;text-align:center;margin-bottom:.4rem">
              {len(recs)} record{'s' if len(recs)!=1 else ''} on file
            </div>
            """, unsafe_allow_html=True)

            if st.checkbox("Show selected report preview", value=False, key="show_selected_report_preview"):
                st.markdown("<div style='margin-bottom:.5rem;font-size:.82rem;color:var(--text2) !important;'>Preview of the currently selected report:</div>", unsafe_allow_html=True)
                preview_html = ""
                for field in ["record_date","source","lab_name","doctor_name","diagnosis","medicines","bp_systolic","bp_diastolic","sugar","cholesterol","haemoglobin","spo2","weight","height","bmi","tsh","hba1c"]:
                    if selected.get(field) is not None and selected.get(field) != "":
                        label = field.replace("_"," ").title()
                        preview_html += data_row(label, str(selected.get(field)))
                st.markdown(f'<div class="report-panel">{preview_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
              border-radius:12px;padding:.8rem .9rem;margin-bottom:.6rem;text-align:center">
              <div style="font-size:.76rem;color:#5a7099 !important;">No health records yet.<br>Upload data to see your report here.</div>
            </div>""", unsafe_allow_html=True)

        # ── Navigation ─────────────────────────────────────────────
        for section, items in NAV:
            st.markdown(f"<div class='nl' style='color:rgba(184,114,10,.6) !important;'>{section}</div>", unsafe_allow_html=True)
            for icon, name in items:
                if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True):
                    st.session_state.page = name; st.rerun()

        if user.get("role") == "admin":
            st.markdown("<div class='nl' style='color:rgba(184,114,10,.6) !important;'>ADMIN</div>", unsafe_allow_html=True)
            if st.button("🔒  Admin Dashboard", key="nav_Admin Dashboard", use_container_width=True):
                st.session_state.page = "Admin Dashboard"; st.rerun()

        st.markdown("<hr/>", unsafe_allow_html=True)
        if not st.session_state.get("logged_in"):
            if st.button("🔐  Admin Signup", key="nav_Admin Signup", use_container_width=True):
                st.session_state.page = "Admin Signup"; st.rerun()
        st.markdown("""<div style="text-align:center;padding:.35rem 0;font-size:.74rem;color:#7a96c4 !important;font-weight:500">
          🚨 Police Emergency: <b style="color:#f0a020 !important;">112</b>
        </div>""", unsafe_allow_html=True)
        if st.button("🚪  Logout", use_container_width=True, key="nav_logout"):
            logout(); st.rerun()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: WELCOME                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_welcome():
    user  = get_user(st.session_state.username) or {}
    recs  = _load_records()
    selected = get_selected_record(recs)
    today = datetime.date.today()
    hour  = datetime.datetime.now().hour
    greet = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 18 else "Good Evening"

    st.markdown(f"""<div class="welcome-card">
      <div class="wc-greet" style="color:var(--gold3) !important;">{greet}, Officer</div>
      <div class="wc-name" style="color:var(--navy) !important;">{user.get('rank','')} {user.get('name','')}</div>
      <div class="wc-sub" style="color:var(--text2) !important;">
        🛡️ {user.get('dept','—')} &nbsp;·&nbsp;
        🩸 {user.get('blood_group','—')} &nbsp;·&nbsp;
        📍 {user.get('state','—')} &nbsp;·&nbsp;
        📅 {today.strftime('%d %b %Y')}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Save notification ─────────────────────────────────────────
    if st.session_state.get("record_just_saved"):
        st.session_state.record_just_saved = False
        st.markdown("""<div class="save-success">
          <div class="save-success-icon">✅</div>
          <div class="save-success-text">
            Health record saved successfully! All tabs — Charts, History, Fitness Score,
            Prediction &amp; Suggestions — now reflect your latest data.
          </div>
        </div>""", unsafe_allow_html=True)

    if not recs:
        st.markdown("""<div class="card" style="text-align:center;padding:2.5rem">
          <div style="font-size:2.5rem;margin-bottom:.8rem">📊</div>
          <div style="font-family:'Rajdhani',sans-serif;color:#d9880c !important;font-size:1.1rem;font-weight:700">No Records Yet</div>
          <div style="color:#5a6f99 !important;font-size:.88rem;margin-top:.4rem">
            Go to <b>Upload Health Data</b> or <b>AI Upload Report</b> to begin.</div>
        </div>""", unsafe_allow_html=True)
        return

    l    = selected or recs[-1]
    bs   = l.get("bp_systolic") or 120; bd = l.get("bp_diastolic") or 80
    sg   = l.get("sugar") or 90;       ch = l.get("cholesterol") or 190
    hb   = l.get("haemoglobin") or 14.0; spo2 = l.get("spo2") or 98
    age  = user.get("age", 30); gender = user.get("gender", "Male")
    fit  = fitness_score(bs, bd, sg, ch, hb, spo2, age, gender)

    bp_s, bp_c   = classify_bp(bs, bd)
    sg_s, sg_c   = classify_sugar(sg)
    ch_s, ch_c   = classify_chol(ch)
    spo_s, spo_c = classify_spo2(spo2)
    hb_s, hb_c   = classify_hb(hb, gender)
    fit_s = "Excellent" if fit >= 80 else "Good" if fit >= 65 else "Average" if fit >= 50 else "Needs Attention"
    fit_c = "p-ok" if fit >= 65 else "p-warn" if fit >= 50 else "p-danger"

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(metric_card("Blood Pressure", f"{int(bs)}/{int(bd)}", "mmHg", bp_s, bp_c, "#d9880c"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Blood Sugar", str(int(sg)), "mg/dL", sg_s, sg_c, "#f59e0b"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Cholesterol", str(int(ch)), "mg/dL", ch_s, ch_c, "#0d9488"), unsafe_allow_html=True)
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4: st.markdown(metric_card("Haemoglobin", str(hb), "g/dL", hb_s, hb_c, "#3b82f6"), unsafe_allow_html=True)
    with c5: st.markdown(metric_card("SpO2", str(int(spo2)), "%", spo_s, spo_c, "#10b981"), unsafe_allow_html=True)
    with c6: st.markdown(metric_card("Fitness Score", str(fit), "/100", fit_s, fit_c, "#7c3aed"), unsafe_allow_html=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    months   = user.get("reminder_months", 6) or 6
    last_d_str = user.get("last_checkup") or str(today)
    try: last_d = datetime.date.fromisoformat(str(last_d_str)[:10])
    except: last_d = today
    next_d = last_d + datetime.timedelta(days=months * 30)
    days   = (next_d - today).days

    ca, cb = st.columns(2)
    with ca:
        card_open("Last Record")
        st.markdown(
            data_row("Date", l.get('record_date', '—')) +
            data_row("Weight", f"{l.get('weight','—')} kg") +
            data_row("BMI", str(l.get('bmi','—'))) +
            data_row("Total Records", str(len(recs))),
            unsafe_allow_html=True
        )
        card_close()
    with cb:
        over = days < 0
        col_ = "#dc2626" if over else "#d97706" if days <= 30 else "#059669"
        card_open("Next Checkup")
        st.markdown(
            f'<div style="font-family:Rajdhani,sans-serif;font-size:1.5rem;color:{col_};margin:.35rem 0;font-weight:700">{next_d}</div>' +
            data_row("Status", '⚠️ Overdue '+str(abs(days))+'d' if over else str(days)+' days remaining') +
            data_row("Interval", f"Every {months} months") +
            data_row("Blood Group", user.get('blood_group', '—')),
            unsafe_allow_html=True
        )
        card_close()

    # ── Trend mini-view if enough records ─────────────────────────
    if len(recs) >= 2:
        st.markdown('<div class="sec-label">📈 &nbsp; Recent Trend</div>', unsafe_allow_html=True)
        r5 = recs[-5:]
        c1, c2 = st.columns(2)
        with c1:
            card_open("Systolic BP — Last 5")
            for r in r5:
                v = int(r.get("bp_systolic") or 0)
                st.markdown(stat_bar(r["record_date"], v, 220, "#d9880c"), unsafe_allow_html=True)
            card_close()
        with c2:
            card_open("Blood Sugar — Last 5")
            for r in r5:
                v = int(r.get("sugar") or 0)
                st.markdown(stat_bar(r["record_date"], v, 400, "#f59e0b"), unsafe_allow_html=True)
            card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: IMPORTANCE                                               ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_importance():
    page_header("ℹ️", "Why SHIELD Matters", "The case for proactive police health monitoring")
    st.markdown("""<div class="card" style="margin-bottom:1.5rem">
      <div style="font-size:.96rem;color:#2d3f6b !important;line-height:1.9;max-width:860px">
        Police officers face <b style="color:#0d1e4a !important;">2–3× higher risk</b> of cardiovascular disease,
        diabetes, and mental health disorders compared to the general population.
        <b style="color:#d9880c !important;">SHIELD</b> tracks the 6 most impactful parameters —
        BP, Sugar, Cholesterol, Haemoglobin, SpO2, and BMI — requiring just
        <b style="color:#0b6e62 !important;">₹300 and 20 minutes</b> every 6 months.
      </div>
    </div>""", unsafe_allow_html=True)
    cards = [
        ("🫀","Silent BP Crisis","68% of officers have undetected high BP. It causes strokes with zero prior symptoms."),
        ("🩺","Diabetes Prevention","Irregular meals + canteen food = pre-diabetes. A ₹80 test prevents lifetime medication."),
        ("🧠","Mental Health","80% of officers report chronic stress. Regular monitoring flags issues early."),
        ("📊","Data Over Time","Trends over multiple records reveal the real picture and predict future risk."),
        ("⏰","Shift-Friendly","SHIELD works on mobile. Log a reading between patrols in under 60 seconds."),
        ("🏥","Hospital Network","Pre-linked Mumbai hospitals mean officers never search for where to go."),
        ("📤","AI Report Upload","Photograph your lab report. AI extracts every value into a clean table instantly."),
        ("🌐","Zero Paper","Digital records travel with the officer across postings. No lost files."),
    ]
    for i in range(0, len(cards), 4):
        cols = st.columns(4)
        for col, (ico, title, text) in zip(cols, cards[i:i+4]):
            with col:
                st.markdown(f"""<div class="ic">
                  <div class="ic-icon">{ico}</div>
                  <div class="ic-title" style="color:#0d1e4a !important;">{title}</div>
                  <div class="ic-text" style="color:#2d3f6b !important;">{text}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: UPLOAD HEALTH DATA (Manual)                              ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_upload():
    page_header("💉", "Upload Health Data", "Manual entry of your core health parameters")
    with st.form("hf"):
        c1, c2 = st.columns(2)
        with c1:
            card_open("Blood Pressure & Heart")
            bp_sys = st.number_input("Systolic BP (mmHg)", 80, 220, 120)
            bp_dia = st.number_input("Diastolic BP (mmHg)", 50, 140, 80)
            heart  = st.number_input("Heart Rate (bpm)", 40, 200, 72)
            card_close()
            card_open("Blood Parameters")
            sugar = st.number_input("Fasting Blood Sugar (mg/dL)", 50, 400, 90)
            chol  = st.number_input("Total Cholesterol (mg/dL)", 100, 400, 185)
            hb    = st.number_input("Haemoglobin (g/dL)", 5.0, 20.0, 14.0, step=0.1)
            ldl   = st.number_input("LDL (mg/dL) — optional", 0.0, 300.0, 0.0)
            hdl   = st.number_input("HDL (mg/dL) — optional", 0.0, 200.0, 0.0)
            card_close()
        with c2:
            card_open("Oxygen & Body")
            spo2   = st.number_input("SpO2 / Oxygen Level (%)", 70, 100, 98)
            weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0, step=0.5)
            height = st.number_input("Height (cm)", 100.0, 230.0, 170.0, step=0.5)
            bmi    = round(weight / ((height / 100) ** 2), 1)
            st.markdown(f"""<div class="dr" style="margin-top:.4rem">
              <span class="dr-k">Calculated BMI</span><span class="dr-v">{bmi}</span></div>""", unsafe_allow_html=True)
            card_close()
            card_open("Record Details")
            chk_date = st.date_input("Checkup Date", datetime.date.today())
            lab      = st.text_input("Lab / Hospital Name")
            doctor   = st.text_input("Doctor Name — optional")
            notes    = st.text_area("Doctor's Remarks", height=76)
            card_close()
        submitted = st.form_submit_button("💾  SAVE HEALTH RECORD →", use_container_width=True)

    if submitted:
        rec = {
            "record_date": str(chk_date),
            "bp_systolic": bp_sys, "bp_diastolic": bp_dia,
            "heart_rate": heart, "sugar": sugar,
            "cholesterol": chol, "haemoglobin": hb,
            "spo2": spo2, "weight": weight, "height": height, "bmi": bmi,
            "ldl": ldl if ldl > 0 else None,
            "hdl": hdl if hdl > 0 else None,
            "lab_name": lab, "doctor_name": doctor, "notes": notes,
            "source": "Manual",
        }
        saved_id = save_health_record(st.session_state.username, rec)
        st.session_state.force_select_id = saved_id
        update_user_field(st.session_state.username, last_checkup=str(chk_date))
        st.session_state.record_just_saved = True
        st.session_state.save_ts = time.time()
        st.session_state.current_report_data = rec.copy()
        st.session_state.current_report_data["id"] = saved_id
        st.markdown("""<div class="save-success">
          <div class="save-success-icon">✅</div>
          <div class="save-success-text">
            Record saved! All tabs now reflect your updated data.<br>
            <span style="font-size:.85rem;font-weight:400;color:#0a6b3e !important;">
              → Navigate to <b>Welcome · Health Charts · History · Fitness Score · Prediction · Suggestions</b>
            </span>
          </div>
        </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: AI UPLOAD REPORT                                         ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_report():
    page_header("🤖", "AI Upload Report", "OCR + AI extracts every parameter into a structured table")

    card_open("How AI Report Analysis Works")
    st.markdown("""<div style="font-size:.9rem;color:#2d3f6b !important;line-height:1.9">
      <b style="color:#d9880c !important;">Step 1:</b> Upload your lab report (PDF, JPG or PNG) — up to 50 MB.<br>
      <b style="color:#d9880c !important;">Step 2:</b> PDF is converted to images via pdf2image + Poppler, then OCR reads all text.<br>
      <b style="color:#d9880c !important;">Step 3:</b> AI extracts <em>every</em> detectable field into a clean grouped table.<br>
      <b style="color:#d9880c !important;">Step 4:</b> Review results and save directly to your health profile.
      <br><br>
      <span style="color:#5a6f99 !important;font-size:.82rem">
        ℹ️ Tesseract path: <code>C:\\Program Files\\Tesseract-OCR\\tesseract.exe</code> &nbsp;|&nbsp;
        Poppler path: <code>C:\\poppler\\Library\\bin</code>
      </span>
    </div>""", unsafe_allow_html=True)
    card_close()

    up = st.file_uploader("Upload Medical Report (PDF / JPG / PNG) — Max 50 MB",
                          type=["pdf", "jpg", "jpeg", "png"])
    if not up:
        st.markdown("""<div style="background:#eaeff8;border:2px dashed #b8c8e8;
          border-radius:14px;padding:1.6rem;text-align:center;color:#5a6f99 !important;font-size:.9rem">
          🖼️ Drag and drop a medical report, or click to browse.<br>
          <small>Supported: JPG · PNG · PDF &nbsp;·&nbsp; 300 DPI recommended for best results</small>
        </div>""", unsafe_allow_html=True)
        return

    size_mb = len(up.getvalue()) / (1024 * 1024)
    if size_mb > 50:
        st.markdown(f"""<div class="alert-box alert-danger">🚫 File too large: {size_mb:.1f} MB. Max 50 MB.</div>""", unsafe_allow_html=True)
        return

    is_pdf = "pdf" in up.type.lower() or up.name.lower().endswith(".pdf")
    file_type_label = "PDF" if is_pdf else "Image"
    st.markdown(f"""<div class="alert-box alert-ok">✅ File ready: <b>{up.name}</b> ({size_mb:.2f} MB) · {file_type_label}</div>""", unsafe_allow_html=True)

    if not st.button("🤖  EXTRACT & ANALYSE →", use_container_width=True):
        return

    spinner_msg = "🔍 Converting PDF pages and running OCR..." if is_pdf else "🔍 Running OCR on image..."
    with st.spinner(spinner_msg):
        raw_text, ocr_error = extract_text_ocr(up)

    if ocr_error:
        st.markdown(f"""<div class="ocr-error">
          ❌ <b>OCR Failed</b> — here is the actual error:<br>
          <pre>{ocr_error}</pre>
        </div>""", unsafe_allow_html=True)
        st.info("Fix the error above and re-upload.")
        return

    if not raw_text or len(raw_text.strip()) < 20:
        st.markdown("""<div class="alert-box alert-warn">
          ⚠️ OCR succeeded but extracted very little text.
          Ensure the file is a clear scan at 300+ DPI.
        </div>""", unsafe_allow_html=True)
        return

    cleaned = clean_ocr_text(raw_text)

    with st.spinner("🧠 AI extracting all parameters..."):
        extracted = extract_all_fields(cleaned)

    total_found = len(extracted)
    if total_found == 0:
        st.markdown("""<div class="alert-box alert-warn">⚠️ No parameters detected.</div>""", unsafe_allow_html=True)
        st.text_area("OCR Output:", value=cleaned[:2000], height=200)
        return
        
        numeric_count = sum(
        1 for v in extracted.values()
        if v and any(c.isdigit() for c in str(v))
        )
        st.success(f"✅ {total_found} field(s) successfully extracted. {numeric_count} numeric values detected.")

    # Generate and display analysis
    analysis = generate_analysis(extracted)
    st.markdown("### 🩺 Health Analysis")
    st.markdown(f"**Overall Status:** {analysis['status']}")
    if analysis['concerns']:
        st.markdown("**Key Concerns:** " + ", ".join(analysis['concerns']))
    if analysis['suggestions']:
        st.markdown("**Suggestions:** " + "; ".join(analysis['suggestions']))

    # Auto-save immediately after extraction
    db_rec = {"source": "AI Report Upload", "record_date": parse_report_date(extracted.get("Report Date"))}
    for field, val in extracted.items():
        db_col = FIELD_TO_DB.get(field)
        if db_col:
            try:
                if db_col in ("diagnosis","medicines","doctor_name","lab_name"):
                    db_rec[db_col] = str(val)
                else:
                    db_rec[db_col] = float(str(val).replace(",",""))
            except:
                db_rec[db_col] = str(val)

    if "weight" in db_rec and "height" in db_rec and not db_rec.get("bmi"):
        try:
            h = float(db_rec["height"])
            w = float(db_rec["weight"])
            if h > 0:
                db_rec["bmi"] = round(w / ((h / 100) ** 2), 1)
        except:
            pass

    db_rec["notes"] = f"AI-extracted from {up.name}. Patient: {extracted.get('Patient Name','Unknown')}"
    saved_id = save_health_record(st.session_state.username, db_rec)
    if saved_id:
        st.session_state.force_select_id = saved_id
        update_user_field(st.session_state.username, last_checkup=db_rec["record_date"])
        st.session_state.record_just_saved = True
        st.session_state.save_ts = time.time()
        st.session_state.current_report_data = db_rec.copy()
        st.session_state.current_report_data["id"] = saved_id
        st.markdown(f"""<div class="save-success">
          <div class="save-success-icon">✅</div>
          <div class="save-success-text">
            Record saved! <b>{total_found} fields</b> extracted, <b>{len([k for k in db_rec if k not in ("source","record_date","diagnosis","medicines","doctor_name","lab_name","notes")])} numeric values</b> stored.<br>
            <span style="font-size:.85rem;font-weight:400;color:#0a6b3e !important;">
              Live in: <b>Health History · Health Charts · Fitness Score · Prediction · Welcome</b>
            </span>
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.error("Failed to save the record. Please try again.")

    tab_full, tab_grouped, tab_vitals, tab_ocr = st.tabs([
        "📊 Full Extraction Table",
        "📋 Grouped by Category",
        "💊 Visual Vitals",
        "📄 Raw OCR Text",
    ])


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: PREDICTION                                               ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_prediction():
    page_header("🔮", "Prediction & Results", "Composite health risk analysis from your latest saved record")
    user = get_user(st.session_state.username) or {}
    recs = _load_records()
    selected = get_selected_record(recs)
    if not recs:
        st.info("No health data found in database. Please upload a record first."); return
    l  = selected or recs[-1]
    bs, bd = float(l.get("bp_systolic") or 120), float(l.get("bp_diastolic") or 80)
    sg, ch = float(l.get("sugar") or 90), float(l.get("cholesterol") or 190)
    hb     = float(l.get("haemoglobin") or 14.0)
    spo2   = float(l.get("spo2") or 98)
    age    = user.get("age", 30); gender = user.get("gender", "Male")
    fit    = fitness_score(bs, bd, sg, ch, hb, spo2, age, gender)
    risk   = max(0, 100 - fit)
    fc     = "#059669" if fit >= 70 else "#d97706" if fit >= 50 else "#dc2626"
    rc     = "#dc2626" if risk >= 50 else "#d97706" if risk >= 30 else "#059669"

    st.markdown(f"""<div class="card" style="margin-bottom:.8rem">
      <div style="font-size:.82rem;color:#5a6f99 !important;">
        Based on record dated <b style="color:#0d1e4a !important;">{l.get('record_date','—')}</b>
        &nbsp;·&nbsp; Source: <span class="pill p-navy">{l.get('source','Manual')}</span>
        &nbsp;·&nbsp; {len(recs)} total record{'s' if len(recs)!=1 else ''} on file
      </div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(donut(fit, 100, fc, "Fitness Score", "/100"), unsafe_allow_html=True)
    with c2: st.markdown(donut(risk, 100, rc, "Risk Score", "/100"), unsafe_allow_html=True)
    with c3: st.markdown(donut(int(bs), 220, "#d9880c", "Systolic BP", "mmHg"), unsafe_allow_html=True)
    with c4: st.markdown(donut(int(spo2), 100, "#3b82f6", "SpO2", "%"), unsafe_allow_html=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    card_open("Full Parameter Analysis")
    rows = [
        ("Blood Pressure",   f"{int(bs)}/{int(bd)} mmHg", *classify_bp(bs, bd)),
        ("Blood Sugar",      f"{int(sg)} mg/dL",          *classify_sugar(sg)),
        ("Cholesterol",      f"{int(ch)} mg/dL",          *classify_chol(ch)),
        ("Haemoglobin",      f"{hb} g/dL",                *classify_hb(hb, gender)),
        ("SpO2",             f"{int(spo2)}%",             *classify_spo2(spo2)),
        ("Heart Rate",       f"{int(l.get('heart_rate') or 72)} bpm", *classify_hr(l.get('heart_rate') or 72)),
        ("BMI",              f"{l.get('bmi','—')}",       *classify_bmi(l.get('bmi') or 22)),
        ("Fitness Score",    f"{fit}/100",
         "Excellent" if fit >= 80 else "Good" if fit >= 65 else "Average" if fit >= 50 else "Poor",
         "p-ok" if fit >= 65 else "p-warn" if fit >= 50 else "p-danger"),
        ("Overall Risk",     f"{risk}/100",
         "Low" if risk < 30 else "Moderate" if risk < 60 else "High",
         "p-ok" if risk < 30 else "p-warn" if risk < 60 else "p-danger"),
    ]
    for name, val, status, cls in rows:
        st.markdown(f"""<div class="dr"><span class="dr-k">{name}</span>
          <span style="display:flex;align-items:center;gap:.5rem">
            <span class="dr-v">{val}</span>
            <span class="pill {cls}">{status}</span>
          </span></div>""", unsafe_allow_html=True)
    card_close()

    # ── History of fitness trend ───────────────────────────────────
    if len(recs) >= 2:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        card_open("Fitness Score Trend — All Records")
        for r in recs[-8:]:
            r_bs = float(r.get("bp_systolic") or 120)
            r_bd = float(r.get("bp_diastolic") or 80)
            r_sg = float(r.get("sugar") or 90)
            r_ch = float(r.get("cholesterol") or 190)
            r_hb = float(r.get("haemoglobin") or 14)
            r_spo = float(r.get("spo2") or 98)
            r_fit = fitness_score(r_bs, r_bd, r_sg, r_ch, r_hb, r_spo, age, gender)
            col_ = "#059669" if r_fit >= 70 else "#d97706" if r_fit >= 50 else "#dc2626"
            st.markdown(stat_bar(r.get("record_date","?"), r_fit, 100, col_), unsafe_allow_html=True)
        card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: SUGGESTIONS                                              ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_suggestions():
    page_header("💡", "Health Suggestions", "Personalised advice based on your latest saved metrics")
    user = get_user(st.session_state.username) or {}
    recs = _load_records()
    if not recs:
        st.info("No health data. Please upload a record first."); return
    selected = get_selected_record(recs)
    l    = selected or recs[-1]
    tips = get_suggestions(l.get("bp_systolic", 120), l.get("bp_diastolic", 80),
                           l.get("sugar", 90), l.get("cholesterol", 190))

    st.markdown(f"""<div class="card" style="margin-bottom:.8rem">
      <div style="font-size:.82rem;color:#5a6f99 !important;">
        Recommendations based on record dated <b style="color:#0d1e4a !important;">{l.get('record_date','—')}</b>
      </div>
    </div>""", unsafe_allow_html=True)

    card_open("Personalised Recommendations")
    for i, tip in enumerate(tips, 1):
        st.markdown(f"""<div class="dr">
          <span style="color:#d9880c !important;font-family:'Rajdhani',sans-serif;font-weight:700;
                       margin-right:12px;min-width:28px">{i:02d}</span>
          <span style="color:#0d1e4a !important;font-size:.9rem;font-weight:400">{tip}</span>
        </div>""", unsafe_allow_html=True)
    card_close()

    card_open("Shift-Friendly Diet Tips")
    meals = [("🌅","Before Duty","Oats + banana + 2 boiled eggs + green tea."),
             ("☀️","Mid Shift","Brown rice / 2 rotis + dal + sabzi."),
             ("🌙","Night Shift","Light — khichdi, curd, salad."),
             ("🚰","All Day","1 glass water every hour on duty.")]
    cols = st.columns(4)
    for col, (ico, title, text) in zip(cols, meals):
        with col:
            st.markdown(f"""<div style="background:#eaeff8;border-radius:12px;padding:1.1rem;text-align:center;border:1.5px solid #cdd7ee">
              <div style="font-size:1.5rem">{ico}</div>
              <div style="font-family:'Rajdhani',sans-serif;font-weight:700;color:#0d1e4a !important;font-size:.95rem;margin:.35rem 0">{title}</div>
              <div style="color:#2d3f6b !important;font-size:.84rem;line-height:1.7">{text}</div>
            </div>""", unsafe_allow_html=True)
    card_close()

    card_open("Exercise Routine for Police Officers")
    exercises = [
        ("🏃","Brisk Walk","20 min before shift, 5× weekly. Lowers BP by 5–8 mmHg."),
        ("🏋️","Bodyweight Strength","Push-ups, squats, lunges — 15 min, 3× weekly."),
        ("🧘","Breathing & Stretch","10 min yoga + 4-7-8 breathing before sleep."),
        ("🚲","Weekend Cardio","45 min cycling or swimming — boosts HDL cholesterol."),
    ]
    cols = st.columns(4)
    for col, (ico, title, text) in zip(cols, exercises):
        with col:
            st.markdown(f"""<div style="background:#e8faf2;border-radius:12px;padding:1.1rem;text-align:center;border:1.5px solid #9de8d8">
              <div style="font-size:1.5rem">{ico}</div>
              <div style="font-family:'Rajdhani',sans-serif;font-weight:700;color:#0b6e62 !important;font-size:.95rem;margin:.35rem 0">{title}</div>
              <div style="color:#2d3f6b !important;font-size:.84rem;line-height:1.7">{text}</div>
            </div>""", unsafe_allow_html=True)
    card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: HEALTH CHARTS                                            ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_charts():
    page_header("📈", "Health Charts", "Visual trends across all core parameters from saved records")
    user = get_user(st.session_state.username) or {}
    recs = _load_records()
    selected = get_selected_record(recs)
    if not recs:
        st.info("No data to chart. Upload a health record first."); return

    l = selected or recs[-1]
    card_open("Latest Reading — Visual Overview")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(donut(int(l.get("bp_systolic",120) or 120), 220, "#d9880c", "Systolic BP", "mmHg"), unsafe_allow_html=True)
    with c2: st.markdown(donut(int(l.get("sugar",90) or 90), 400, "#f59e0b", "Blood Sugar", "mg/dL"), unsafe_allow_html=True)
    with c3: st.markdown(donut(int(l.get("cholesterol",190) or 190), 400, "#0d9488", "Cholesterol", "mg/dL"), unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4: st.markdown(donut(int((l.get("haemoglobin",14) or 14)*10), 200, "#3b82f6", "Haemoglobin", "g/dL×10"), unsafe_allow_html=True)
    with c5: st.markdown(donut(int(l.get("spo2",98) or 98), 100, "#10b981", "SpO2", "%"), unsafe_allow_html=True)
    with c6: st.markdown(donut(int((l.get("bmi",23) or 23)*10), 400, "#7c3aed", "BMI", "×10"), unsafe_allow_html=True)
    card_close()

    if len(recs) >= 2:
        r5 = recs[-8:]  # show up to 8 records
        card_open(f"Trend Analysis — Last {len(r5)} Records")
        c1, c2 = st.columns(2)
        with c1:
            html = "".join(stat_bar(r["record_date"], int(r.get("bp_systolic") or 0), 220, "#d9880c") for r in r5)
            st.markdown(f"<div class='card'><div class='card-title'>Systolic BP (mmHg)</div>{html}</div>", unsafe_allow_html=True)
        with c2:
            html = "".join(stat_bar(r["record_date"], int(r.get("sugar") or 0), 400, "#f59e0b") for r in r5)
            st.markdown(f"<div class='card'><div class='card-title'>Blood Sugar (mg/dL)</div>{html}</div>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            html = "".join(stat_bar(r["record_date"], int(r.get("cholesterol") or 0), 400, "#0d9488") for r in r5)
            st.markdown(f"<div class='card'><div class='card-title'>Cholesterol (mg/dL)</div>{html}</div>", unsafe_allow_html=True)
        with c4:
            html = "".join(stat_bar(r["record_date"], int((r.get("haemoglobin") or 14)*10), 200, "#3b82f6") for r in r5)
            st.markdown(f"<div class='card'><div class='card-title'>Haemoglobin (g/dL ×10)</div>{html}</div>", unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        with c5:
            html = "".join(stat_bar(r["record_date"], int(r.get("spo2") or 0), 100, "#10b981") for r in r5)
            st.markdown(f"<div class='card'><div class='card-title'>SpO2 (%)</div>{html}</div>", unsafe_allow_html=True)
        with c6:
            valid_hr = [r for r in r5 if r.get("heart_rate")]
            if valid_hr:
                html = "".join(stat_bar(r["record_date"], int(r.get("heart_rate") or 0), 200, "#ef4444") for r in valid_hr)
                st.markdown(f"<div class='card'><div class='card-title'>Heart Rate (bpm)</div>{html}</div>", unsafe_allow_html=True)
        card_close()
    else:
        st.info("Add 2+ records to see trend charts.")

    # ── Streamlit native charts via pandas ─────────────────────────
    if len(recs) >= 2:
        import pandas as pd
        df = pd.DataFrame(recs)[["record_date","bp_systolic","bp_diastolic","sugar","cholesterol","spo2"]].dropna(how="all")
        df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
        df = df.dropna(subset=["record_date"]).sort_values("record_date")
        if not df.empty:
            st.markdown('<div class="sec-label">📊 &nbsp; Native Line Chart</div>', unsafe_allow_html=True)
            chart_cols = [c for c in ["bp_systolic","bp_diastolic","sugar","cholesterol"] if c in df.columns]
            df_plot = df.set_index("record_date")[chart_cols].dropna(how="all")
            if not df_plot.empty:
                st.line_chart(df_plot)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: FITNESS SCORE                                            ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_fitness():
    page_header("🏅", "Fitness Score", "Weighted composite health rating out of 100")
    user = get_user(st.session_state.username) or {}
    recs = _load_records()
    if not recs:
        st.info("No data. Please upload a record first."); return
    selected = get_selected_record(recs)
    l     = selected or recs[-1]
    bs, bd = float(l.get("bp_systolic") or 120), float(l.get("bp_diastolic") or 80)
    sg, ch = float(l.get("sugar") or 90), float(l.get("cholesterol") or 190)
    hb     = float(l.get("haemoglobin") or 14.0); spo2 = float(l.get("spo2") or 98)
    age    = user.get("age", 30); gender = user.get("gender", "Male")
    fit    = fitness_score(bs, bd, sg, ch, hb, spo2, age, gender)
    color  = "#059669" if fit >= 70 else "#d97706" if fit >= 50 else "#dc2626"
    label  = "EXCELLENT" if fit >= 80 else "GOOD" if fit >= 65 else "AVERAGE" if fit >= 50 else "NEEDS CARE"

    st.markdown(f"""<div class="card" style="margin-bottom:.8rem">
      <div style="font-size:.82rem;color:#5a6f99 !important;">
        Based on record dated <b style="color:#0d1e4a !important;">{l.get('record_date','—')}</b>
        &nbsp;·&nbsp; {len(recs)} total record{'s' if len(recs)!=1 else ''} on file
      </div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"""<div class="card" style="text-align:center;padding:2.5rem 1rem">
          <div style="font-family:'Rajdhani',sans-serif;font-size:5rem;font-weight:700;color:{color} !important;">{fit}</div>
          <div style="font-family:'Rajdhani',sans-serif;font-size:.85rem;color:{color} !important;letter-spacing:2.5px">{label}</div>
          <div style="color:#5a6f99 !important;font-size:.76rem;margin-top:.2rem">out of 100</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        bp_pt  = max(0, 25 - (max(0, int(bs) - 120) // 5) * 5)
        sg_pt  = max(0, 20 - (max(0, int(sg) - 90) // 5) * 5)
        ch_pt  = max(0, 20 - (max(0, int(ch) - 180) // 10) * 5)
        hb_pt  = 10 if hb >= (13.5 if gender == "Male" else 12.0) else 5
        spo_pt = 15 if spo2 >= 95 else 7 if spo2 >= 90 else 0
        age_pt = 10 if age <= 40 else 7 if age <= 50 else 5
        card_open("Score Breakdown")
        for nm, pt, mx, col in [
            ("Blood Pressure", bp_pt, 25, "#d9880c"),
            ("Blood Sugar", sg_pt, 20, "#f59e0b"),
            ("Cholesterol", ch_pt, 20, "#0d9488"),
            ("Haemoglobin", hb_pt, 10, "#3b82f6"),
            ("SpO2", spo_pt, 15, "#10b981"),
            ("Age Factor", age_pt, 10, "#7c3aed"),
        ]:
            st.markdown(stat_bar(f"{nm} ({pt}/{mx}pts)", pt, mx, col), unsafe_allow_html=True)
        card_close()

    # ── Fitness trend ──────────────────────────────────────────────
    if len(recs) >= 2:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        card_open("Fitness Trend — All Records")
        for r in recs[-10:]:
            r_fit = fitness_score(
                r.get("bp_systolic",120), r.get("bp_diastolic",80),
                r.get("sugar",90), r.get("cholesterol",190),
                r.get("haemoglobin",14), r.get("spo2",98), age, gender
            )
            col_ = "#059669" if r_fit >= 70 else "#d97706" if r_fit >= 50 else "#dc2626"
            st.markdown(stat_bar(r.get("record_date","?"), r_fit, 100, col_), unsafe_allow_html=True)
        card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: STRESS CALCULATOR                                        ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_stress():
    page_header("🧠", "Stress Calculator", "Occupational stress assessment for police personnel")
    with st.form("sf"):
        c1, c2 = st.columns(2)
        with c1:
            sleep    = st.slider("Nightly sleep (hours)", 3, 10, 7)
            workload = st.slider("Work pressure (0=low, 10=extreme)", 0, 10, 5)
        with c2:
            exercise = st.slider("Exercise days per week", 0, 7, 3)
            social   = st.slider("Social/family support (0=isolated, 10=strong)", 0, 10, 6)
        sub = st.form_submit_button("CALCULATE STRESS →", use_container_width=True)
    if sub:
        sc_  = stress_score(sleep, workload, exercise, social)
        col_ = "#059669" if sc_ < 30 else "#d97706" if sc_ < 60 else "#dc2626"
        lbl_ = "LOW" if sc_ < 30 else "MODERATE" if sc_ < 60 else "HIGH"
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"""<div class="card" style="text-align:center;padding:2rem">
              <div style="font-family:'Rajdhani',sans-serif;font-size:3.8rem;font-weight:700;color:{col_} !important;">{sc_}%</div>
              <div style="color:{col_} !important;font-family:'Rajdhani',sans-serif;letter-spacing:2px;font-size:.85rem;font-weight:700">{lbl_} STRESS</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            card_open("Breakdown & Advice")
            st.markdown(
                data_row("Sleep", f"{'✅ Adequate' if sleep >= 7 else '⚠️ Insufficient (Target: 7h)'}") +
                data_row("Work Pressure", f"{'🔴 High — request rotation' if workload >= 7 else '🟡 Moderate' if workload >= 4 else '🟢 Manageable'}") +
                data_row("Activity", f"{'✅ Active' if exercise >= 4 else '⚠️ Add 2 more active days'}") +
                data_row("Support", f"{'✅ Strong network' if social >= 6 else '⚠️ Connect with family/peers'}"),
                unsafe_allow_html=True)
            if sc_ >= 60:
                st.markdown("""<div class="alert-box alert-danger" style="margin-top:.5rem">
                  🆘 Contact your Police Welfare Officer | iCall: <b>9152987821</b> | Emergency: <b>112</b>
                </div>""", unsafe_allow_html=True)
            card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: HEALTH HISTORY                                           ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_history():
    page_header("📋", "Health History", "Complete log of all your saved health records")
    user = get_user(st.session_state.username) or {}
    recs = _load_records()
    if not recs:
        st.markdown("""<div class="card" style="text-align:center;padding:2.5rem">
          <div style="font-size:2.5rem;margin-bottom:.8rem">📋</div>
          <div style="font-family:'Rajdhani',sans-serif;color:#d9880c !important;font-size:1.1rem;font-weight:700">No Records Yet</div>
          <div style="color:#5a6f99 !important;font-size:.88rem;margin-top:.4rem">
            Go to <b>Upload Health Data</b> or <b>AI Upload Report</b> to add your first record.</div>
        </div>""", unsafe_allow_html=True)
        return

    total      = len(recs)
    ai_count   = sum(1 for r in recs if "AI" in (r.get("source") or ""))
    manual_count = total - ai_count
    selected = get_selected_record(recs)
    latest     = selected or recs[-1]

    st.markdown(f"""<div style="display:flex;gap:1rem;margin-bottom:1.2rem;flex-wrap:wrap;">
      <div class="card" style="flex:1;text-align:center;padding:1rem;min-width:120px">
        <div style="font-family:'Rajdhani',sans-serif;font-size:2rem;font-weight:700;color:#d9880c !important;">{total}</div>
        <div style="font-size:.78rem;color:#5a6f99 !important;font-weight:600">Total Records</div>
      </div>
      <div class="card" style="flex:1;text-align:center;padding:1rem;min-width:120px">
        <div style="font-family:'Rajdhani',sans-serif;font-size:2rem;font-weight:700;color:#0f9a8a !important;">{ai_count}</div>
        <div style="font-size:.78rem;color:#5a6f99 !important;font-weight:600">AI Uploaded</div>
      </div>
      <div class="card" style="flex:1;text-align:center;padding:1rem;min-width:120px">
        <div style="font-family:'Rajdhani',sans-serif;font-size:2rem;font-weight:700;color:#1a4fd6 !important;">{manual_count}</div>
        <div style="font-size:.78rem;color:#5a6f99 !important;font-weight:600">Manual Entry</div>
      </div>
      <div class="card" style="flex:1;text-align:center;padding:1rem;min-width:120px">
        <div style="font-family:'Rajdhani',sans-serif;font-size:1.1rem;font-weight:700;color:#0d1e4a !important;">{latest.get('record_date','—')}</div>
        <div style="font-size:.78rem;color:#5a6f99 !important;font-weight:600">Latest Record</div>
      </div>
    </div>""", unsafe_allow_html=True)

    card_open(f"All Records — {len(recs)} Total")
    table_rows = ""
    for i, r in enumerate(reversed(recs), 1):
        bs   = int(r.get("bp_systolic") or 0); bd = int(r.get("bp_diastolic") or 0)
        sg   = int(r.get("sugar") or 0);       ch = int(r.get("cholesterol") or 0)
        hb   = r.get("haemoglobin") or 0.0;    spo2 = int(r.get("spo2") or 0)
        src  = r.get("source", "Manual")
        bp_s, bp_c   = classify_bp(bs, bd)
        sg_s, sg_c   = classify_sugar(sg)
        spo_s, spo_c = classify_spo2(spo2)
        bpcol  = "#059669" if bp_c=="p-ok" else "#d97706" if bp_c=="p-warn" else "#dc2626"
        sgcol  = "#059669" if sg_c=="p-ok" else "#d97706" if sg_c=="p-warn" else "#dc2626"
        spocol = "#059669" if spo_c=="p-ok" else "#d97706" if spo_c=="p-warn" else "#dc2626"
        src_badge = f'<span class="pill p-teal">AI OCR</span>' if "AI" in src else f'<span class="pill p-ok">Manual</span>'
        table_rows += f"""<tr>
          <td class="num" style="color:#d9880c !important;">#{i}</td>
          <td class="num" style="color:#0d1e4a !important;">{r.get('record_date','—')}</td>
          <td class="num" style="color:{bpcol} !important;">{bs}/{bd}</td>
          <td class="num" style="color:{sgcol} !important;">{sg}</td>
          <td class="num" style="color:#0d1e4a !important;">{ch}</td>
          <td class="num" style="color:#0d1e4a !important;">{hb}</td>
          <td class="num" style="color:{spocol} !important;">{spo2}%</td>
          <td class="num" style="color:#0d1e4a !important;">{r.get('bmi','—')}</td>
          <td class="num" style="color:#0d1e4a !important;">{r.get('weight','—')} kg</td>
          <td>{src_badge}</td>
        </tr>"""
    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:10px;border:1.5px solid #cdd7ee">
      <table class="hist-table">
        <thead><tr>
          <th>#</th><th>Date</th><th>BP (mmHg)</th><th>Sugar</th>
          <th>Chol.</th><th>Hb</th><th>SpO2</th><th>BMI</th><th>Weight</th><th>Source</th>
        </tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>""", unsafe_allow_html=True)
    card_close()

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    card_open("Detailed Record View")
    for i, r in enumerate(reversed(recs), 1):
        bs, bd = int(r.get("bp_systolic") or 0), int(r.get("bp_diastolic") or 0)
        hb     = r.get("haemoglobin") or 0.0; spo2 = r.get("spo2") or 0
        src    = r.get("source", "Manual")
        src_icon = "🤖" if "AI" in src else "✍️"
        with st.expander(f"{src_icon} Record #{i} — {r.get('record_date','—')} | {src}"):
            c1, c2, c3 = st.columns(3)
            bp_s, bp_c = classify_bp(bs, bd)
            sg_s, sg_c = classify_sugar(r.get("sugar") or 0)
            ch_s, ch_c = classify_chol(r.get("cholesterol") or 0)
            with c1: st.markdown(metric_card("Blood Pressure", f"{bs}/{bd}", "mmHg", bp_s, bp_c), unsafe_allow_html=True)
            with c2: st.markdown(metric_card("Blood Sugar", str(int(r.get("sugar") or 0)), "mg/dL", sg_s, sg_c, "#f59e0b"), unsafe_allow_html=True)
            with c3: st.markdown(metric_card("Cholesterol", str(int(r.get("cholesterol") or 0)), "mg/dL", ch_s, ch_c, "#0d9488"), unsafe_allow_html=True)
            hb_s, hb_c   = classify_hb(hb, user.get("gender", "Male"))
            spo_s, spo_c = classify_spo2(spo2)
            bmi_s, bmi_c = classify_bmi(r.get("bmi") or 0)
            extra_fields = ""
            for field in ["ldl","hdl","triglycerides","creatinine","tsh","heart_rate","hba1c"]:
                val = r.get(field)
                if val: extra_fields += data_row(field.replace("_"," ").title(), str(val))
            st.markdown(
                data_row("Haemoglobin", f"{hb} g/dL — {hb_s}") +
                data_row("SpO2", f"{spo2}% — {spo_s}") +
                data_row("BMI", f"{r.get('bmi','—')} — {bmi_s}") +
                data_row("Weight", f"{r.get('weight','—')} kg") +
                (data_row("Diagnosis", r.get("diagnosis","")) if r.get("diagnosis") else "") +
                (data_row("Medicines", r.get("medicines","")[:80]) if r.get("medicines") else "") +
                (data_row("Doctor", r.get("doctor_name","")) if r.get("doctor_name") else "") +
                (data_row("Lab / Hospital", r.get("lab_name","")) if r.get("lab_name") else "") +
                extra_fields +
                data_row("Source", src) +
                (data_row("Notes", r.get("notes","")[:100]) if r.get("notes") else ""),
                unsafe_allow_html=True
            )
    card_close()


def page_admin_signup():
    page_header("🔐", "Admin Signup", "Register as a new administrator")
    with st.form("admin_signup_form"):
        email = st.text_input("Email (will be used as login ID)")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register Admin")
    if submitted:
        if not email or not password:
            st.error("Please fill all fields.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            existing = get_admin(email)
            if existing:
                st.error("This email is already registered as admin.")
            else:
                save_admin(email, hash_pw(password))
                st.success("Admin account created successfully! You can now login as admin.")

def page_admin_dashboard():
    if st.session_state.get("role") != "admin":
        st.error("Access denied. Admin dashboard is restricted to administrators only.")
        return

    page_header("🔒", "Admin Dashboard", "All health records from all officers")

    all_records = get_all_health_records()
    if not all_records:
        st.info("No health records found."); return

    st.markdown(f"""
      <div class="card" style="margin-bottom:1rem">
        <div style="font-size:.9rem;color:#5a6f99 !important;">
          Total records: <b>{len(all_records)}</b> from all officers.
        </div>
      </div>
    """, unsafe_allow_html=True)

    # Export to Excel
    df = pd.DataFrame(all_records)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_data = excel_buffer.getvalue()
    st.download_button(
        label="📊 Export All Records to Excel",
        data=excel_data,
        file_name="all_health_records.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    display_columns = [
        "badge", "name", "rank", "dept", "record_date", "source",
        "bp_systolic", "bp_diastolic", "heart_rate", "sugar", "cholesterol",
        "haemoglobin", "spo2", "weight", "height", "bmi",
        "ldl", "hdl", "triglycerides", "creatinine", "tsh", "hba1c",
        "lab_name", "doctor_name", "diagnosis"
    ]

    column_labels = {
        "badge": "Badge",
        "name": "Officer Name",
        "rank": "Rank",
        "dept": "Department",
        "record_date": "Record Date",
        "source": "Source",
        "bp_systolic": "BP Systolic",
        "bp_diastolic": "BP Diastolic",
        "heart_rate": "Heart Rate",
        "sugar": "Sugar",
        "cholesterol": "Cholesterol",
        "haemoglobin": "Haemoglobin",
        "spo2": "SpO2",
        "weight": "Weight",
        "height": "Height",
        "bmi": "BMI",
        "ldl": "LDL",
        "hdl": "HDL",
        "triglycerides": "Triglycerides",
        "creatinine": "Creatinine",
        "tsh": "TSH",
        "hba1c": "HbA1c",
        "lab_name": "Lab / Hospital",
        "doctor_name": "Doctor",
        "diagnosis": "Diagnosis"
    }

    df_display = pd.DataFrame(all_records)
    df_display = df_display.reindex(columns=display_columns)
    df_display = df_display.rename(columns=column_labels)
    df_display = df_display.fillna("—")

    st.markdown("### Summary")
    st.markdown(f"<div style='margin-bottom:0.8rem;color:#5a6f99;'>Displaying the latest {min(len(df_display), 100)} records for quick review. Export all records with the button above.</div>", unsafe_allow_html=True)
    st.dataframe(df_display.head(100), use_container_width=True, height=520)

    if len(all_records) > 100:
        st.info("Showing first 100 records in the dashboard. All records are included in the Excel export.")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: REMINDERS                                                ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_reminders():
    page_header("⏰", "Reminders & Schedule", "Manage your health checkup schedule")
    user  = get_user(st.session_state.username) or {}
    today = datetime.date.today()
    c1, c2 = st.columns(2)
    with c1:
        card_open("Configure Reminder")
        with st.form("rf"):
            months = st.selectbox("Checkup Interval", [3, 6],
                                  index=0 if (user.get("reminder_months") or 6) == 3 else 1,
                                  format_func=lambda x: f"Every {x} Months")
            last_c_def = user.get("last_checkup") or str(today)
            try: last_c_def = datetime.date.fromisoformat(str(last_c_def)[:10])
            except: last_c_def = today
            last_c = st.date_input("Last Checkup Date", last_c_def)
            if st.form_submit_button("SAVE →", use_container_width=True):
                update_user_field(st.session_state.username,
                                  reminder_months=months, last_checkup=str(last_c))
                st.success("Reminder updated.")
        card_close()
    with c2:
        m       = user.get("reminder_months") or 6
        ld_str  = user.get("last_checkup") or str(today)
        try: ld = datetime.date.fromisoformat(str(ld_str)[:10])
        except: ld = today
        nd   = ld + datetime.timedelta(days=m * 30)
        dl   = (nd - today).days
        col_ = "#dc2626" if dl < 0 else "#d97706" if dl <= 30 else "#059669"
        card_open("Schedule Summary")
        st.markdown(
            f'<div style="font-family:Rajdhani,sans-serif;font-size:1.5rem;color:{col_} !important;margin:.35rem 0;font-weight:700">{nd}</div>' +
            data_row("Status", 'Overdue '+str(abs(dl))+'d' if dl < 0 else str(dl)+'d remaining') +
            data_row("Interval", f"Every {m} months") +
            data_row("6-Test Cost", "~₹300 at Govt. Lab"),
            unsafe_allow_html=True
        )
        card_close()

    card_open("Upcoming Checkup Calendar")
    ld_str = user.get("last_checkup") or str(today)
    try: ld = datetime.date.fromisoformat(str(ld_str)[:10])
    except: ld = today
    m = user.get("reminder_months") or 6
    for i in range(1, 7):
        nd   = ld + datetime.timedelta(days=m * 30 * i)
        dl   = (nd - today).days; over = dl < 0
        col_ = "#dc2626" if over else "#d97706" if dl <= 30 else "#059669"
        tag  = "OVERDUE" if over else "DUE SOON" if dl <= 30 else "SCHEDULED"
        cls  = "p-danger" if over else "p-warn" if dl <= 30 else "p-ok"
        st.markdown(f"""<div class="sr">
          <span style="font-family:'Rajdhani',sans-serif;color:#d9880c !important;font-weight:700">#{i}</span>
          <span style="color:#0d1e4a !important;font-weight:700">{nd.strftime('%d %B %Y')}</span>
          <span style="color:#5a6f99 !important;font-size:.8rem">{nd.strftime('%A')}</span>
          <span class="pill {cls}">{tag}</span>
          <span style="color:{col_} !important;font-size:.8rem;font-weight:700">{str(abs(dl))+'d overdue' if over else str(dl)+'d'}</span>
        </div>""", unsafe_allow_html=True)
    card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: EXPORT DATA (NEW)                                        ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_export():
    page_header("📤", "Export Data", "Download your complete health records as CSV")
    recs = _load_records()
    user = get_user(st.session_state.username) or {}

    if not recs:
        st.info("No records to export. Upload health data first."); return

    import pandas as pd

    card_open("Export Health Records")
    st.markdown(f"""<div style="font-size:.9rem;color:#2d3f6b !important;line-height:1.9;margin-bottom:.8rem">
      You have <b style="color:#d9880c !important;">{len(recs)} records</b> on file.
      Export as CSV to keep a backup or share with your doctor.
    </div>""", unsafe_allow_html=True)

    df = pd.DataFrame(recs)
    # Drop internal DB columns from export
    for col in ["id","badge","created_at"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    csv = df.to_csv(index=False)
    st.download_button(
        label="⬇️  Download CSV",
        data=csv,
        file_name=f"SHIELD_health_{st.session_state.username}_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    st.markdown("**Preview (last 5 records):**")
    st.dataframe(df.tail(5), use_container_width=True, hide_index=True)
    card_close()

    card_open("Officer Summary Card")
    st.markdown(
        data_row("Name", f"{user.get('rank','')} {user.get('name','')}") +
        data_row("Badge", st.session_state.username) +
        data_row("Blood Group", user.get('blood_group','—')) +
        data_row("Department", user.get('dept','—')) +
        data_row("Emergency Contact", f"{user.get('emergency_contact','—')} — {user.get('emergency_phone','—')}") +
        data_row("Known Allergies", user.get('allergies','None') or 'None') +
        data_row("Pre-existing Conditions", (user.get('conditions','None') or 'None')[:80]) +
        data_row("Total Records", str(len(recs))),
        unsafe_allow_html=True
    )
    card_close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PAGE: HOSPITAL NETWORK                                         ║
# ╚══════════════════════════════════════════════════════════════════╝
def page_hospitals():
    page_header("🏥", "Hospital Network — Mumbai", "Empanelled hospitals across Mumbai region")
    st.markdown("""<div class="card" style="margin-bottom:1.2rem">
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;text-align:center">
        <div><div style="font-family:'Rajdhani',sans-serif;font-size:1.9rem;color:#d9880c !important;font-weight:700">21</div><div style="color:#5a6f99 !important;font-size:.84rem">Mumbai Hospitals</div></div>
        <div><div style="font-family:'Rajdhani',sans-serif;font-size:1.9rem;color:#0b6e62 !important;font-weight:700">FREE</div><div style="color:#5a6f99 !important;font-size:.84rem">Police Health Package</div></div>
        <div><div style="font-family:'Rajdhani',sans-serif;font-size:1.9rem;color:#1a4fd6 !important;font-weight:700">48h</div><div style="color:#5a6f99 !important;font-size:.84rem">Report Turnaround</div></div>
        <div><div style="font-family:'Rajdhani',sans-serif;font-size:1.9rem;color:#a81515 !important;font-weight:700">112</div><div style="color:#5a6f99 !important;font-size:.84rem">Police Emergency</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("🔍  Search by name or area", placeholder="e.g. KEM, Bandra, Andheri")
    with c2:
        type_filter = st.selectbox("Type", ["All","Government","Private"])

    filtered = get_hospitals(search)
    if type_filter != "All":
        filtered = [h for h in filtered if h.get("type") == type_filter]

    if not filtered:
        st.info("No hospitals found."); return
    st.markdown(f"<div style='color:#5a6f99 !important;font-size:.82rem;margin:.3rem 0 .8rem'>Showing {len(filtered)} hospitals</div>", unsafe_allow_html=True)

    for idx_h, h in enumerate(filtered, 1):
        type_cls = "p-ok" if h.get("type") == "Government" else "p-blue"
        st.markdown(f"""<div class="hosp-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem">
            <div style="flex:1">
              <div style="display:flex;align-items:center;gap:.55rem;margin-bottom:.3rem">
                <span style="font-family:'Rajdhani',sans-serif;font-size:.7rem;font-weight:700;
                  color:#d9880c !important;background:rgba(184,114,10,.08);padding:1px 8px;
                  border-radius:20px;border:1px solid rgba(184,114,10,.25)">#{idx_h}</span>
                <div class="hosp-name" style="color:#0d1e4a !important;">🏥 {h['name']}</div>
              </div>
              <div class="hosp-addr" style="color:#2d3f6b !important;">📍 {h['address']}</div>
              {f'<div style="color:#5a6f99 !important;font-size:.8rem;margin-top:.2rem;font-weight:500">📞 {h["phone"]}</div>' if h.get("phone") else ""}
            </div>
            <div style="display:flex;flex-direction:column;gap:.3rem;align-items:flex-end;flex-shrink:0">
              <span class="pill {type_cls}">{h.get("type","General")}</span>
              {f'<span class="pill p-navy">PIN {h["pincode"]}</span>' if h.get("pincode") else ""}
            </div>
          </div>
        </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  MAIN ROUTER                                                    ║
# ╚══════════════════════════════════════════════════════════════════╝
def main():
    # Initialize database on first run
    init_db()
    seed_hospitals()
    
    if not st.session_state.logged_in:
        if st.session_state.page == "Auth":
            page_auth()
        else:
            page_landing()
        return

    render_sidebar()
    p = st.session_state.page

    if   p == "Welcome":              page_welcome()
    elif p == "Importance":           page_importance()
    elif p == "Upload Health Data":   page_upload()
    elif p == "AI Upload Report":     page_report()
    elif p == "Prediction & Results": page_prediction()
    elif p == "Suggestions":          page_suggestions()
    elif p == "Health Charts":        page_charts()
    elif p == "Fitness Score":        page_fitness()
    elif p == "Stress Calculator":    page_stress()
    elif p == "Health History":       page_history()
    elif p == "Admin Dashboard":       page_admin_dashboard()
    elif p == "Admin Signup":          page_admin_signup()
    elif p == "Reminders":            page_reminders()
    elif p == "Export Data":          page_export()
    elif p == "Hospital Network":     page_hospitals()
    else:
        page_welcome()

    st.markdown("""<div class="af">
      <b>SHIELD</b> v6.0 — Smart Health Intelligence &amp; Emergency Life-care Dashboard &nbsp;·&nbsp;
      Police Wellness Division &nbsp;·&nbsp; Confidential &amp; Secure &nbsp;·&nbsp;
      &copy; 2026 Police Welfare Division &nbsp;·&nbsp; Emergency: <b>112</b>
    </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
