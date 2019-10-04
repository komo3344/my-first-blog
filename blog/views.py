# blog/views.py
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Post, Comment
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


def post_list(request):
    posts = Post.objects.filter(published_date__lte=timezone.now()).order_by('-published_date')
    return render(request, 'blog/post_list.html', {'posts': posts})


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'blog/post_detail.html', {'post': post})


@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            # post.published_date = timezone.now() 작성한 글이 바로 게시(미리보기 X)
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'blog/post_edit.html', {'form': form})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            # post.published_date = timezone.now()
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_edit.html', {'form': form})


@login_required
def post_draft_list(request):
    posts = Post.objects.filter(published_date__isnull=True).order_by('created_date')  # 발행되지 않은 글 목록 가져오기
    return render(request, 'blog/post_draft_list.html', {'posts': posts})


@login_required
def post_publish(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.publish()
    return redirect('post_detail', pk=pk)


@login_required
def post_remove(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.delete()
    return redirect('post_list')


def add_comment_to_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.save()
            return redirect('post_detail', pk=post.pk)
    else:

        if request.user.is_staff:
            form = CommentForm(initial={'author': request.user})
            # print(request.session.get('nickName'))
            # print(User.objects.filter(username=request.session.get('nickName')))
            return render(request, 'blog/add_comment_to_post.html', {'form': form})

        elif request.session.get('nickName'):   # kakao->oauth->add_comment_to_post

            form = CommentForm(initial={'author': request.session.get('nickName')})
            return render(request, 'blog/add_comment_to_post.html', {'form': form})

        else:
            login_request_uri = 'https://kauth.kakao.com/oauth/authorize?'

            client_id = '63e4734e72d2d421ef9d5ff9200a241f'
            redirect_uri = 'http://127.0.0.1:8000/oauth'
            post_primary_key = pk
            login_request_uri += 'client_id=' + client_id
            login_request_uri += '&redirect_uri=' + redirect_uri
            login_request_uri += '&response_type=code'

            request.session['client_id'] = client_id
            request.session['redirect_uri'] = redirect_uri
            request.session['post_primary_key'] = post_primary_key
            return redirect(login_request_uri)

    


@login_required
def comment_approve(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.approve()
    return redirect('post_detail', pk=comment.post.pk)


@login_required
def comment_remove(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.delete()
    return redirect('post_detail', pk=comment.post.pk)


def oauth(request):
    code = request.GET['code']
    client_id = request.session.get('client_id')
    redirect_uri = request.session.get('redirect_uri')
    post_primary_key = request.session.get('post_primary_key')

    # 발급받은 code를 통해 access token 발급
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'code': code
    }
    response_token = requests.post('https://kauth.kakao.com/oauth/token', data=data)
    access_token_json = response_token.json()

    # access token을 이용하여 사용자 정보받기
    headers = {
        'Authorization': 'Bearer {}'.format(access_token_json['access_token']),
    }
    response_userinfo = requests.get('https://kapi.kakao.com/v2/user/me', headers=headers)
    userinfo_json = response_userinfo.json()

    nickName = str(userinfo_json['properties']['nickname']) + str('#' + str(userinfo_json['id']))

    if not User.objects.filter(username=nickName):
        User.objects.create_user(nickName)

    request.session['nickName'] = nickName
    # print('코드 : ', code)
    # print('엑세스토큰 : ', access_token_json)
    # print(userinfo_json)
    # print(User.objects.all())

    return redirect('http://127.0.0.1:8000/post/{}/comment/'.format(post_primary_key))
