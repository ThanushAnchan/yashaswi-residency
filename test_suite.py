import os
import json
import unittest

os.environ["VERCEL"] = "1"
import app
import database

class YashaswiResidencyVerificationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        # Clean up test bookings to ensure idempotency
        conn = database.get_db_connection()
        conn.execute("DELETE FROM bookings WHERE guest_name LIKE '%Test Guest%'")
        conn.commit()
        conn.close()

    def test_01_vercel_import_safety(self):
        """Verify Vercel import configuration and upload folder."""
        self.assertEqual(app.app.config["UPLOAD_FOLDER"], "/tmp/uploads")
        self.assertNotIn("static", app.app.config["UPLOAD_FOLDER"])

    def test_02_health_endpoint(self):
        """Verify API health status."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data.get("status"), "healthy")

    def test_03_rooms_and_real_images(self):
        """Verify initial 3 rooms and presence of real provided photos."""
        resp = self.client.get("/api/rooms")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        rooms = data.get("rooms", [])
        self.assertGreaterEqual(len(rooms), 3)

        room_names = [r["name"] for r in rooms]
        self.assertIn("Comfortable Stay", room_names)
        self.assertIn("Premium Stay", room_names)
        self.assertIn("Family Stay", room_names)

        # Verify real image references
        all_photos = []
        for r in rooms:
            all_photos.extend(r.get("photos", []))
        self.assertTrue(any("living_lounge.png" in p for p in all_photos))
        self.assertTrue(any("premium_wood_lounge.png" in p for p in all_photos))
        self.assertTrue(any("family_suite_lounge.png" in p for p in all_photos))

    def test_04_static_images_served(self):
        """Verify that all 5 real provided photographs are served over HTTP."""
        images_to_check = [
            "/static/images/hero_exterior.jpg",
            "/static/images/entrance_reception.png",
            "/static/images/living_lounge.png",
            "/static/images/premium_wood_lounge.png",
            "/static/images/family_suite_lounge.png",
            "/static/images/buddha_zen_sanctum.jpg",
            "/static/images/honeymoon_romantic_suite.jpg",
            "/static/images/lounge_kitchen_open.jpg",
            "/static/images/dining_living_suite.jpg",
            "/static/images/lounge_french_doors.jpg"
        ]
        for img_url in images_to_check:
            resp = self.client.get(img_url)
            self.assertEqual(resp.status_code, 200, f"Image {img_url} returned {resp.status_code}")
            self.assertGreater(len(resp.data), 10000, f"Image {img_url} content is empty")

    def test_05_booking_and_double_booking_prevention(self):
        """Verify booking creation and double-booking conflict rejection."""
        # 1. Create first valid booking
        b1_payload = {
            "guest_name": "Test Guest Alpha",
            "phone": "9876543210",
            "email": "alpha@example.com",
            "room_id": 1,
            "check_in": "2026-11-20",
            "check_out": "2026-11-23",
            "guests": 2,
            "special_requests": "Ground floor preferred"
        }
        res1 = self.client.post("/api/bookings", json=b1_payload)
        self.assertEqual(res1.status_code, 201)
        data1 = json.loads(res1.data)
        self.assertTrue(data1.get("success"))
        b1_id = data1.get("booking", {}).get("booking_id")
        self.assertTrue(b1_id.startswith("YASH-2026-"))

        # 2. Try creating overlapping booking for same room on overlapping dates (2026-11-21 to 2026-11-24)
        b2_payload = {
            "guest_name": "Test Guest Beta",
            "phone": "9876543211",
            "email": "beta@example.com",
            "room_id": 1,
            "check_in": "2026-11-21",
            "check_out": "2026-11-24",
            "guests": 2
        }
        res2 = self.client.post("/api/bookings", json=b2_payload)
        self.assertEqual(res2.status_code, 400, "Double-booking should be rejected with HTTP 400")
        data2 = json.loads(res2.data)
        self.assertIn("error", data2)

        # 3. Create non-overlapping booking for same room on dates (2026-11-25 to 2026-11-27)
        b3_payload = {
            "guest_name": "Test Guest Gamma",
            "phone": "9876543212",
            "email": "gamma@example.com",
            "room_id": 1,
            "check_in": "2026-11-25",
            "check_out": "2026-11-27",
            "guests": 2
        }
        res3 = self.client.post("/api/bookings", json=b3_payload)
        self.assertEqual(res3.status_code, 201, "Non-overlapping booking must succeed")

    def test_06_admin_auth_and_metrics(self):
        """Verify admin login and dashboard metrics."""
        # Bad login
        res_bad = self.client.post("/api/admin/login", json={"username": "admin", "password": "wrongpassword"})
        self.assertEqual(res_bad.status_code, 401)

        # Good login
        res_good = self.client.post("/api/admin/login", json={"username": "admin", "password": "yashaswi2026!"})
        self.assertEqual(res_good.status_code, 200)

        # Fetch metrics
        res_metrics = self.client.get("/api/admin/metrics")
        self.assertEqual(res_metrics.status_code, 200)
        data = json.loads(res_metrics.data)
        self.assertTrue(data.get("success"))
        metrics = data.get("metrics", {})
        self.assertIn("rooms", metrics)
        self.assertIn("bookings", metrics)

    def test_07_admin_room_management(self):
        """Verify admin can add, update, and manage rooms."""
        # Login
        self.client.post("/api/admin/login", json={"username": "admin", "password": "yashaswi2026!"})

        # Add new room
        new_room = {
            "room_number": "YR-999",
            "name": "Garden Cottage Room",
            "category": "Premium",
            "description": "Lovely tranquil garden room with veranda.",
            "price_per_night": 2999.0,
            "capacity": 2,
            "bed_type": "1 King Bed",
            "amenities": ["AC", "Wi-Fi", "Garden View"],
            "photos": ["/static/images/living_lounge.png"]
        }
        res_add = self.client.post("/api/admin/rooms", json=new_room)
        self.assertEqual(res_add.status_code, 201)
        room_id = json.loads(res_add.data).get("room_id")

        # Toggle status
        res_stat = self.client.patch(f"/api/admin/rooms/{room_id}/status", json={"status": "MAINTENANCE"})
        self.assertEqual(res_stat.status_code, 200)

        # Delete room
        res_del = self.client.delete(f"/api/admin/rooms/{room_id}")
        self.assertEqual(res_del.status_code, 200)

    def test_08_property_settings(self):
        """Verify property settings and UPI configuration update."""
        self.client.post("/api/admin/login", json={"username": "admin", "password": "yashaswi2026!"})

        # Update UPI settings
        payload = {
            "phone": "087921 28459",
            "upi_enabled": "1",
            "upi_id": "8792128459@upi",
            "upi_payee_name": "Yashaswi Residency Home Stay"
        }
        res = self.client.post("/api/admin/settings", json=payload)
        self.assertEqual(res.status_code, 200)

        # Verify get settings
        res_get = self.client.get("/api/admin/settings")
        self.assertEqual(res_get.status_code, 200)
        data = json.loads(res_get.data)
        self.assertEqual(data.get("settings", {}).get("upi_id"), "8792128459@upi")

    def test_09_feedback_submission_and_moderation(self):
        """Verify public feedback submission and admin moderation."""
        # 1. Public user submits feedback
        fb_payload = {
            "guest_name": "Test Reviewer",
            "rating": 5,
            "stay_date": "October 2026",
            "comment": "Exceptional stay! Immaculate cleanliness and very peaceful surroundings in Manipal."
        }
        res_fb = self.client.post("/api/feedback", json=fb_payload)
        self.assertEqual(res_fb.status_code, 201)
        data_fb = json.loads(res_fb.data)
        self.assertTrue(data_fb.get("success"))
        rev_id = data_fb.get("review_id")

        # 2. Admin logs in and retrieves reviews
        self.client.post("/api/admin/login", json={"username": "admin", "password": "yashaswi2026!"})
        res_list = self.client.get("/api/admin/reviews")
        self.assertEqual(res_list.status_code, 200)
        reviews = json.loads(res_list.data).get("reviews", [])
        self.assertTrue(any(r["review_id"] == rev_id for r in reviews))

        # 3. Admin hides review
        res_hide = self.client.patch(f"/api/admin/reviews/{rev_id}/status", json={"status": "HIDDEN"})
        self.assertEqual(res_hide.status_code, 200)

        # 4. Admin deletes test review to maintain test idempotency
        res_del = self.client.delete(f"/api/admin/reviews/{rev_id}")
        self.assertEqual(res_del.status_code, 200)

if __name__ == "__main__":
    unittest.main()
