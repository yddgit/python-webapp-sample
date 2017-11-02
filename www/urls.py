#!/usr/bin/env python
# -*- coding: utf-8 -*-

from transwarp.web import get, view
from models import User, Blog, Comment

@view('blogs.html')
@get('/')
def index():
    u'博客首页'
    blogs = Blog.find_all()
    # 查找登录用户
    user = User.find_first('where email=?', 'tom@example.com')
    return dict(blogs=blogs, user=user)


