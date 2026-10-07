# 🏡 Yashaswi Residency Home Stay — Full-Stack Booking Platform

> **Manipal, Karnataka**  
> *"Comfort • Peace • Privacy • Homely Hospitality"*

A modern, luxury full-stack accommodation and booking platform designed specifically for **Yashaswi Residency Home Stay** in Manipal, Karnataka. Built with authentic property photographs, interactive 3D UI elements, date-conflict booking validation, and an owner management portal.

---

## 🌟 Key Features

### 1. Luxury Guest Experience
- **Interactive 3D Ambient Visuals:** Real-time Three.js particle constellation canvas and perspective 3D card tilt effects.
- **10 Authentic Real Photographs:** No stock photos or AI-generated placeholders. Uses verified exterior building facade, reception entrance porch, living TV lounge, designer wood-paneled room, family suite lounge, Buddha Zen sanctum, Honeymoon celebration suite, open living & kitchenette, dining suite, and private lounge with French doors.
- **Interactive Masonry Gallery:** Category filters (`All Photos`, `Exterior & Porch`, `Living & Suites`, `Honeymoon & Zen Court`) with full-screen lightbox modal.
- **Interactive Location & Directions:** Google Maps integration with 1-click **Get Directions** and **Call Now (087921 28459)**.
- **5.0 ★★★★★ Verified Reviews & Guest Feedback Engine:** Interactive modal for verified guest reviews with immediate owner approval and live display.

### 2. Functional Booking Engine (No Placeholders)
- **Live Availability Engine:** Prevents double-booking across overlapping check-in/check-out dates.
- **Sequential Booking ID Generation:** Formats distinct reservation codes (e.g., `YASH-2026-0001`).
- **Instant WhatsApp Link Generator:** Pre-fills reservation details for guests to confirm with the owner via WhatsApp.
- **Configurable UPI Payment Advance:** Displays official UPI ID (`8792128459@upi`) with instructions for GPay/PhonePe/Paytm.

### 3. Owner & Manager Admin Portal (`/admin`)
- **Secure Authentication:** Password hashing and protected admin sessions (`admin` / `yashaswi2026!`).
- **Live Business Metrics:** Total Bookings, Pending Approvals, Confirmed Reservations, Today's Check-ins, Today's Check-outs, Available Rooms, and Total Revenue.
- **Reservation Management:** Filter and search bookings, confirm, complete, or cancel reservations, and message guests on WhatsApp in 1 click.
- **Room Management:** Add new rooms, change room prices, edit room descriptions/amenities, toggle availability (`AVAILABLE` / `OCCUPIED` / `MAINTENANCE`), and update photos.
- **Property Settings:** Configure phone numbers, WhatsApp, address, check-in/out policies, and UPI settings.

---

## 🚀 Running Locally

1. **Quick 1-Click Launch (Recommended for Windows):**
   - Double-click **`start_public_website.bat`**.
   - Starts the local Flask server and creates a secure live HTTPS public link for instant WhatsApp sharing.

2. **Standard Terminal Launch:**
   ```bash
   py run_server.py
   ```
   - Public Website: `http://127.0.0.1:5000`
   - Owner Admin Portal: `http://127.0.0.1:5000/admin/login`

---

## 🔑 Default Owner Credentials
- **Username:** `admin`
- **Password:** `yashaswi2026!`

---

## 🌐 Deploying to Vercel

This repository is built for **100% Vercel compatibility**:
1. Contains `vercel.json` configured with modern rewrites to `/api/index.py`.
2. Zero filesystem write attempts at import time (safe `/tmp` upload handling).
3. Dual database engine support: SQLite for local preview, PostgreSQL for persistent production storage via `DATABASE_URL`.

**Steps to deploy:**
1. Push this folder to your GitHub repository.
2. In [Vercel](https://vercel.com), click **Add New Project** -> **Import Git Repository**.
3. Click **Deploy**. Your site will be live at `https://your-project.vercel.app` with the admin portal at `https://your-project.vercel.app/admin`.
