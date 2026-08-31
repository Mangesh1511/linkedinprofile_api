"""
Unit and endpoint integration tests for Reverse-Engineered LinkedIn Profile REST API.
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api_server import app
from linkedinprofile_api.models import Person, Experience


class TestAPIServer(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        """Test healthcheck endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data.get("status"), "healthy")
        self.assertIn("Reverse-Engineered", json_data.get("engine", ""))

    @patch("linkedinprofile_api.scrapers.reverse_person.ReverseEngineeredScraper.scrape")
    def test_get_profile_info(self, mock_scrape):
        """Test direct reverse-engineered profile endpoint."""
        mock_scrape.return_value = Person(
            linkedin_url="https://www.linkedin.com/in/test/",
            name="Reverse Engine User",
            headline="Software Engineer",
            experiences=[
                Experience(
                    position_title="Software Engineer",
                    institution_name="Tech Corp",
                )
            ]
        )
        response = self.client.get("/api/profileinfo?profileUrl=https://www.linkedin.com/in/test/")
        self.assertEqual(response.status_code, 200)
        data = response.json().get("data", {})
        self.assertEqual(data.get("name"), "Reverse Engine User")
        self.assertEqual(len(data.get("experiences", [])), 1)

    @patch("linkedinprofile_api.scrapers.reverse_person.ReverseEngineeredScraper.scrape")
    def test_get_profile_info_not_found(self, mock_scrape):
        """Test profile not found returns 404 HTTP status code."""
        from linkedinprofile_api.core.exceptions import ProfileNotFoundError
        mock_scrape.side_effect = ProfileNotFoundError("LinkedIn profile 'nonexistent' does not exist (HTTP 404).")
        response = self.client.get("/api/profileinfo?profileUrl=https://www.linkedin.com/in/nonexistent/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("does not exist", response.json().get("detail", ""))

    @patch("linkedinprofile_api.scrapers.reverse_person.ReverseEngineeredScraper.scrape")
    def test_get_profile_info_auth_error(self, mock_scrape):
        """Test authentication failure returns 401 HTTP status code."""
        from linkedinprofile_api.core.exceptions import AuthenticationError
        mock_scrape.side_effect = AuthenticationError("LinkedIn session expired.")
        response = self.client.get("/api/profileinfo?profileUrl=https://www.linkedin.com/in/test/")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
