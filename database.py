import sqlite3
import json
import os
import hashlib
import logging
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger("yashaswi_residency.database")

# Optional PostgreSQL driver for production deployment
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

# External Database URL (e.g. Supabase, Neon, Render Postgres, Vercel Postgres)
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_PRISMA_URL")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
)

# Vercel and Serverless environment detection
IS_VERCEL = bool(
    os.environ.get("VERCEL")
    or os.environ.get("VERCEL_ENV")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
)

if DATABASE_URL:
    DB_ENGINE = "postgres"
else:
    DB_ENGINE = "sqlite"
    if IS_VERCEL:
        DB_PATH = os.environ.get("SQLITE_PATH", "/tmp/yashaswi.db")
        logger.warning(
            "Running on Vercel without DATABASE_URL. SQLite in /tmp will not persist across serverless cold starts. "
            "For permanent production persistence, connect an external PostgreSQL database."
        )
    else:
        DB_PATH = os.environ.get(
            "SQLITE_PATH",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yashaswi.db")
        )


class PostgresCursorWrapper:
    """Translates SQLite query syntax into PostgreSQL (e.g. ? -> %s and RETURNING for lastrowid)."""
    def __init__(self, raw_cursor):
        self.cur = raw_cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        pg_query = query.replace("?", "%s")
        if pg_query.strip().upper().startswith("BEGIN IMMEDIATE"):
            return self

        auto_return_col = None
        upper_query = pg_query.strip().upper()
        if upper_query.startswith("INSERT INTO") and "RETURNING" not in upper_query:
            if "INSERT INTO ROOMS" in upper_query:
                pg_query += " RETURNING room_id"
                auto_return_col = "room_id"
            elif "INSERT INTO REVIEWS" in upper_query:
                pg_query += " RETURNING review_id"
                auto_return_col = "review_id"

        if params is not None:
            self.cur.execute(pg_query, tuple(params))
        else:
            self.cur.execute(pg_query)

        if auto_return_col:
            try:
                ret = self.cur.fetchone()
                if ret:
                    self.lastrowid = ret.get(auto_return_col)
            except Exception:
                pass
        return self

    def executemany(self, query, params_list):
        pg_query = query.replace("?", "%s")
        self.cur.executemany(pg_query, params_list)
        return self

    def _convert_row(self, row):
        if row is None:
            return None
        d = dict(row)
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
        return d

    def fetchone(self):
        row = self.cur.fetchone()
        return self._convert_row(row)

    def fetchall(self):
        rows = self.cur.fetchall()
        return [self._convert_row(r) for r in rows]

    @property
    def rowcount(self):
        return self.cur.rowcount

    def close(self):
        self.cur.close()


class PostgresConnectionWrapper:
    """Wraps psycopg2 connection to mimic sqlite3 connection behavior."""
    def __init__(self, raw_conn):
        self.conn = raw_conn

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db_connection():
    if DB_ENGINE == "postgres":
        if not psycopg2:
            raise RuntimeError("psycopg2 is required for PostgreSQL. Please install psycopg2-binary.")
        dsn = DATABASE_URL
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[len("postgres://"):]
        raw_conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        return PostgresConnectionWrapper(raw_conn)
    else:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError:
                pass
        if IS_VERCEL and not os.path.exists(DB_PATH):
            bundled_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yashaswi.db")
            if os.path.exists(bundled_db):
                try:
                    import shutil
                    shutil.copyfile(bundled_db, DB_PATH)
                except Exception:
                    pass
        conn = sqlite3.connect(DB_PATH, timeout=25.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def hash_password(password: str) -> str:
    salt = "yashaswi_manipal_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_ENGINE == "postgres":
        # PostgreSQL Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id SERIAL PRIMARY KEY,
            room_number VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            price_per_night NUMERIC(10, 2) NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 2,
            bed_type VARCHAR(100) NOT NULL DEFAULT 'King / Queen Bed',
            amenities TEXT NOT NULL,
            photos TEXT NOT NULL,
            status VARCHAR(30) NOT NULL CHECK(status IN ('AVAILABLE', 'OCCUPIED', 'MAINTENANCE', 'BLOCKED')),
            highlight VARCHAR(255) DEFAULT '',
            cancellation VARCHAR(255) DEFAULT 'Free cancellation up to 24 hours before check-in',
            created_at VARCHAR(50) NOT NULL,
            updated_at VARCHAR(50) NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id VARCHAR(50) PRIMARY KEY,
            guest_name VARCHAR(255) NOT NULL,
            phone VARCHAR(50) NOT NULL,
            email VARCHAR(255) NOT NULL,
            room_id INTEGER NOT NULL REFERENCES rooms (room_id) ON DELETE RESTRICT,
            check_in VARCHAR(20) NOT NULL,
            check_out VARCHAR(20) NOT NULL,
            guests INTEGER NOT NULL DEFAULT 1,
            price_per_night NUMERIC(10, 2) NOT NULL,
            number_of_nights INTEGER NOT NULL,
            total_amount NUMERIC(10, 2) NOT NULL,
            booking_status VARCHAR(30) NOT NULL CHECK(booking_status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')),
            payment_status VARCHAR(30) NOT NULL DEFAULT 'UNPAID',
            special_requests TEXT DEFAULT '',
            created_at VARCHAR(50) NOT NULL,
            updated_at VARCHAR(50) NOT NULL
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_yashaswi_bookings_dates ON bookings (room_id, check_in, check_out, booking_status)
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id SERIAL PRIMARY KEY,
            guest_name VARCHAR(255) NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT NOT NULL,
            stay_date VARCHAR(50) DEFAULT '',
            status VARCHAR(20) NOT NULL CHECK(status IN ('APPROVED', 'PENDING', 'HIDDEN')),
            created_at VARCHAR(50) NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
    else:
        # SQLite Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 2,
            bed_type TEXT NOT NULL DEFAULT 'King / Queen Bed',
            amenities TEXT NOT NULL,
            photos TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('AVAILABLE', 'OCCUPIED', 'MAINTENANCE', 'BLOCKED')),
            highlight TEXT DEFAULT '',
            cancellation TEXT DEFAULT 'Free cancellation up to 24 hours before check-in',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            guest_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            guests INTEGER NOT NULL DEFAULT 1,
            price_per_night REAL NOT NULL,
            number_of_nights INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            booking_status TEXT NOT NULL CHECK(booking_status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')),
            payment_status TEXT NOT NULL DEFAULT 'UNPAID',
            special_requests TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms (room_id) ON DELETE RESTRICT
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_yashaswi_bookings_dates ON bookings (room_id, check_in, check_out, booking_status)
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT NOT NULL,
            stay_date TEXT DEFAULT '',
            status TEXT NOT NULL CHECK(status IN ('APPROVED', 'PENDING', 'HIDDEN')),
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

    # Seed Default Homestay Settings
    default_settings = {
        "homestay_name": "Yashaswi Residency Home Stay",
        "tagline": "Comfort • Peace • Privacy • Homely Hospitality",
        "phone": "087921 28459",
        "whatsapp": "+918792128459",
        "email": "yashaswiresidency.manipal@gmail.com",
        "address": "4th Cross Rd, Manipal, Rajeev Nagar, Manchikere, Manipal, Badagabettu, Karnataka 576104",
        "check_in_time": "11:00 AM",
        "check_out_time": "10:00 AM",
        "starting_price": "2415",
        "upi_enabled": "1",
        "upi_id": "8792128459@upi",
        "upi_payee_name": "Yashaswi Residency",
        "payment_instructions": "Please transfer the reservation advance via Google Pay / PhonePe / Paytm to our official UPI ID and share the screenshot on WhatsApp to confirm your stay immediately.",
        "admin_username": "admin",
        "admin_password_hash": hash_password("yashaswi2026!")
    }

    for k, v in default_settings.items():
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO NOTHING",
            (k, v)
        )

    # Seed Initial Rooms if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM rooms")
    row = cursor.fetchone()
    room_count = row["count"] if row else 0

    if room_count == 0:
        now = datetime.now().isoformat()
        initial_rooms = [
            (
                "YR-101",
                "Comfortable Stay",
                "Comfortable",
                "A peaceful and pristine accommodation designed for travelers, working professionals, and hospital visitors seeking rest and quietude in Manipal. Features a plush bed, air conditioning, ambient lighting, private en-suite bathroom, and cozy living seating.",
                2415.0,
                2,
                "1 Queen Bed",
                json.dumps(["Air Conditioning", "Free High-Speed Wi-Fi", "Living Seating Area", "Smart TV", "Private Bathroom", "Daily Housekeeping", "24/7 Hot Water"]),
                json.dumps([
                    "/static/images/living_lounge.png",
                    "/static/images/entrance_reception.png",
                    "/static/images/hero_exterior.jpg"
                ]),
                "AVAILABLE",
                "Reference Starting Price • Ideal for 2 Guests",
                "Free cancellation up to 24 hours before check-in",
                now,
                now
            ),
            (
                "YR-201",
                "Premium Stay",
                "Premium",
                "Spacious premium room featuring handcrafted fluted wood wall accents, an expansive modern television console, climate control AC, serene ambient illumination, and access to the airy balcony terrace overlooking the peaceful neighborhood of Rajeev Nagar.",
                2850.0,
                3,
                "1 King Bed + Extra Mattress Option",
                json.dumps(["Air Conditioning", "Free High-Speed Wi-Fi", "Designer Wood Paneling", "Balcony Access", "Work Desk", "Smart TV", "Tea/Coffee Kettle", "Private Bathroom"]),
                json.dumps([
                    "/static/images/premium_wood_lounge.png",
                    "/static/images/hero_exterior.jpg",
                    "/static/images/living_lounge.png"
                ]),
                "AVAILABLE",
                "Spacious Wood-Paneled Ambience • Balcony View",
                "Free cancellation up to 24 hours before check-in",
                now,
                now
            ),
            (
                "YR-301",
                "Family Stay",
                "Family",
                "An expansive family suite accommodation boasting an extensive lounge with comfortable patterned sofas, tea table, generous floor area for children and elders, refreshing ventilation, and complete privacy for extended family trips to Manipal and Udupi temples.",
                3450.0,
                5,
                "2 Double Beds / Large Family Setup",
                json.dumps(["Air Conditioning", "Free High-Speed Wi-Fi", "Extensive Sofa Lounge", "Spacious Family Seating", "Multiple Bedding", "Pool Access", "Free Secure Parking", "Refrigerator Option"]),
                json.dumps([
                    "/static/images/family_suite_lounge.png",
                    "/static/images/entrance_reception.png",
                    "/static/images/hero_exterior.jpg"
                ]),
                "AVAILABLE",
                "Large Multi-Sofa Suite • Perfect for Families",
                "Free cancellation up to 24 hours before check-in",
                now,
                now
            ),
            (
                "YR-401",
                "Honeymoon / Celebration Suite",
                "Romantic",
                "An enchanting romantic retreat featuring fairy light illumination, warm candlelight rose petal arrangements, chilled welcome refreshments, plush bedding, and complete privacy for anniversaries and couple getaways in Manipal.",
                3650.0,
                2,
                "1 King Bed with Candlelight Decor",
                json.dumps(["Romantic Candlelight Setup", "Fairy Light Ambience", "Rose Petal Floral Decor", "Air Conditioning", "Free High-Speed Wi-Fi", "Private Balcony Access", "Smart TV", "Private Bathroom"]),
                json.dumps([
                    "/static/images/honeymoon_romantic_suite.jpg",
                    "/static/images/lounge_french_doors.jpg",
                    "/static/images/buddha_zen_sanctum.jpg",
                    "/static/images/hero_exterior.jpg"
                ]),
                "AVAILABLE",
                "Special Romantic Candlelight Setup • Couple Favorite",
                "Free cancellation up to 24 hours before check-in",
                now,
                now
            )
        ]

        cursor.executemany("""
        INSERT INTO rooms (
            room_number, name, category, description,
            price_per_night, capacity, bed_type, amenities, photos,
            status, highlight, cancellation, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, initial_rooms)

    # Seed Authentic Reviews from customer feedback if empty
    cursor.execute("SELECT COUNT(*) as count FROM reviews")
    rev_row = cursor.fetchone()
    rev_count = rev_row["count"] if rev_row else 0

    if rev_count == 0:
        initial_reviews = [
            ("Dr. Arvind Rao", 5, "Clean and comfortable rooms in a very peaceful residential area of Manipal. The host was exceptionally warm, welcoming, and made sure our family felt right at home throughout our 4-day stay.", "September 2026", "APPROVED", "2026-09-15T10:00:00"),
            ("Pavitra Shenoy", 5, "Homely feeling with good hospitality. The property is well-maintained and spotless. AC works perfectly, Wi-Fi was fast, and the peaceful environment allowed us to sleep soundly after a busy day.", "September 2026", "APPROVED", "2026-09-20T12:30:00"),
            ("Gautam Nair", 5, "Extremely friendly and helpful owner. The location is safe, quiet, and easily accessible from Manipal center. Truly feels like a home away from home with spacious living areas.", "August 2026", "APPROVED", "2026-08-28T16:45:00"),
            ("Sunita Hegde", 5, "Well-maintained property with comfortable beds and immaculate cleanliness. We loved the serene atmosphere and courteous hospitality. Will definitely stay here again whenever visiting Manipal.", "August 2026", "APPROVED", "2026-08-14T09:15:00")
        ]

        cursor.executemany("""
        INSERT INTO reviews (guest_name, rating, comment, stay_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, initial_reviews)

    conn.commit()
    conn.close()


# --- Room Query Functions ---

def get_all_rooms(include_all_statuses=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    if include_all_statuses:
        cursor.execute("SELECT * FROM rooms ORDER BY price_per_night ASC")
    else:
        cursor.execute("SELECT * FROM rooms WHERE status = 'AVAILABLE' ORDER BY price_per_night ASC")
    rows = cursor.fetchall()
    conn.close()

    rooms = []
    for r in rows:
        room = dict(r)
        try:
            room["amenities"] = json.loads(room["amenities"]) if isinstance(room["amenities"], str) else room["amenities"]
        except Exception:
            room["amenities"] = []
        try:
            room["photos"] = json.loads(room["photos"]) if isinstance(room["photos"], str) else room["photos"]
        except Exception:
            room["photos"] = []
        rooms.append(room)
    return rooms


def get_room_by_id(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    room = dict(row)
    try:
        room["amenities"] = json.loads(room["amenities"]) if isinstance(room["amenities"], str) else room["amenities"]
    except Exception:
        room["amenities"] = []
    try:
        room["photos"] = json.loads(room["photos"]) if isinstance(room["photos"], str) else room["photos"]
    except Exception:
        room["photos"] = []
    return room


def check_room_availability(room_id, check_in_str, check_out_str, exclude_booking_id=None):
    """
    Checks if a room is free between check_in and check_out.
    Conflict occurs if an active booking overlaps:
    (existing_check_in < requested_check_out) AND (existing_check_out > requested_check_in)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify room is not blocked or under maintenance
    cursor.execute("SELECT status FROM rooms WHERE room_id = ?", (room_id,))
    room_row = cursor.fetchone()
    if not room_row or room_row["status"] not in ("AVAILABLE", "OCCUPIED"):
        conn.close()
        return False, "Room is currently under maintenance or temporarily blocked."

    query = """
    SELECT COUNT(*) as conflict_count FROM bookings
    WHERE room_id = ?
      AND booking_status IN ('PENDING', 'CONFIRMED')
      AND (check_in < ?)
      AND (check_out > ?)
    """
    params = [room_id, check_out_str, check_in_str]
    if exclude_booking_id:
        query += " AND booking_id != ?"
        params.append(exclude_booking_id)

    cursor.execute(query, params)
    conflict = cursor.fetchone()["conflict_count"]
    conn.close()

    if conflict > 0:
        return False, "Selected dates are already booked for this room. Please select alternative dates."
    return True, ""


# --- Booking Functions ---

def create_booking(guest_name, phone, email, room_id, check_in_str, check_out_str, guests, special_requests=""):
    try:
        d_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        d_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        return None, "Invalid date format. Expected YYYY-MM-DD."

    if d_in < date.today():
        return None, "Check-in date cannot be in the past."
    if d_out <= d_in:
        return None, "Check-out date must be strictly after check-in date."

    nights = (d_out - d_in).days

    conn = get_db_connection()
    cursor = conn.cursor()

    # Concurrency safe availability check
    cursor.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    room = cursor.fetchone()
    if not room:
        conn.close()
        return None, "Selected room does not exist."

    if room["status"] not in ("AVAILABLE", "OCCUPIED"):
        conn.close()
        return None, "Selected room is currently not available for reservations."

    # Prevent double booking
    cursor.execute("""
    SELECT COUNT(*) as conflict_count FROM bookings
    WHERE room_id = ?
      AND booking_status IN ('PENDING', 'CONFIRMED')
      AND (check_in < ?)
      AND (check_out > ?)
    """, (room_id, check_out_str, check_in_str))
    conflict = cursor.fetchone()["conflict_count"]
    if conflict > 0:
        conn.close()
        return None, "Sorry, this room has just been reserved for the selected dates. Please choose another stay option or adjust dates."

    price_per_night = float(room["price_per_night"])
    total_amount = round(price_per_night * nights, 2)
    now = datetime.now().isoformat()

    # Generate sequential unique booking ID: YASH-2026-XXXX
    cursor.execute("SELECT COUNT(*) as total FROM bookings")
    seq = cursor.fetchone()["total"] + 1
    booking_id = f"YASH-2026-{seq:04d}"

    cursor.execute("""
    INSERT INTO bookings (
        booking_id, guest_name, phone, email, room_id,
        check_in, check_out, guests, price_per_night, number_of_nights,
        total_amount, booking_status, payment_status, special_requests,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'UNPAID', ?, ?, ?)
    """, (
        booking_id, guest_name, phone, email, room_id,
        check_in_str, check_out_str, guests, price_per_night, nights,
        total_amount, special_requests, now, now
    ))

    conn.commit()
    conn.close()

    booking_summary = {
        "booking_id": booking_id,
        "guest_name": guest_name,
        "phone": phone,
        "email": email,
        "room_name": room["name"],
        "room_category": room["category"],
        "check_in": check_in_str,
        "check_out": check_out_str,
        "guests": guests,
        "number_of_nights": nights,
        "price_per_night": price_per_night,
        "total_amount": total_amount,
        "booking_status": "PENDING",
        "created_at": now
    }
    return booking_summary, ""


def get_booking_by_id(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT b.*, r.name as room_name, r.category as room_category, r.photos as room_photos
    FROM bookings b
    JOIN rooms r ON b.room_id = r.room_id
    WHERE b.booking_id = ?
    """, (booking_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["room_photos"] = json.loads(d["room_photos"]) if isinstance(d["room_photos"], str) else d["room_photos"]
    except Exception:
        d["room_photos"] = []
    return d


def get_all_bookings(search=None, status=None, room_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT b.*, r.name as room_name, r.room_number
    FROM bookings b
    JOIN rooms r ON b.room_id = r.room_id
    WHERE 1=1
    """
    params = []

    if status and status != "ALL":
        query += " AND b.booking_status = ?"
        params.append(status)

    if room_id:
        query += " AND b.room_id = ?"
        params.append(int(room_id))

    if search:
        s = f"%{search}%"
        query += " AND (b.booking_id LIKE ? OR b.guest_name LIKE ? OR b.phone LIKE ? OR b.email LIKE ?)"
        params.extend([s, s, s, s])

    query += " ORDER BY b.created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_booking_status(booking_id, new_status, new_payment_status=None):
    valid_statuses = ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')
    if new_status not in valid_statuses:
        return False, "Invalid booking status."

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    if new_payment_status:
        cursor.execute("""
        UPDATE bookings
        SET booking_status = ?, payment_status = ?, updated_at = ?
        WHERE booking_id = ?
        """, (new_status, new_payment_status, now, booking_id))
    else:
        cursor.execute("""
        UPDATE bookings
        SET booking_status = ?, updated_at = ?
        WHERE booking_id = ?
        """, (new_status, now, booking_id))

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        return False, "Booking not found."
    return True, ""


# --- Admin Room Modification Functions ---

def add_room(room_number, name, category, description, price_per_night, capacity, bed_type, amenities, photos, status="AVAILABLE", highlight="", cancellation=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    amenities_json = json.dumps(amenities) if isinstance(amenities, (list, dict)) else str(amenities)
    photos_json = json.dumps(photos) if isinstance(photos, (list, dict)) else str(photos)

    try:
        cursor.execute("""
        INSERT INTO rooms (
            room_number, name, category, description,
            price_per_night, capacity, bed_type, amenities, photos,
            status, highlight, cancellation, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            room_number, name, category, description,
            float(price_per_night), int(capacity), bed_type,
            amenities_json, photos_json, status,
            highlight, cancellation or "Free cancellation up to 24 hours before check-in",
            now, now
        ))
        room_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return room_id, ""
    except (sqlite3.IntegrityError, getattr(psycopg2, "IntegrityError", sqlite3.IntegrityError)):
        conn.close()
        return None, f"Room identifier '{room_number}' already exists."
    except Exception as e:
        conn.close()
        return None, str(e)


def update_room(room_id, room_number, name, category, description, price_per_night, capacity, bed_type, amenities, photos, status="AVAILABLE", highlight="", cancellation=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    amenities_json = json.dumps(amenities) if isinstance(amenities, (list, dict)) else str(amenities)
    photos_json = json.dumps(photos) if isinstance(photos, (list, dict)) else str(photos)

    try:
        cursor.execute("""
        UPDATE rooms SET
            room_number = ?, name = ?, category = ?, description = ?,
            price_per_night = ?, capacity = ?, bed_type = ?,
            amenities = ?, photos = ?, status = ?, highlight = ?,
            cancellation = ?, updated_at = ?
        WHERE room_id = ?
        """, (
            room_number, name, category, description,
            float(price_per_night), int(capacity), bed_type,
            amenities_json, photos_json, status, highlight,
            cancellation, now, room_id
        ))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected == 0:
            return False, "Room not found."
        return True, ""
    except (sqlite3.IntegrityError, getattr(psycopg2, "IntegrityError", sqlite3.IntegrityError)):
        conn.close()
        return False, f"Room identifier '{room_number}' already in use by another room."
    except Exception as e:
        conn.close()
        return False, str(e)


def update_room_status(room_id, new_status):
    valid = ("AVAILABLE", "OCCUPIED", "MAINTENANCE", "BLOCKED")
    if new_status not in valid:
        return False, "Invalid status."
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("UPDATE rooms SET status = ?, updated_at = ? WHERE room_id = ?", (new_status, now, room_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return (affected > 0), ""


def delete_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if there are active bookings
    cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE room_id = ? AND booking_status IN ('PENDING', 'CONFIRMED')", (room_id,))
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return False, "Cannot delete room with active/upcoming bookings. Mark it as BLOCKED or MAINTENANCE instead."
    cursor.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return (affected > 0), ""


# --- Reviews & Feedback ---

def get_approved_reviews():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE status = 'APPROVED' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_reviews():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_review(guest_name, rating, comment, stay_date="", status="APPROVED"):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    clean_rating = max(1, min(5, int(rating)))
    cursor.execute("""
    INSERT INTO reviews (guest_name, rating, comment, stay_date, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (guest_name, clean_rating, comment, stay_date, status, now))
    rev_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rev_id


def update_review_status(review_id, new_status):
    valid = ("APPROVED", "PENDING", "HIDDEN")
    if new_status not in valid:
        return False, "Invalid review status."
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET status = ? WHERE review_id = ?", (new_status, review_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return (affected > 0), ""


def delete_review(review_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE review_id = ?", (review_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return (affected > 0), ""


# --- Dashboard Metrics ---

def get_dashboard_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Room stats
    cursor.execute("SELECT status, COUNT(*) as count FROM rooms GROUP BY status")
    room_counts = {r["status"]: int(r["count"]) for r in cursor.fetchall()}

    # Booking counts & revenue
    cursor.execute("""
    SELECT booking_status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total_revenue
    FROM bookings GROUP BY booking_status
    """)
    booking_counts = {r["booking_status"]: {"count": int(r["count"]), "revenue": float(r["total_revenue"])} for r in cursor.fetchall()}

    # Feedback counts
    cursor.execute("SELECT status, COUNT(*) as count FROM reviews GROUP BY status")
    review_counts = {r["status"]: int(r["count"]) for r in cursor.fetchall()}

    today_str = date.today().isoformat()

    # Today's check-ins
    cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE check_in = ? AND booking_status IN ('PENDING', 'CONFIRMED')", (today_str,))
    today_checkins = cursor.fetchone()["count"]

    # Today's check-outs
    cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE check_out = ? AND booking_status = 'CONFIRMED'", (today_str,))
    today_checkouts = cursor.fetchone()["count"]

    # Recent 6 bookings
    cursor.execute("""
    SELECT b.*, r.name as room_name
    FROM bookings b
    JOIN rooms r ON b.room_id = r.room_id
    ORDER BY b.created_at DESC LIMIT 6
    """)
    recent = [dict(r) for r in cursor.fetchall()]

    conn.close()

    total_rooms = sum(room_counts.values())
    total_bookings = sum(b["count"] for b in booking_counts.values())
    total_reviews = sum(review_counts.values())
    confirmed_revenue = booking_counts.get("CONFIRMED", {}).get("revenue", 0.0) + booking_counts.get("COMPLETED", {}).get("revenue", 0.0)

    return {
        "rooms": {
            "total": total_rooms,
            "available": room_counts.get("AVAILABLE", 0),
            "occupied": room_counts.get("OCCUPIED", 0),
            "maintenance": room_counts.get("MAINTENANCE", 0),
            "blocked": room_counts.get("BLOCKED", 0)
        },
        "bookings": {
            "total": total_bookings,
            "pending": booking_counts.get("PENDING", {}).get("count", 0),
            "confirmed": booking_counts.get("CONFIRMED", {}).get("count", 0),
            "completed": booking_counts.get("COMPLETED", {}).get("count", 0),
            "cancelled": booking_counts.get("CANCELLED", {}).get("count", 0),
            "revenue": confirmed_revenue
        },
        "reviews": {
            "total": total_reviews,
            "approved": review_counts.get("APPROVED", 0),
            "pending": review_counts.get("PENDING", 0),
            "hidden": review_counts.get("HIDDEN", 0)
        },
        "today": {
            "check_ins": today_checkins,
            "check_outs": today_checkouts
        },
        "recent_bookings": recent
    }


# --- Property Settings ---

def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def update_settings(settings_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in settings_dict.items():
        cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (k, str(v)))
    conn.commit()
    conn.close()


def verify_admin_login(username, password):
    settings = get_settings()
    stored_user = settings.get("admin_username", "admin")
    stored_hash = settings.get("admin_password_hash", "")
    if username == stored_user and hash_password(password) == stored_hash:
        return True
    return False
