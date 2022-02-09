from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="Testname")
        cls.group = Group.objects.create(
            title="Test title",
            slug="test-slug",
        )
        cls.post = Post.objects.create(text="Test text", author=cls.user)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_unexisting_page(self):
        """Проверяем несуществующую страницу."""
        response = self.client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unexisting_page_template(self):
        """Проверка шаблона 404 NOT FOUND несуществующей страницы."""
        response = self.client.get("handler404")
        self.assertTemplateUsed(response, "core/404.html")

    def test_urls_exist(self):
        """Проверяем существования страниц приложения posts."""
        urls_name = {
            (self.client.get("/").status_code, HTTPStatus.OK),
            (self.client.get("/create/").status_code, HTTPStatus.FOUND),
            (
                self.client.get(
                    "/group/" + str(PostsURLTests.group.slug) + "/"
                ).status_code,
                HTTPStatus.OK,
            ),
            (
                self.client.get(
                    "/profile/" + str(self.user) + "/"
                ).status_code,
                HTTPStatus.OK,
            ),
            (
                self.client.get(
                    "/posts/" + str(PostsURLTests.post.id) + "/"
                ).status_code,
                HTTPStatus.OK,
            ),
            (
                self.client.get(
                    "/posts/" + str(PostsURLTests.post.id) + "/edit/"
                ).status_code,
                HTTPStatus.FOUND,
            ),
        }
        for urls, status in urls_name:
            with self.subTest(status=status):
                self.assertEqual(urls, status)

    def test_urls_correct_templates(self):
        """Проверяем URL-адрес использует соответствующий шаблон."""
        templates_url = {
            "/create/": "posts/create_post.html",
            "/posts/"
            + str(PostsURLTests.post.id)
            + "/edit/": "posts/create_post.html",
            "/group/"
            + str(PostsURLTests.group.slug)
            + "/": "posts/group_list.html",
            "/": "posts/index.html",
            "/posts/"
            + str(PostsURLTests.post.id)
            + "/": "posts/post_detail.html",
            "/profile/" + str(self.user) + "/": "posts/profile.html",
        }
        for templates, urls in templates_url.items():
            with self.subTest(templates=templates):
                response = self.authorized_client.get(templates)
                self.assertTemplateUsed(response, urls)
