#!/usr/bin/env python3
"""
Windows Hotspot Attendance Monitor
- Scans hotspot devices every 20 seconds
- Serves live attendance data at http://localhost:5000/attendance
- Open dashboard.html in your browser to see the live UI
Run as Administrator for best results.
"""

import subprocess, socket, re, time, sys, json, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

HOTSPOT_IP = "192.168.137.1"
SUBNET     = "192.168.137"
SCAN_INTERVAL = 5   # seconds between scans

# ─── Student Registry ──────────────────────────────────────────────────────────
# Format:  "MAC Address" : "Student Name"
# How to find a student's MAC:
#   Run script → unknown devices section shows their MAC → paste it here.
STUDENTS = {
    "52-38-90-11-30-72": "Abdul Rehman",   # replace with real MAC
    "4A-AC-F0-5F-3D-A7": "Shariq Syed",
    "5A-C4-4E-39-02-4C": "Sami Ullah",
}
# ───────────────────────────────────────────────────────────────────────────────

# Shared state updated by scanner thread, read by web server
latest_data = {}
data_lock   = threading.Lock()


# ── Scanner ────────────────────────────────────────────────────────────────────

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
    procs = []
    for i in range(1, 255):
        ip = f"{SUBNET}.{i}"
        p = subprocess.Popen(
            ["ping", "-n", "1", "-w", "400", ip],
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


def build_attendance(devices, my_ip):
    connected     = [d for d in devices if d["ip"] != my_ip]
    connected_macs = {d["mac"]: d for d in connected}
    registered_macs = set(STUDENTS.keys())

    students_out = []
    present_count = 0
    for mac, name in STUDENTS.items():
        if mac in connected_macs:
            dev = connected_macs[mac]
            students_out.append({
                "name": name, "mac": mac,
                "ip": dev["ip"], "hostname": dev["hostname"],
                "status": "present"
            })
            present_count += 1
        else:
            students_out.append({
                "name": name, "mac": mac,
                "ip": None, "hostname": None,
                "status": "absent"
            })

    unknown = [d for d in connected if d["mac"] not in registered_macs]

    return {
        "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hotspot_ip":    my_ip,
        "total":         len(STUDENTS),
        "present":       present_count,
        "absent":        len(STUDENTS) - present_count,
        "students":      students_out,
        "unknown":       unknown,
        "next_scan_in":  SCAN_INTERVAL,
    }


def scanner_loop(my_ip):
    global latest_data
    print(f"  Scanner started — hotspot IP: {my_ip}")
    while True:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Scanning...")
        ping_sweep()
        devices = read_arp_table()
        data    = build_attendance(devices, my_ip)
        with data_lock:
            latest_data = data
        present = data["present"]
        total   = data["total"]
        print(f"  Done — {present}/{total} present. Next scan in {SCAN_INTERVAL}s.")
        time.sleep(SCAN_INTERVAL)


# ── Web Server ─────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence request logs

    def do_GET(self):
        if self.path == "/attendance":
            with data_lock:
                payload = dict(latest_data)
            body = json.dumps(payload if payload else {"status": "scanning", "message": "First scan in progress..."}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("   📡  Hotspot Attendance Monitor")
    print("=" * 60)

    my_ip = get_hotspot_ip()
    print(f"\n  Hotspot IP   : {my_ip}")
    print(f"  Scan interval: every {SCAN_INTERVAL}s")
    print(f"  API endpoint : http://localhost:5000/attendance")
    print(f"\n  → Open dashboard.html in your browser")
    print(f"  → Press Ctrl+C to stop\n")

    # Start scanner in background thread
    t = threading.Thread(target=scanner_loop, args=(my_ip,), daemon=True)
    t.start()

    # Start web server (blocking)
    server = HTTPServer(("localhost", 5000), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  Stopped. 👋\n")


if __name__ == "__main__":
    main()