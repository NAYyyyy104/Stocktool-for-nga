#!/usr/bin/env python3
import json
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("CGP_HOST", "127.0.0.1")
PORT = int(os.environ.get("CGP_PORT", "8765"))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("CGP_DATA_DIR", os.path.join(BASE_DIR, "data"))
DATA_FILE = os.path.join(DATA_DIR, "cgp-data.json")
BACKUP_FILE = os.path.join(DATA_DIR, "cgp-data.backup.json")
CALENDAR_DB_FILE = os.path.join(DATA_DIR, "market-calendar.db")

state_lock = threading.Lock()
calendar_lock = threading.Lock()

DEFAULT_2026_HOLIDAYS = [
    ("2026-01-01", "元旦"),
    ("2026-01-02", "元旦"),
    ("2026-01-03", "元旦"),
    ("2026-02-15", "春节"),
    ("2026-02-16", "春节"),
    ("2026-02-17", "春节"),
    ("2026-02-18", "春节"),
    ("2026-02-19", "春节"),
    ("2026-02-20", "春节"),
    ("2026-02-21", "春节"),
    ("2026-02-22", "春节"),
    ("2026-02-23", "春节"),
    ("2026-04-04", "清明节"),
    ("2026-04-05", "清明节"),
    ("2026-04-06", "清明节"),
    ("2026-05-01", "劳动节"),
    ("2026-05-02", "劳动节"),
    ("2026-05-03", "劳动节"),
    ("2026-05-04", "劳动节"),
    ("2026-05-05", "劳动节"),
    ("2026-06-19", "端午节"),
    ("2026-06-20", "端午节"),
    ("2026-06-21", "端午节"),
    ("2026-09-25", "中秋节"),
    ("2026-09-26", "中秋节"),
    ("2026-09-27", "中秋节"),
    ("2026-10-01", "国庆节"),
    ("2026-10-02", "国庆节"),
    ("2026-10-03", "国庆节"),
    ("2026-10-04", "国庆节"),
    ("2026-10-05", "国庆节"),
    ("2026-10-06", "国庆节"),
    ("2026-10-07", "国庆节"),
]


def default_state():
    return {"watchlist": [], "holdings": [], "watchCategories": []}


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_state(raw):
    if isinstance(raw, list):
        return {"watchlist": raw, "holdings": [], "watchCategories": []}

    if not isinstance(raw, dict):
        return default_state()

    watchlist = raw.get("watchlist")
    holdings = raw.get("holdings")
    watch_categories = raw.get("watchCategories")
    return {
        "watchlist": watchlist if isinstance(watchlist, list) else [],
        "holdings": holdings if isinstance(holdings, list) else [],
        "watchCategories": watch_categories if isinstance(watch_categories, list) else [],
    }


def load_state():
    for path in (DATA_FILE, BACKUP_FILE):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                return normalize_state(json.load(f))
        except Exception:
            continue
    return default_state()


def save_state(payload):
    os.makedirs(DATA_DIR, exist_ok=True)
    data = normalize_state(payload)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    temp = DATA_FILE + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temp, DATA_FILE)

    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        f.write(text)


def ensure_calendar_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(CALENDAR_DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS market_holidays (
                date TEXT PRIMARY KEY,
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cur.executemany(
            "INSERT OR IGNORE INTO market_holidays(date, note) VALUES (?, ?)",
            DEFAULT_2026_HOLIDAYS,
        )
        conn.commit()
    finally:
        conn.close()


def _validate_ymd(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except Exception:
        return False


def list_holidays(year=None):
    ensure_calendar_db()
    conn = sqlite3.connect(CALENDAR_DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        if year:
            cur.execute(
                "SELECT date, note FROM market_holidays WHERE date LIKE ? ORDER BY date ASC",
                (f"{year}-%",),
            )
        else:
            cur.execute("SELECT date, note FROM market_holidays ORDER BY date ASC")
        rows = cur.fetchall()
        return [{"date": row["date"], "note": row["note"]} for row in rows]
    finally:
        conn.close()


def upsert_holiday(date_text, note=""):
    if not isinstance(date_text, str) or not _validate_ymd(date_text):
        raise ValueError("Invalid date format, expected YYYY-MM-DD")

    ensure_calendar_db()
    conn = sqlite3.connect(CALENDAR_DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO market_holidays(date, note) VALUES (?, ?) "
            "ON CONFLICT(date) DO UPDATE SET note = excluded.note",
            (date_text, str(note or "")),
        )
        conn.commit()
    finally:
        conn.close()


def remove_holiday(date_text):
    if not isinstance(date_text, str) or not _validate_ymd(date_text):
        raise ValueError("Invalid date format, expected YYYY-MM-DD")

    ensure_calendar_db()
    conn = sqlite3.connect(CALENDAR_DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM market_holidays WHERE date = ?", (date_text,))
        conn.commit()
    finally:
        conn.close()


def parse_qt_line(line):
    line = line.strip().rstrip(";")
    if not line.startswith("v_") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    code = key[2:]
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    fields = value.split("~")
    if len(fields) < 38:
        return None

    name = fields[1]
    now = to_float(fields[3])
    close = to_float(fields[4])
    high = to_float(fields[33], now)
    low = to_float(fields[34], now)
    volume = to_float(fields[36])
    turnover = to_float(fields[37])

    if code.startswith("hk"):
        avg = (turnover / volume) if volume > 0 else close
    else:
        if volume > 0:
            avg_hand = (turnover * 10000) / (volume * 100)
            avg_share = (turnover * 10000) / volume
            if now > 0 and avg_hand > 0 and (now / avg_hand) >= 10:
                avg = avg_share
            elif now > 0:
                avg = avg_hand if abs(avg_hand - now) <= abs(avg_share - now) else avg_share
            else:
                avg = avg_hand
        else:
            avg = close

    return {
        "fullCode": code,
        "name": name,
        "now": round(now, 3),
        "close": round(close, 3),
        "high": round(high, 3),
        "low": round(low, 3),
        "avg": round(avg, 3),
    }


def fetch_quotes(codes):
    clean_codes = []
    seen = set()
    for item in codes:
        if not isinstance(item, str):
            continue
        code = item.strip().lower()
        if not code or code in seen:
            continue
        seen.add(code)
        clean_codes.append(code)

    if not clean_codes:
        return []

    query = ",".join(clean_codes)
    url = "https://qt.gtimg.cn/q=" + urllib.parse.quote(query)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"},
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        text = resp.read().decode("gbk", errors="ignore")

    quote_map = {}
    for line in text.splitlines():
        parsed = parse_qt_line(line)
        if parsed:
            quote_map[parsed["fullCode"]] = parsed

    return [quote_map[c] for c in clean_codes if c in quote_map]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_json({"ok": True})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/health":
            self.send_json({"ok": True, "ts": int(time.time())})
            return

        if path == "/api/state":
            with state_lock:
                state = load_state()
            self.send_json({"ok": True, "data": state})
            return

        if path == "/api/calendar/holidays":
            year = query.get("year", [None])[0]
            try:
                with calendar_lock:
                    data = list_holidays(year=year)
                self.send_json({"ok": True, "data": data})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return

        self.send_json({"ok": False, "error": "Not Found"}, status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/state":
            payload = self.read_json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if data is None:
                self.send_json({"ok": False, "error": "Missing data"}, status=400)
                return
            try:
                with state_lock:
                    save_state(data)
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return

        if path == "/api/quotes":
            payload = self.read_json()
            codes = payload.get("codes", []) if isinstance(payload, dict) else []
            try:
                data = fetch_quotes(codes)
                self.send_json({"ok": True, "data": data})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=502)
            return

        if path == "/api/calendar/holidays":
            payload = self.read_json()
            date_text = payload.get("date") if isinstance(payload, dict) else None
            note = payload.get("note", "") if isinstance(payload, dict) else ""
            try:
                with calendar_lock:
                    upsert_holiday(date_text, note)
                    data = list_holidays()
                self.send_json({"ok": True, "data": data})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=400)
            return

        self.send_json({"ok": False, "error": "Not Found"}, status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/calendar/holidays":
            date_text = query.get("date", [None])[0]
            try:
                with calendar_lock:
                    remove_holiday(date_text)
                    data = list_holidays()
                self.send_json({"ok": True, "data": data})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=400)
            return

        self.send_json({"ok": False, "error": "Not Found"}, status=404)

    def log_message(self, fmt, *args):
        return


def main():
    ensure_calendar_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[cgp-python] listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
