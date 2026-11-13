"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_read_account(self):
        """It should read an existing account and follow its Location."""
        account = self._create_accounts(1)[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["email"], account.email)

    def test_create_location_resolves(self):
        """A created account should have a resolvable resource Location."""
        response = self.client.post(BASE_URL, json=AccountFactory().serialize())
        found = self.client.get(response.headers["Location"])
        self.assertEqual(found.get_json(), response.get_json())

    def test_read_missing_account(self):
        """It should report a missing account as not found."""
        response = self.client.get(f"{BASE_URL}/999999")
        self.assertEqual(response.status_code, 404)

    def test_list_accounts(self):
        """It should list all persisted accounts."""
        accounts = self._create_accounts(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({a["id"] for a in response.get_json()},
                         {a.id for a in accounts})

    def test_list_empty_accounts(self):
        """An empty collection should return an empty JSON array."""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_update_account(self):
        """It should update data while keeping the resource ID."""
        account = self._create_accounts(1)[0]
        data = account.serialize()
        data["name"] = "Updated Customer"
        data["id"] = 999999
        response = self.client.put(f"{BASE_URL}/{account.id}", json=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["id"], account.id)
        self.assertEqual(response.get_json()["name"], "Updated Customer")
        found = self.client.get(f"{BASE_URL}/{account.id}").get_json()
        self.assertEqual(found["name"], "Updated Customer")

    def test_update_missing_account(self):
        """It should reject updates to missing accounts."""
        response = self.client.put(f"{BASE_URL}/999999",
                                   json=AccountFactory().serialize())
        self.assertEqual(response.status_code, 404)

    def test_update_bad_data(self):
        """It should reject incomplete update data."""
        account = self._create_accounts(1)[0]
        response = self.client.put(f"{BASE_URL}/{account.id}", json={})
        self.assertEqual(response.status_code, 400)

    def test_update_bad_media_type(self):
        """It should reject non-JSON updates."""
        account = self._create_accounts(1)[0]
        response = self.client.put(f"{BASE_URL}/{account.id}",
                                   data="not-json", content_type="text/plain")
        self.assertEqual(response.status_code, 415)

    def test_delete_account(self):
        """Deletion should remove the account and be idempotent."""
        account = self._create_accounts(1)[0]
        url = f"{BASE_URL}/{account.id}"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_delete_missing_account(self):
        """Deleting a missing account should return no content."""
        self.assertEqual(self.client.delete(f"{BASE_URL}/999999").status_code,
                         204)

    def test_invalid_json(self):
        """Malformed JSON should produce a client error."""
        response = self.client.post(BASE_URL, data="{",
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_unsupported_method(self):
        """Unsupported methods should return a structured client error."""
        response = self.client.patch(BASE_URL, json={})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["status"], 405)

    def test_security_headers(self):
        """It should provide browser security headers."""
        response = self.client.get("/")
        self.assertEqual(response.headers.get("X-Content-Type-Options"),
                         "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertIn("default-src", response.headers["Content-Security-Policy"])

    def test_cors_headers(self):
        """Allowed browser origins should receive CORS headers."""
        origin = "https://example.com"
        response = self.client.get("/", headers={"Origin": origin})
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"),
                         origin)
