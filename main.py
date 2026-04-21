import asyncio
import subprocess
import socket
import re
import sqlite3
import datetime
import threading
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HOTSPOT_IP = "192.168.137.1"
SUBNET     = "192.168.137"
SCAN_INTERVAL = 5   # seconds between scans
LECTURE_MINUTES = 1  # 2 hours 40 minutes

DB_FILE = "attendance.db"

# ─── Database Setup ────────────────────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS students (
                mac TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT,
                date TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                manual_status TEXT,
                connected_seconds REAL DEFAULT 0.0,
                FOREIGN KEY(mac) REFERENCES students(mac)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS archived_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT,
                date TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                manual_status TEXT,
                connected_seconds REAL DEFAULT 0.0,
                FOREIGN KEY(mac) REFERENCES students(mac)
            )
        """)
        try:
            c.execute("ALTER TABLE sessions ADD COLUMN connected_seconds REAL DEFAULT 0.0")
            c.execute("ALTER TABLE archived_sessions ADD COLUMN connected_seconds REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass
        conn.commit()

# Run init
init_db()


# ─── Scanner Helpers ───────────────────────────────────────────────────────────

def get_hotspot_ip():
    try:
        out = subprocess.check_output("ipconfig /all", text=True, shell=True)
        for block in re.split(r"\r?\n\r?\n", out):
            if any(k in block for k in ["Wi-Fi Direct", "Local Area Connection*", "Hosted Network"]):
                m = re.search(r"IPv4 Address[\s.]+:\s*([\d.]+)", block)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return HOTSPOT_IP

def ping_sweep():
    # To avoid hanging the event loop, we don't wait for all subprocesses here if not necessary,
    # but since this runs in a background thread, it's fine.
    procs = []
    for i in range(1, 255):
        ip = f"{SUBNET}.{i}"
        p = subprocess.Popen(
            ["ping", "-n", "1", "-w", "200", ip],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        procs.append(p)
    for p in procs:
        p.wait()

def read_arp_table():
    devices, seen = [], set()
    try:
        out = subprocess.check_output("arp -a", text=True, shell=True)
        for line in out.splitlines():
            m = re.match(r"\s*(192\.168\.137\.\d+)\s+([\w-]+)\s+(\w+)", line)
            if m:
                ip, mac = m.group(1), m.group(2).upper()
                if ip.endswith(".255") or ip in seen:
                    continue
                seen.add(ip)
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    hostname = "Unknown"
                devices.append({"ip": ip, "mac": mac, "hostname": hostname})
    except Exception as e:
        print(f"  [!] ARP error: {e}")
    return devices

# ─── State ─────────────────────────────────────────────────────────────────────

latest_data = {}
data_lock = threading.Lock()

def update_sessions(detected_macs):
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now()
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        c.execute("SELECT mac FROM students")
        registered_macs = set(row[0] for row in c.fetchall())
        
        for mac in detected_macs:
            if mac not in registered_macs:
                continue
                
            c.execute("SELECT id, last_seen FROM sessions WHERE mac = ? AND date = ?", (mac, today))
            row = c.fetchone()
            if row:
                last_seen_dt = datetime.datetime.fromisoformat(row[1])
                diff_sec = (now - last_seen_dt).total_seconds()
                added_sec = diff_sec if diff_sec <= SCAN_INTERVAL * 2 else SCAN_INTERVAL
                c.execute("UPDATE sessions SET last_seen = ?, connected_seconds = connected_seconds + ? WHERE id = ?", (now.isoformat(), added_sec, row[0]))
            else:
                c.execute("INSERT INTO sessions (mac, date, first_seen, last_seen, connected_seconds) VALUES (?, ?, ?, ?, ?)", 
                          (mac, today, now.isoformat(), now.isoformat(), SCAN_INTERVAL))
        conn.commit()

def calculate_status(session_row):
    # session_row: (first_seen, last_seen, manual_status, connected_seconds)
    if not session_row:
        return "absent", 0
    
    first_seen_str, last_seen_str, manual_status, connected_seconds = session_row
    
    if manual_status:
        return manual_status.lower(), 0
        
    duration_minutes = connected_seconds / 60.0
    
    status = "absent"
    
    # If connected straight for at least 20 seconds
    if connected_seconds >= 20: 
        status = "partial"
    
    # If duration connected is near full lecture length, mark as present.
    if duration_minutes >= LECTURE_MINUTES * 0.8:
        status = "present"
        
    return status, round(duration_minutes)

def build_attendance(devices, my_ip):
    connected = [d for d in devices if d["ip"] != my_ip]
    connected_macs = {d["mac"]: d for d in connected}
    
    # Update sessions for connected devices
    update_sessions(list(connected_macs.keys()))
    
    today = datetime.date.today().isoformat()
    
    students_out = []
    present_count = 0
    absent_count = 0
    partial_count = 0
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT mac, name FROM students")
        registered_students = c.fetchall()
        
        for mac, name in registered_students:
            c.execute("SELECT first_seen, last_seen, manual_status, connected_seconds FROM sessions WHERE mac = ? AND date = ?", (mac, today))
            session_row = c.fetchone()
            
            status, duration = calculate_status(session_row)
            
            if status == "present":
                present_count += 1
            elif status == "partial":
                partial_count += 1
            else:
                absent_count += 1
                
            dev_info = connected_macs.get(mac, {"ip": None, "hostname": None})
            
            students_out.append({
                "name": name, 
                "mac": mac,
                "ip": dev_info["ip"], 
                "hostname": dev_info["hostname"],
                "status": status,
                "connected_minutes": duration
            })

    # unknown devices
    registered_macs = set(s[0] for s in registered_students)
    unknown = [d for d in connected if d["mac"] not in registered_macs]

    return {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hotspot_ip": my_ip,
        "total": len(registered_students),
        "present": present_count,
        "partial": partial_count,
        "absent": absent_count,
        "students": students_out,
        "unknown": unknown,
        "next_scan_in": SCAN_INTERVAL,
    }


def background_scanner():
    my_ip = get_hotspot_ip()
    print(f"  Scanner started — hotspot IP: {my_ip}")
    while True:
        try:
            ping_sweep()
            devices = read_arp_table()
            data = build_attendance(devices, my_ip)
            with data_lock:
                global latest_data
                latest_data = data
        except Exception as e:
            print(f"Error in scanner loop: {e}")
            
        time.sleep(SCAN_INTERVAL)

import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clear sessions on startup so every server restart provides a clean slate for testing
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM sessions")
        conn.commit()

    # Clear Windows ARP cache so stale devices from previous runs aren't falsely detected
    try:
        subprocess.run(["arp", "-d", "*"], capture_output=True)
    except Exception:
        pass

    # Start background scanner on startup
    t = threading.Thread(target=background_scanner, daemon=True)
    t.start()
    yield
    # Shutdown: copy sessions to archived_sessions before stopping
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO archived_sessions (mac, date, first_seen, last_seen, manual_status, connected_seconds)
            SELECT mac, date, first_seen, last_seen, manual_status, connected_seconds FROM sessions
        """)
        conn.commit()

app = FastAPI(lifespan=lifespan)

# ─── API Routes ────────────────────────────────────────────────────────────────

@app.get("/attendance")
def get_attendance():
    """Returns the live attendance payload."""
    with data_lock:
        payload = dict(latest_data)
    if not payload:
        return {"status": "scanning", "message": "First scan in progress..."}
    return payload

class StudentInput(BaseModel):
    name: str
    mac: str

@app.post("/api/students")
def add_student(s: StudentInput):
    mac = s.mac.strip().upper()
    name = s.name.strip()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO students (mac, name) VALUES (?, ?)", (mac, name))
            conn.commit()
            return {"status": "success"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="MAC Address already exists")

@app.put("/api/students/{mac}")
def update_student(mac: str, s: StudentInput):
    old_mac = mac.strip().upper()
    new_mac = s.mac.strip().upper()
    name = s.name.strip()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE students SET mac = ?, name = ? WHERE mac = ?", (new_mac, name, old_mac))
        conn.commit()
        return {"status": "success"}

@app.delete("/api/students/{mac}")
def delete_student(mac: str):
    mac = mac.strip().upper()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE mac = ?", (mac,))
        conn.commit()
        return {"status": "success"}

class ManualStatus(BaseModel):
    status: str # "Present", "Absent", "Partial", or "" to reset

@app.post("/api/students/{mac}/manual")
def set_manual_status(mac: str, s: ManualStatus):
    mac = mac.strip().upper()
    status = s.status if s.status else None
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().isoformat()
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM sessions WHERE mac = ? AND date = ?", (mac, today))
        row = c.fetchone()
        if row:
            c.execute("UPDATE sessions SET manual_status = ? WHERE id = ?", (status, row[0]))
        else:
            c.execute("INSERT INTO sessions (mac, date, first_seen, last_seen, manual_status, connected_seconds) VALUES (?, ?, ?, ?, ?, ?)", 
                      (mac, today, now, now, status, 0.0))
        conn.commit()
        return {"status": "success"}

# ─── Static files routing ──────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse("dashboard.html")

@app.get("/admin")
def admin():
    return FileResponse("admin.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
