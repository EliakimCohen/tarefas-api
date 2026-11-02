import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Task


class APITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="eli", password="test-password-only")
        cls.other = get_user_model().objects.create_user(username="other", password="test-password-only")

    def setUp(self):
        self.client.force_login(self.user)

    def post(self, data):
        return self.client.post("/api/tasks/", data=json.dumps(data), content_type="application/json")

    def test_health_is_public(self):
        self.assertEqual(Client().get("/api/health/").json(), {"status": "ok"})

    def test_anonymous_cannot_read_or_create(self):
        client = Client()
        self.assertEqual(client.get("/api/tasks/").status_code, 401)
        self.assertEqual(client.post("/api/tasks/", data="{}", content_type="application/json").status_code, 401)

    def test_create_and_read(self):
        response = self.post({"title": "  Estudar Python  "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Estudar Python")
        self.assertFalse(response.json()["completed"])
        self.assertEqual(self.client.get(response["Location"]).json(), response.json())
        self.assertEqual(Task.objects.get().owner, self.user)

    def test_patch_and_filter(self):
        task = Task.objects.create(owner=self.user, title="Ler")
        response = self.client.patch(f"/api/tasks/{task.pk}/", data=json.dumps({"completed": True}), content_type="application/json")
        self.assertTrue(response.json()["completed"])
        self.assertEqual(self.client.get("/api/tasks/?completed=false").json()["count"], 0)
        self.assertEqual(self.client.get("/api/tasks/?completed=true").json()["count"], 1)

    def test_delete(self):
        task = Task.objects.create(owner=self.user, title="Ler")
        response = self.client.delete(f"/api/tasks/{task.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Task.objects.exists())

    def test_other_users_task_is_hidden_for_all_methods(self):
        task = Task.objects.create(owner=self.other, title="Privada")
        self.assertEqual(self.client.get("/api/tasks/").json()["count"], 0)
        for method in ("get", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(f"/api/tasks/{task.pk}/").status_code, 404)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_invalid_payloads_do_not_create_tasks(self):
        for data in [{}, {"title": " "}, {"title": "a" * 161}, {"title": None}, {"title": "A", "completed": "false"}, {"title": "A", "owner": self.other.pk}, [], 42]:
            with self.subTest(data=data):
                self.assertEqual(self.post(data).status_code, 400)
        self.assertFalse(Task.objects.exists())

    def test_malformed_json_and_content_type(self):
        for data, content_type in [("{", "application/json"), ("{}", "text/plain"), (b"\xff", "application/json")]:
            with self.subTest(data=data):
                response = self.client.post("/api/tasks/", data=data, content_type=content_type)
                self.assertEqual(response.status_code, 400)

    def test_invalid_patch_preserves_data(self):
        task = Task.objects.create(owner=self.user, title="Original")
        for data in [{}, {"title": "Novo", "completed": 1}]:
            response = self.client.patch(f"/api/tasks/{task.pk}/", data=json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 400)
        task.refresh_from_db()
        self.assertEqual(task.title, "Original")

    def test_pagination(self):
        Task.objects.bulk_create([Task(owner=self.user, title=str(index)) for index in range(21)])
        first = self.client.get("/api/tasks/").json()
        second = self.client.get("/api/tasks/?page=2").json()
        self.assertEqual(first["count"], 21)
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(len(second["results"]), 1)
        self.assertNotEqual(first["results"][0]["id"], second["results"][0]["id"])

    def test_invalid_filters_and_missing_task(self):
        for query in ["page=0", "page=abc", "completed=yes"]:
            self.assertEqual(self.client.get("/api/tasks/?" + query).status_code, 400)
        self.assertEqual(self.client.get("/api/tasks/999/").status_code, 404)

    def test_method_not_allowed(self):
        response = self.client.put("/api/tasks/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET, POST")

    def test_csrf_login_create_logout_end_to_end(self):
        client = Client(enforce_csrf_checks=True)
        login_url = "/api/login/"
        credentials = {"username": "eli", "password": "test-password-only"}
        self.assertEqual(client.post(login_url, credentials, content_type="application/json").status_code, 403)
        token = client.get("/api/csrf/").json()["csrfToken"]
        failed = client.post(login_url, {**credentials, "password": "wrong"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(failed.status_code, 401)
        response = client.post(login_url, credentials, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        token = response.json()["csrfToken"]
        self.assertEqual(client.post("/api/tasks/", {"title": "Teste"}, content_type="application/json").status_code, 403)
        created = client.post("/api/tasks/", {"title": "Teste"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(client.post("/api/logout/", HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(client.get("/api/tasks/").status_code, 401)

    def test_invalid_login_body(self):
        self.assertEqual(Client().post("/api/login/", {"username": []}, content_type="application/json").status_code, 400)
