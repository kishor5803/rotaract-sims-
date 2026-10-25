import unittest
from app import app, db

class RotaractWebsiteTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"ASTHRA" in response.data or b"Rotaract" in response.data)

    def test_about_page(self):
        response = self.client.get("/about")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"Soundarya" in response.data)

    def test_faculty_page(self):
        response = self.client.get("/faculty")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"Santhosh R S" in response.data)
        self.assertTrue(b"Sandhya R L" in response.data)

    def test_board_page(self):
        response = self.client.get("/board")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"Board of Directors" in response.data)

    def test_projects_page(self):
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, 200)

    def test_events_page(self):
        response = self.client.get("/events")
        self.assertEqual(response.status_code, 200)

    def test_gallery_page(self):
        response = self.client.get("/gallery")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"Google Drive" in response.data)

    def test_achievements_page(self):
        response = self.client.get("/achievements")
        self.assertEqual(response.status_code, 200)

    def test_letterhead_page(self):
        response = self.client.get("/letterhead")
        self.assertEqual(response.status_code, 200)

    def test_join_page(self):
        response = self.client.get("/join")
        self.assertEqual(response.status_code, 200)

    def test_collaborate_page(self):
        response = self.client.get("/collaborate")
        self.assertEqual(response.status_code, 200)

    def test_certificate_page(self):
        response = self.client.get("/certificate")
        self.assertEqual(response.status_code, 200)

    def test_admin_login_page(self):
        response = self.client.get("/admin/login")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
