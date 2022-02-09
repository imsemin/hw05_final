import shutil
import tempfile
from time import sleep

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
CACHE_TEST_TIME = 3
settings.CACHE_TIME_INDEX = CACHE_TEST_TIME


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded = SimpleUploadedFile(
            name="small.gif", content=small_gif, content_type="image/gif"
        )
        cls.user = User.objects.create_user(username="Testname")
        cls.group = Group.objects.create(
            title="Test title",
            slug="test-slug",
            description="Test description",
        )
        cls.post = Post.objects.create(
            text="Test text",
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsViewTests.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse("posts:post_create"): "posts/create_post.html",
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:group_list", kwargs={"slug": PostsViewTests.group.slug}
            ): "posts/group_list.html",
            reverse(
                "posts:profile", kwargs={"username": PostsViewTests.user}
            ): "posts/profile.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": PostsViewTests.post.id}
            ): "posts/post_detail.html",
            reverse(
                "posts:post_edit",
                kwargs={
                    "post_id": PostsViewTests.post.id,
                },
            ): "posts/create_post.html",
        }
        for reverse_name, urls in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, urls)

    def test_homepage_show_correct_context(self):
        """Шаблон home сформирован с правильным контекстом."""
        new_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04"
            b"\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
            b"\x02\x4c\x01\x00\x3b"
        )
        uploaded = SimpleUploadedFile(
            name="new.gif", content=new_gif, content_type="image/gif"
        )
        new_author = User.objects.create_user(username="Testname2")
        new_group = Group.objects.create(
            title="Test title 2",
            slug="test-slug-2",
        )
        new_post = Post.objects.create(
            text="Test text 2",
            author=new_author,
            group=new_group,
            image=uploaded,
        )
        response = self.authorized_client.get(reverse("posts:index"))
        post1 = response.context["page_obj"][1]
        post2 = response.context["page_obj"][0]
        page_context = {
            (post1.group, PostsViewTests.post.group),
            (post1.text, PostsViewTests.post.text),
            (post1.author, PostsViewTests.post.author),
            (post1.image, PostsViewTests.post.image),
            (post2.group, new_post.group),
            (post2.text, new_post.text),
            (post2.author, new_post.author),
            (post2.image, new_post.image),
            (len(response.context["page_obj"]), Post.objects.count()),
        }
        for context, expected_value in page_context:
            with self.subTest(context=context):
                self.assertEqual(context, expected_value)

    def test_cache_homepage(self):
        """Проверка работоспособности кэша на главной странице.
        Переопределены настройки частоты кэширования."""
        new_user = User.objects.create_user(username="Test_name")
        new_group = Group.objects.create(
            title="Test cache title",
            slug="test-cache-slug",
            description="Test description",
        )
        new_post = Post.objects.create(
            text="Test text cache",
            author=new_user,
            group=new_group,
        )
        response_before = self.client.get(reverse("posts:index"))
        new_post.delete()
        self.assertNotEqual(
            len(response_before.context["page_obj"]),
            Post.objects.count(),
        )
        page_context = {
            (
                new_post.text,
                response_before.context["page_obj"][0].text,
            ),
            (
                PostsViewTests.post.text,
                response_before.context["page_obj"][1].text,
            ),
            (
                new_post.group,
                response_before.context["page_obj"][0].group,
            ),
            (
                PostsViewTests.post.group,
                response_before.context["page_obj"][1].group,
            ),
            (
                new_post.author,
                response_before.context["page_obj"][0].author,
            ),
            (
                PostsViewTests.post.author,
                response_before.context["page_obj"][1].author,
            ),
        }
        for context, expected_value in page_context:
            with self.subTest(context=context):
                self.assertEqual(context, expected_value)
        sleep(CACHE_TEST_TIME)  # cache.clear() альтернативный способ
        response_after = self.client.get(reverse("posts:index"))
        self.assertEqual(
            len(response_after.context["page_obj"]), Post.objects.count()
        )
        self.assertFalse(
            Post.objects.filter(
                text=new_post.text,
                group=new_post.group,
                author=new_post.author,
            ).exists()
        )

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                "posts:group_list", kwargs={"slug": PostsViewTests.group.slug}
            ),
        )
        page_context = {
            (response.context.get("group").title, PostsViewTests.group.title),
            (response.context.get("group").slug, PostsViewTests.group.slug),
            (
                response.context.get("group").description,
                PostsViewTests.group.description,
            ),
            (
                response.context["page_obj"][0],
                PostsViewTests.post,
            ),
            (
                response.context["page_obj"][0].image,
                PostsViewTests.post.image,
            ),
        }
        for context, expected_value in page_context:
            with self.subTest(context=context):
                self.assertEqual(context, expected_value)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:profile", kwargs={"username": PostsViewTests.user}),
        )
        page_context = {
            (response.context.get("author"), PostsViewTests.user),
            (
                response.context["page_obj"][0].group,
                PostsViewTests.post.group,
            ),
            (response.context.get("post_count"), Post.objects.count()),
            (response.context["page_obj"][0], PostsViewTests.post),
            (response.context["page_obj"][0].image, PostsViewTests.post.image),
        }
        for context, expected_value in page_context:
            with self.subTest(context=context):
                self.assertEqual(context, expected_value)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        comment = Comment.objects.create(
            text="test comment",
            author=PostsViewTests.user,
            post=PostsViewTests.post,
        )
        response = self.authorized_client.get(
            reverse(
                "posts:post_detail", kwargs={"post_id": PostsViewTests.post.id}
            ),
        )
        page_context = {
            (response.context.get("post"), PostsViewTests.post),
            (
                response.context.get("post").group,
                PostsViewTests.post.group,
            ),
            (
                response.context.get("post_count"),
                Post.objects.count(),
            ),
            (response.context["post"].image, PostsViewTests.post.image),
            (response.context.get("post_comments")[0], comment),
        }
        for context, expected_value in page_context:
            with self.subTest(context=context):
                self.assertEqual(context, expected_value)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                "posts:post_edit", kwargs={"post_id": PostsViewTests.post.id}
            ),
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields.get(value)
                self.assertIsInstance(form_field, expected)


class PaginatorViewTests(TestCase):
    POST_CREATED_QUANTITY = settings.POST_QUANTITY + 3
    POSTS_ON_PAGE_1 = settings.POST_QUANTITY
    POSTS_ON_PAGE_2 = POST_CREATED_QUANTITY - POSTS_ON_PAGE_1
    if POSTS_ON_PAGE_2 >= settings.POST_QUANTITY:
        POSTS_ON_PAGE_2 = settings.POST_QUANTITY

    def setUp(self):
        self.user = User.objects.create_user(username="Testname1")
        self.group = Group.objects.create(
            title="test group1", slug="test-slug-2"
        )
        post = [
            Post(
                text="Test text",
                author=self.user,
                group=self.group,
            )
        ] * self.POST_CREATED_QUANTITY
        Post.objects.bulk_create(post)
        cache.clear()

    def test_paginator(self):
        """Проверка работоспособности паджинатора на 1 и 2 странице
        home, group_list, profile."""
        response_profile_page_1 = self.client.get(
            reverse("posts:profile", kwargs={"username": self.user})
        )
        response_profile_page_2 = self.client.get(
            reverse("posts:profile", kwargs={"username": self.user})
            + "?page=2"
        )
        response_group_list_page_1 = self.client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        response_group_list_page_2 = self.client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
            + "?page=2"
        )
        response_index_page_1 = self.client.get(reverse("posts:index"))
        response_index_page_2 = self.client.get(
            reverse("posts:index") + "?page=2"
        )
        page_context = {
            (
                len(response_profile_page_1.context["page_obj"]),
                self.POSTS_ON_PAGE_1,
            ),
            (
                len(response_profile_page_2.context["page_obj"]),
                self.POSTS_ON_PAGE_2,
            ),
            (
                len(response_group_list_page_1.context["page_obj"]),
                self.POSTS_ON_PAGE_1,
            ),
            (
                len(response_group_list_page_2.context["page_obj"]),
                self.POSTS_ON_PAGE_2,
            ),
            (
                len(response_index_page_1.context["page_obj"]),
                self.POSTS_ON_PAGE_1,
            ),
            (
                len(response_index_page_2.context["page_obj"]),
                self.POSTS_ON_PAGE_2,
            ),
        }
        for posts_on_page, expected_value in page_context:
            with self.subTest(posts_on_page=posts_on_page):
                self.assertEqual(posts_on_page, expected_value)


class FollowViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="Testname")
        cls.group = Group.objects.create(
            title="Test title",
            slug="test-slug",
            description="Test description",
        )
        cls.post = Post.objects.create(
            text="Test text",
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(FollowViewTest.user)
        cache.clear()

    def test_following_system(self):
        """Проверка работоспособности системы подписки."""
        new_user = User.objects.create_user(username="Test_name")
        response_not_authorized = Client(new_user).get(
            reverse(
                "posts:profile_follow",
                kwargs={"username": FollowViewTest.user},
            )
        )
        response_auth = self.authorized_client.get(
            reverse("posts:profile_follow", kwargs={"username": new_user})
        )
        response_user_to_user = self.authorized_client.get(
            reverse(
                "posts:profile_follow",
                kwargs={"username": FollowViewTest.user},
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                author=FollowViewTest.user, user=new_user
            ).exists()
        )
        self.assertTrue(
            Follow.objects.filter(
                author=new_user, user=FollowViewTest.user
            ).exists()
        )
        self.assertFalse(
            Follow.objects.filter(
                author=FollowViewTest.user, user=FollowViewTest.user
            ).exists()
        )

    def test_unfollowing_system(self):
        """Проверка работоспособности системы отписки."""
        new_user = User.objects.create_user(username="Test_name")
        Follow.objects.create(author=new_user, user=FollowViewTest.user)
        response = self.authorized_client.get(
            reverse(
                "posts:profile_unfollow",
                kwargs={"username": new_user},
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                author=new_user, user=FollowViewTest.user
            ).exists()
        )

    def test_follow_index(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        new_user = User.objects.create_user(username="Test_name")
        new_group = Group.objects.create(
            title="Test cache title",
            slug="test-cache-slug",
            description="Test description",
        )
        new_post = Post.objects.create(
            text="Test text follow",
            author=new_user,
            group=new_group,
        )
        response_follow = self.authorized_client.get(
            reverse("posts:profile_follow", kwargs={"username": new_user})
        )
        response_page = self.authorized_client.get(
            reverse("posts:follow_index")
        )
        post = response_page.context["page_obj"][0]
        page_context = {
            (post.group, new_post.group),
            (post.text, new_post.text),
            (post.author, new_post.author),
        }
        for context, expected_value in page_context:
            with self.subTest(context=context):
                self.assertEqual(context, expected_value)
        self.assertNotEqual(
            len(response_page.context["page_obj"]), Post.objects.count
        )
