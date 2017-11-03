#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, time, base64, hashlib, logging

from transwarp.web import get, post, view, ctx, interceptor, seeother, notfound
from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
from models import User, Blog, Comment
from config import configs

# Cookie名称
_COOKIE_NAME = 'pwssession'
# Cookie SecretKey
_COOKIE_KEY = configs.session.secret

# HTTP协议是无状态协议，服务器要跟踪用户状态只能通过cookie实现
# 大多数Web框架提供了session功能来封装保存用户状态的cookie，简单易用，可以直接从Session中取出用户登录信息
# Session的缺点是服务器需要在内存中维护一个映射表来存储用户登录信息，如果有两台以上服务器就要对Session做集群，难以扩展
# 这里采用直接读取cookie的方式来验证用户登录，每次用户访问任意URL都会对cookie进行验证，这可以保证服务器处理任意的URL都是无状态的，可以扩展到多台服务器

# 由于cookie是服务器生成的，要保证这个cookie不会被客户端伪造。
# 实现防伪造cookie的关键是使用一个单向算法（如MD5）
# 当用户登录成功后，服务器可以按照如下方式计算出一个字符串：
#   user_id + expire_time + md5(user_id + password + expire_time + SecretKey)
# 当浏览器发送cookie到服务器后，服务端拿到user_id、expire_time、md5，如果未到期就根据以下算法计算md5：
#   md5(user_id + password + expire_time + SecretKey)
# 如果与浏览器cookie中的md5相等，则说明用户已登录，否则cookie就是伪造的

def make_signed_cookie(id, password, max_age):
    u'生成Cookie'
    # build cookie string by: id-expires-md5
    expires = str(int(time.time() + (max_age or 86400)))
    L = [id, expires, hashlib.md5('%s-%s-%s-%s' % (id, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(L)

def parse_signed_cookie(cookie_str):
    u'验证Cookie'
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        id, expires, md5 = L
        if int(expires) < time.time():
            return None
        user = User.get(id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except:
        return None

def check_admin():
    u'检查当前登录用户是否是管理员'
    user = ctx.request.user
    if user and user.admin:
        return
    raise APIPermissionError('No permission.')

def _get_page_index():
    u'获取当前页码'
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index

def _get_blogs_by_page():
    u'分页获取博客数据'
    total = Blog.count_all()
    page = Page(total, _get_page_index())
    blogs = Blog.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return blogs, page

@view('blogs.html')
@get('/')
def index():
    u'博客首页'
    blogs, page = _get_blogs_by_page()
    return dict(page=page, blogs=blogs, user=ctx.request.user)

@view('signin.html')
@get('/signin')
def signin():
    u'登录页面'
    return dict()

@get('/signout')
def signout():
    u'退出'
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise seeother('/')

@view('register.html')
@get('/register')
def register():
    u'注册页面'
    return dict()

@view('manage_blog_edit.html')
@get('/manage/blogs/create')
def manage_blogs_create():
    u'编辑日志页面'
    return dict(id=None, action='/api/blogs', redirect='/manage/blogs', user=ctx.request.user)

@view('manage_blog_list.html')
@get('/manage/blogs')
def manage_blogs():
    u'博客列表页面'
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@api
@get('/api/users')
def api_get_users():
    u'获取用户列表的API'
    users = User.find_by('order by created_at desc')
    # 把用户的口令隐藏掉
    for u in users:
        u.password = '******'
    return dict(users=users)

# 校验Email的正则表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# 校验MD5密码摘要的正则表达式
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')

@api
@post('/api/users')
def register_user():
    u'用户注册API'
    i = ctx.request.input(name='', email='', password='')
    name = i.name.strip()
    email = i.email.strip().lower()
    password = i.password
    if not name:
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    # 用户密码是客户端传递的经过MD5计算后的32位Hash字符串
    if not password or not _RE_MD5.match(password):
        raise APIValueError('password')
    user = User.find_first('where email=?', email)
    if user:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    user = User(name=name, email=email, password=password, image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
    user.insert()
    # 为新注册用户创建Cookie:
    cookie = make_signed_cookie(user.id, user.password, None)
    ctx.response.set_cookie(_COOKIE_NAME, cookie)
    return user

@api
@post('/api/authenticate')
def authenticate():
    u'用户登录验证API'
    i = ctx.request.input(remember='')
    email = i.email.strip().lower()
    password = i.password
    remember = i.remember
    user = User.find_first('where email=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'Invalid email.')
    elif user.password != password:
        raise APIError('auth:failed', 'password', 'Invalid password.')
    # make session cookie:
    max_age = 604800 if remember=='true' else None
    cookie = make_signed_cookie(user.id, user.password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
    user.password = '******'
    return user

@api
@post('/api/blogs')
def api_create_blog():
    u'创建一个Blog'
    check_admin()
    i = ctx.request.input(name='', summary='', content='')
    name = i.name.strip()
    summary = i.summary.strip()
    content = i.content.strip()
    if not name:
        raise APIValueError('name', 'name cannot be empty.')
    if not summary:
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content:
        raise APIValueError('content', 'content cannot be empty.')
    user = ctx.request.user
    blog = Blog(user_id=user.id, user_name=user.name, user_image=user.image, name=name, summary=summary, content=content)
    blog.insert()
    return blog

@api
@get('/api/blogs')
def api_get_blogs():
    u'分页获取博客数据API'
    format = ctx.request.get('format', '')
    blogs, page = _get_blogs_by_page()
    if format=='html':
        for blog in blogs:
            blog.content = markdown2.markdown(blog.content)
    return dict(blogs=blogs, page=page)

@interceptor('/')
def user_interceptor(next):
    u'''
    用拦截器在处理URL之前把Cookie解析出来，并将登录用户绑定到ctx.request对象上。这样后续URL处理函数就可以直接拿到登录用户
    '''
    logging.info('try to bind user from session cookie...')
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('parse session cookie...')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('bind user <%s> to session...' % user.email)
    ctx.request.user = user
    return next()

@interceptor('/manage/')
def manage_interceptor(next):
    u'管理员权限验证拦截器'
    user = ctx.request.user
    if user and user.admin:
        return next()
    raise seeother('/signin')

