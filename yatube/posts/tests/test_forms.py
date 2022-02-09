import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsCreateFormTests(TestCase):
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsCreateFormTests.user)
        self.post_count = Post.objects.count()

    def test_post_create(self):
        """Валидная форма создает запись в Post."""
        form_data = {
            "text": "New test text",
            "group": PostsCreateFormTests.group.id,
        }
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                "posts:profile", kwargs={"username": PostsCreateFormTests.user}
            ),
        )
        self.assertEqual(Post.objects.count(), self.post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data["text"],
                group=form_data["group"],
                id=Post.objects.latest("pub_date", "id").id,
            ).exists()
        )

    def test_post_edit(self):
        """Валидная форма редактирует запись в Post."""
        new_group = Group.objects.create(
            title="Test title 2",
            slug="test-slug-2",
            description="Test description 2",
        )
        form_data = {
            "text": "Changed test text",
            "group": new_group.id,
        }
        response = self.authorized_client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), self.post_count)
        self.assertRedirects(
            response,
            reverse(
                "posts:post_detail",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
        )
        self.assertTrue(
            Post.objects.filter(
                text=form_data["text"],
                group=form_data["group"],
                id=PostsCreateFormTests.post.id,
            ).exists()
        )

    def test_post_create_not_authorized(self):
        """Проверка создания записи неавторизованным пользователем."""
        form_data = {
            "text": "Not authorized test text",
            "group": PostsCreateFormTests.group.id,
        }
        response = self.client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse("users:login") + "?next=%2Fcreate%2F",
        )
        self.assertEqual(Post.objects.count(), self.post_count)

    def test_post_edit_not_authorized(self):
        """Проверка редактирования записи неавторизованным пользователем."""
        form_data = {
            "text": "Changed not authorized test text",
            "group": PostsCreateFormTests.group.id,
        }
        response = self.client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse("users:login") + "?next=/posts/1/edit/",
        )
        self.assertEqual(Post.objects.count(), self.post_count)
        self.assertFalse(
            Post.objects.filter(
                text=form_data["text"],
                group=form_data["group"],
                id=PostsCreateFormTests.post.id,
            ).exists()
        )

    def test_post_edit_not_author(self):
        """Проверка редактирования записи не автором."""
        user_2 = User.objects.create_user(username="Testname2")
        client = Client()
        client.force_login(user_2)
        form_data = {
            "text": "Changed not author test text",
            "group": PostsCreateFormTests.group.id,
        }
        response = client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                "posts:post_detail",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
        )
        self.assertFalse(
            Post.objects.filter(
                text=form_data["text"],
                group=form_data["group"],
                id=PostsCreateFormTests.post.id,
                author=user_2,
            ).exists()
        )

    def test_post_create_with_image(self):
        """Валидная форма создает запись с картиной."""
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
        form_data = {
            "text": "New test text",
            "group": PostsCreateFormTests.group.id,
            "image": uploaded,
        }
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                "posts:profile", kwargs={"username": PostsCreateFormTests.user}
            ),
        )
        self.assertEqual(Post.objects.count(), self.post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data["text"],
                group=form_data["group"],
                image=Post.objects.latest("pub_date").image.name,
            ).exists()
        )

    def test_post_add_comment(self):
        """Валидная форма добавляем комментарий в Post."""
        user_3 = User.objects.create(username="Testname2")
        client = Client()
        client.force_login(user_3)
        comment = Comment.objects.create(
            text="new comment",
            author=user_3,
            post=PostsCreateFormTests.post,
        )
        comment_count = Comment.objects.count()
        form_data = {
            "text": comment.text,
        }
        response = client.post(
            reverse(
                "posts:add_comment",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(Comment.objects.latest("pub_date").text, comment.text)
        self.assertRedirects(
            response,
            reverse(
                "posts:post_detail",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
        )
        self.assertTrue(
            Comment.objects.filter(
                text=form_data["text"],
                post=PostsCreateFormTests.post.id,
            ).exists()
        )

    def test_post_add_comment_not_authorized(self):
        """Проверка добавления комментария неавторизованным пользователем."""
        comment_count = Comment.objects.count()
        form_data = {
            "text": "test text not authorized user",
        }
        response = self.client.post(
            reverse(
                "posts:add_comment",
                kwargs={"post_id": PostsCreateFormTests.post.id},
            ),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comment_count)
        self.assertRedirects(
            response,
            reverse("users:login") + "?next=/posts/1/comment/",
        ),
        self.assertFalse(
            Comment.objects.filter(
                text=form_data["text"],
                post=PostsCreateFormTests.post.id,
            ).exists()
        )
