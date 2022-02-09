from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.deletion import SET_NULL

from core.models import CreateModel

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(CreateModel):
    text = models.TextField(
        verbose_name="Текст поста", help_text="Введите текст поста"
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=SET_NULL,
        related_name="posts",
        verbose_name="Группа",
        help_text="Выберите группу",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        related_name="posts",
        verbose_name="Автор",
    )
    image = models.ImageField("Картинка", upload_to="posts/", blank=True)

    def __str__(self):
        return self.text[:15]


class Comment(CreateModel):
    post = models.ForeignKey(
        Post, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Автор",
    )
    text = models.TextField(
        verbose_name="Текст комментария",
        help_text="Текст нового комментария",
        blank=True,
    )

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(
        User, related_name="follower", on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User, related_name="following", on_delete=models.CASCADE
    )
