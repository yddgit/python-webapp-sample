#!/usr/bin/env python
# -*- coding: utf-8 -*-

from transwarp.web import get, view
from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
from models import User, Blog, Comment

@view('blogs.html')
@get('/')
def index():
    u'博客首页'
    blogs = Blog.find_all()
    # 查找登录用户
    user = User.find_first('where email=?', 'tom@example.com')
    return dict(blogs=blogs, user=user)

@api
@get('/api/users')
def api_get_users():
    u'获取用户列表的API'
    users = User.find_by('order by created_at desc')
    # 把用户的口令隐藏掉
    for u in users:
        u.password = '******'
    return dict(users=users)

