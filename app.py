import os
import secrets
import json
import logging
import tempfile
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, send_from_directory
)
from werkzeug.utils import secure_filename
import database

logger = logging.getLogger("yashaswi_residency")

base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(base_dir, "static"),
    template_folder=os.path.join(base_dir, "templates")
)
app.secret_key = os.environ.get("SECRET_KEY", "yashaswi-residency-manipal-secret-key-2026")

class VercelPathNormalizer:
    """Normalizes PATH_INFO when deployed via Vercel Serverless Function rewrites."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        for prefix in ["/api/index.py", "/api/index", "/api/app.py", "/api/app"]:
            if path == prefix:
                environ["PATH_INFO"] = "/"
                break
            elif path.startswith(prefix + "/"):
                environ["PATH_INFO"] = path[len(prefix):]
                break
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathNormalizer(app.wsgi_app)

# Vercel and Serverless environment detection
IS_VERCEL = bool(
    os.environ.get("VERCEL")
    or os.environ.get("VERCEL_ENV")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
)

# Upload directory: Safe temp location on serverless, never inside static/ at import time
if IS_VERCEL:
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")
else:
    app.config["UPLOAD_FOLDER"] = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(tempfile.gettempdir(), "yashaswi_uploads")
    )

# Safe non-blocking database initialization
try:
    database.init_db()
except Exception as e:
    logger.warning("Database init deferred: %s", e)

_db_ready = False

@app.before_request
def ensure_db():
    global _db_ready
    if not _db_ready:
        try:
            database.init_db()
            _db_ready = True
        except Exception as e:
            logger.warning("ensure_db: %s", e)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            if request.is_json or request.path.startswith("/api/admin"):
                return jsonify({"error": "Unauthorized. Please login as admin."}), 401
            return redirect(url_for("admin_login_page"))
        return f(*args, **kwargs)
    return decorated_function


# --- Public Web Pages ---

@app.route("/")
@app.route("/api/index.py")
@app.route("/api/index")
@app.route("/api/app.py")
@app.route("/api/app")
def index():
    settings = database.get_settings()
    rooms = database.get_all_rooms(include_all_statuses=True)
    reviews = database.get_approved_reviews()
    return render_template(
        "index.html",
        settings=settings,
        rooms=rooms,
        reviews=reviews,
        today=date.today().isoformat()
    )


@app.route("/admin/login")
@app.route("/api/index.py/admin/login")
@app.route("/api/index/admin/login")
def admin_login_page():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard_page"))
    settings = database.get_settings()
    return render_template("admin_login.html", settings=settings)


@app.route("/admin")
@app.route("/admin/dashboard")
@app.route("/api/index.py/admin")
@app.route("/api/index/admin")
@app.route("/api/index.py/admin/dashboard")
@app.route("/api/index/admin/dashboard")
@admin_required
def admin_dashboard_page():
    settings = database.get_settings()
    rooms = database.get_all_rooms(include_all_statuses=True)
    metrics = database.get_dashboard_metrics()
    return render_template(
        "admin_dashboard.html",
        settings=settings,
        rooms=rooms,
        metrics=metrics,
        admin_user=session.get("admin_user", "admin")
    )


# --- Public API Endpoints ---

@app.route("/api/health")
def api_health():
    return jsonify({
        "service": "Yashaswi Residency Home Stay Full-Stack API",
        "status": "healthy",
        "environment": "vercel" if IS_VERCEL else "local"
    })


@app.route("/api/rooms")
def api_get_rooms():
    include_all = request.args.get("all", "0") == "1"
    rooms = database.get_all_rooms(include_all_statuses=include_all)
    return jsonify({"success": True, "rooms": rooms})


@app.route("/api/rooms/<int:room_id>")
def api_get_room(room_id):
    room = database.get_room_by_id(room_id)
    if not room:
        return jsonify({"error": "Room not found."}), 404
    return jsonify({"success": True, "room": room})


@app.route("/api/availability")
def api_check_availability():
    room_id = request.args.get("room_id", type=int)
    check_in = request.args.get("check_in", "").strip()
    check_out = request.args.get("check_out", "").strip()

    if not room_id or not check_in or not check_out:
        return jsonify({"error": "room_id, check_in, and check_out parameters are required."}), 400

    available, msg = database.check_room_availability(room_id, check_in, check_out)
    return jsonify({
        "success": True,
        "available": available,
        "message": msg
    })


@app.route("/api/bookings", methods=["POST"])
def api_create_booking():
    data = request.get_json() or {}
    guest_name = data.get("guest_name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    room_id = data.get("room_id")
    check_in = data.get("check_in", "").strip()
    check_out = data.get("check_out", "").strip()
    special_requests = data.get("special_requests", "").strip()

    try:
        guests = int(data.get("guests", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid guests count."}), 400

    # Validation
    if not guest_name:
        return jsonify({"error": "Please provide your Full Name."}), 400
    if not phone:
        return jsonify({"error": "Please provide your Mobile Phone Number."}), 400
    if not email:
        return jsonify({"error": "Please provide your Email Address."}), 400
    if not room_id:
        return jsonify({"error": "Please select a room."}), 400
    if not check_in or not check_out:
        return jsonify({"error": "Check-in and Check-out dates are required."}), 400

    clean_digits = "".join(c for c in phone if c.isdigit())
    if len(clean_digits) < 10:
        return jsonify({"error": "Please enter a valid 10-digit mobile number."}), 400

    booking, err = database.create_booking(
        guest_name=guest_name,
        phone=phone,
        email=email,
        room_id=int(room_id),
        check_in_str=check_in,
        check_out_str=check_out,
        guests=guests,
        special_requests=special_requests
    )

    if err:
        return jsonify({"error": err}), 400

    settings = database.get_settings()
    return jsonify({
        "success": True,
        "booking": booking,
        "homestay_phone": settings.get("phone", "087921 28459"),
        "whatsapp": settings.get("whatsapp", "+918792128459"),
        "upi_id": settings.get("upi_id", "8792128459@upi"),
        "upi_enabled": settings.get("upi_enabled", "1") == "1",
        "message": "Booking request received successfully! We look forward to hosting you in Manipal."
    }), 201


@app.route("/api/bookings/<booking_id>")
def api_get_booking(booking_id):
    booking = database.get_booking_by_id(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found."}), 404
    return jsonify({"success": True, "booking": booking})


@app.route("/api/reviews", methods=["GET", "POST"])
@app.route("/api/feedback", methods=["GET", "POST"])
def api_reviews():
    if request.method == "GET":
        reviews = database.get_approved_reviews()
        return jsonify({"success": True, "reviews": reviews})

    # POST new review
    data = request.get_json() or {}
    guest_name = data.get("guest_name", "").strip()
    comment = data.get("comment", "").strip()
    stay_date = data.get("stay_date", "").strip() or "Verified Guest"
    try:
        rating = int(data.get("rating", 5))
    except (ValueError, TypeError):
        rating = 5

    if not guest_name or not comment:
        return jsonify({"error": "Please provide your name and your feedback comments."}), 400

    rev_id = database.add_review(guest_name, rating, comment, stay_date, status="APPROVED")
    return jsonify({
        "success": True,
        "review_id": rev_id,
        "message": "Thank you for sharing your feedback with Yashaswi Residency!"
    }), 201


@app.route("/api/admin/reviews")
@admin_required
def api_admin_reviews():
    reviews = database.get_all_reviews()
    return jsonify({"success": True, "reviews": reviews})


@app.route("/api/admin/reviews/<int:review_id>/status", methods=["PATCH"])
@admin_required
def api_admin_review_status(review_id):
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "Status is required."}), 400
    ok, err = database.update_review_status(review_id, status)
    if not ok:
        return jsonify({"error": err or "Failed to update review status."}), 400
    return jsonify({"success": True, "message": f"Review marked as {status}."})


@app.route("/api/admin/reviews/<int:review_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_review(review_id):
    ok, err = database.delete_review(review_id)
    if not ok:
        return jsonify({"error": err or "Failed to delete review."}), 400
    return jsonify({"success": True, "message": "Review deleted successfully."})


# --- Admin Authentication & Management APIs ---

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if database.verify_admin_login(username, password):
        session["is_admin"] = True
        session["admin_user"] = username
        return jsonify({"success": True, "message": "Admin login successful."})
    return jsonify({"error": "Invalid username or password. Please check your credentials."}), 401


@app.route("/api/admin/logout", methods=["POST", "GET"])
def api_admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_user", None)
    if request.is_json or request.method == "POST":
        return jsonify({"success": True, "message": "Logged out successfully."})
    return redirect(url_for("admin_login_page"))


@app.route("/api/admin/metrics")
@admin_required
def api_admin_metrics():
    metrics = database.get_dashboard_metrics()
    return jsonify({"success": True, "metrics": metrics})


@app.route("/api/admin/bookings")
@admin_required
def api_admin_bookings():
    search = request.args.get("search")
    status = request.args.get("status")
    room_id = request.args.get("room_id")
    bookings = database.get_all_bookings(search=search, status=status, room_id=room_id)
    return jsonify({"success": True, "bookings": bookings})


@app.route("/api/admin/bookings/<booking_id>/status", methods=["PATCH"])
@admin_required
def api_admin_update_booking_status(booking_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    payment_status = data.get("payment_status")

    if not new_status:
        return jsonify({"error": "Status is required."}), 400

    ok, err = database.update_booking_status(booking_id, new_status, payment_status)
    if not ok:
        return jsonify({"error": err or "Failed to update booking status."}), 400
    return jsonify({"success": True, "message": f"Booking marked as {new_status}."})


@app.route("/api/admin/rooms", methods=["GET", "POST"])
@admin_required
def api_admin_rooms():
    if request.method == "GET":
        rooms = database.get_all_rooms(include_all_statuses=True)
        return jsonify({"success": True, "rooms": rooms})

    # POST - Add New Room
    data = request.get_json() or {}
    room_number = data.get("room_number", "").strip()
    name = data.get("name", "").strip()
    category = data.get("category", "Comfortable").strip()
    description = data.get("description", "").strip()
    price = data.get("price_per_night")
    capacity = data.get("capacity", 2)
    bed_type = data.get("bed_type", "King / Queen Bed").strip()
    amenities = data.get("amenities", [])
    photos = data.get("photos", [])
    status = data.get("status", "AVAILABLE")
    highlight = data.get("highlight", "").strip()
    cancellation = data.get("cancellation", "Free cancellation up to 24 hours before check-in").strip()

    if not room_number or not name or price is None:
        return jsonify({"error": "Room identifier, room name, and price are required."}), 400

    room_id, err = database.add_room(
        room_number=room_number,
        name=name,
        category=category,
        description=description,
        price_per_night=price,
        capacity=capacity,
        bed_type=bed_type,
        amenities=amenities,
        photos=photos,
        status=status,
        highlight=highlight,
        cancellation=cancellation
    )
    if err:
        return jsonify({"error": err}), 400

    return jsonify({"success": True, "room_id": room_id, "message": "New room added successfully."}), 201


@app.route("/api/admin/rooms/<int:room_id>", methods=["GET", "PUT", "DELETE"])
@admin_required
def api_admin_room_detail(room_id):
    if request.method == "GET":
        room = database.get_room_by_id(room_id)
        if not room:
            return jsonify({"error": "Room not found."}), 404
        return jsonify({"success": True, "room": room})

    if request.method == "DELETE":
        ok, err = database.delete_room(room_id)
        if not ok:
            return jsonify({"error": err or "Failed to delete room."}), 400
        return jsonify({"success": True, "message": "Room deleted successfully."})

    # PUT - Update Room
    data = request.get_json() or {}
    room_number = data.get("room_number", "").strip()
    name = data.get("name", "").strip()
    category = data.get("category", "Comfortable").strip()
    description = data.get("description", "").strip()
    price = data.get("price_per_night")
    capacity = data.get("capacity", 2)
    bed_type = data.get("bed_type", "King / Queen Bed").strip()
    amenities = data.get("amenities", [])
    photos = data.get("photos", [])
    status = data.get("status", "AVAILABLE")
    highlight = data.get("highlight", "").strip()
    cancellation = data.get("cancellation", "Free cancellation up to 24 hours before check-in").strip()

    ok, err = database.update_room(
        room_id=room_id,
        room_number=room_number,
        name=name,
        category=category,
        description=description,
        price_per_night=price,
        capacity=capacity,
        bed_type=bed_type,
        amenities=amenities,
        photos=photos,
        status=status,
        highlight=highlight,
        cancellation=cancellation
    )
    if not ok:
        return jsonify({"error": err or "Failed to update room."}), 400

    return jsonify({"success": True, "message": "Room updated successfully."})


@app.route("/api/admin/rooms/<int:room_id>/status", methods=["PATCH"])
@admin_required
def api_admin_room_status(room_id):
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "Status is required."}), 400

    ok, err = database.update_room_status(room_id, status)
    if not ok:
        return jsonify({"error": err or "Failed to update status."}), 400
    return jsonify({"success": True, "message": f"Room status updated to {status}."})


@app.route("/static/<path:filename>")
def serve_static_direct(filename):
    for folder in [
        os.path.join(base_dir, "public", "static"),
        os.path.join(base_dir, "static")
    ]:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            return send_from_directory(folder, filename)
    return jsonify({"error": f"Asset {filename} not found."}), 404


@app.route("/uploads/<path:filename>")
@app.route("/static/images/uploads/<path:filename>")
def serve_upload(filename):
    upload_folder = app.config.get("UPLOAD_FOLDER")
    if upload_folder and os.path.exists(os.path.join(upload_folder, filename)):
        return send_from_directory(upload_folder, filename)
    static_uploads = os.path.join(app.static_folder, "images", "uploads")
    if os.path.exists(os.path.join(static_uploads, filename)):
        return send_from_directory(static_uploads, filename)
    return jsonify({"error": "Uploaded image not found."}), 404


@app.route("/api/admin/upload-photo", methods=["POST"])
@admin_required
def api_admin_upload_photo():
    if "photo" not in request.files:
        return jsonify({"error": "No image file provided."}), 400
    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{int(datetime.now().timestamp())}_{filename}"
    upload_folder = app.config.get("UPLOAD_FOLDER", "/tmp/uploads")
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except OSError as e:
        return jsonify({"error": f"Cannot create upload directory: {e}"}), 500

    filepath = os.path.join(upload_folder, unique_name)
    file.save(filepath)
    rel_url = f"/static/images/uploads/{unique_name}"
    return jsonify({"success": True, "url": rel_url})


@app.route("/api/admin/settings", methods=["GET", "POST"])
@admin_required
def api_admin_settings():
    if request.method == "GET":
        settings = database.get_settings()
        return jsonify({"success": True, "settings": settings})

    data = request.get_json() or {}
    # Do not allow overwriting password directly without proper hashing
    if "admin_password" in data and data["admin_password"]:
        data["admin_password_hash"] = database.hash_password(data.pop("admin_password"))
    database.update_settings(data)
    return jsonify({"success": True, "message": "Settings updated successfully."})


@app.errorhandler(404)
def handle_404(e):
    path = request.path
    for prefix in ["/api/index.py", "/api/index", "/api/app.py", "/api/app"]:
        if path.startswith(prefix):
            clean_path = path[len(prefix):] or "/"
            return redirect(clean_path)
    # If standard 404 or unknown sub-route, serve the full homepage gracefully
    settings = database.get_settings()
    rooms = database.get_all_rooms(include_all_statuses=True)
    reviews = database.get_approved_reviews()
    return render_template(
        "index.html",
        settings=settings,
        rooms=rooms,
        reviews=reviews,
        today=date.today().isoformat()
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
