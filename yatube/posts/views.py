from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post
from .utils import paginator_func


@cache_page(settings.CACHE_TIME_INDEX, key_prefix="index_page")
def index(request):
    template_name = "posts/index.html"
    post_list = Post.objects.all()
    context = {
        "page_obj": paginator_func(post_list, request),
    }
    return render(request, template_name, context)


def group_posts(request, slug):
    template_name = "posts/group_list.html"
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    context = {
        "group": group,
        "page_obj": paginator_func(post_list, request),
    }
    return render(request, template_name, context)


def profile(request, username):
    template_name = "posts/profile.html"
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    post_count = post_list.count()
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(author=author, user=request.user).exists()
    )
    context = {
        "author": author,
        "post_count": post_count,
        "page_obj": paginator_func(post_list, request),
        "following": following,
    }
    return render(request, template_name, context)


def post_detail(request, post_id):
    template_name = "posts/post_detail.html"
    post = get_object_or_404(Post, id=post_id)
    post_count = Post.objects.filter(author=post.author).count()
    post_comments = Comment.objects.filter(post_id=post)
    form = CommentForm(request.POST or None)
    context = {
        "post": post,
        "post_count": post_count,
        "post_comments": post_comments,
        "form": form,
    }
    return render(request, template_name, context)


@login_required
def post_create(request):
    template_name = "posts/create_post.html"
    form = PostForm(request.POST or None)
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect("posts:profile", username=new_post.author)
    return render(request, template_name, {"form": form})


@login_required
def post_edit(request, post_id):
    post_current = get_object_or_404(Post, id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post_current,
    )
    if post_current.author != request.user:
        return redirect("posts:post_detail", post_id=post_id)
    if form.is_valid():
        form.save()
        return redirect("posts:post_detail", post_id=post_id)
    return render(
        request, "posts/create_post.html", {"form": form, "is_edit": True}
    )


@login_required
def add_comment(request, post_id):
    commented_post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = commented_post
        comment.save()
    return redirect("posts:post_detail", post_id=post_id)


@login_required
def follow_index(request):
    template_name = "posts/follow.html"
    following = Follow.objects.filter(user_id=request.user.id).select_related(
        "author"
    )
    posts = []
    for author_id in following:
        posts.append(author_id.author)
    posts_list = Post.objects.all().filter(author__in=posts)
    counter = posts_list.count()
    context = {
        "page_obj": paginator_func(posts_list, request),
        "counter": counter,
    }
    return render(request, template_name, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        if (
            Follow.objects.filter(author=author, user=request.user).exists()
            == True
        ):
            return redirect("posts:profile", username=username)
        else:
            Follow.objects.create(author=author, user=request.user)
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(author=author, user=request.user).delete()
    return redirect("posts:profile", username=username)
