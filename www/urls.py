#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, time, base64, hashlib, logging, uuid, mimetypes
from urllib import quote

import markdown2

from transwarp.web import get, post, view, ctx, interceptor, seeother, notfound, static_file_generator, MultipartFile
from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
from models import User, Blog, Comment, Attachment
from config import configs

# Cookie名称
_COOKIE_NAME = 'pwssession'
# Cookie SecretKey
_COOKIE_KEY = configs.session.secret
# Upload Path
_UPLOAD_PATH = configs.upload.path
# Upload Allow File Type
_UPLOAD_ALLOW_FILE_TYPE = configs.upload.allowFileType
# Upload Max Size
_UPLOAD_MAX_SIZE = configs.upload.maxSize

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

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

@view('blog.html')
@get('/blog/:blog_id')
def blog(blog_id):
    u'博客详情页'
    blog = Blog.get(blog_id)
    if blog is None:
        raise notfound()
    blog.html_content = markdown2.markdown(blog.content)
    comments = Comment.find_by('where blog_id=? order by created_at desc limit 1000', blog_id)
    return dict(blog=blog, comments=comments, user=ctx.request.user)

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

@get('/manage/')
def manage_index():
    u'后台管理首页'
    raise seeother('/manage/comments')

@view('manage_comment_list.html')
@get('/manage/comments')
def manage_comments():
    u'评论列表页面'
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_blog_edit.html')
@get('/manage/blogs/create')
def manage_blogs_create():
    u'创建日志页面'
    return dict(id=None, action='/api/blogs', redirect='/manage/blogs', user=ctx.request.user)

@view('manage_blog_edit.html')
@get('/manage/blogs/edit/:blog_id')
def manage_blogs_edit(blog_id):
    u'编辑日志页面'
    blog = Blog.get(blog_id)
    if blog is None:
        raise notfound()
    return dict(id=blog.id, name=blog.name, summary=blog.summary, content=blog.content, action='/api/blogs/%s' % blog_id, redirect='/manage/blogs', user=ctx.request.user)

@view('manage_user_list.html')
@get('/manage/users')
def manage_users():
    u'用户列表页面'
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_blog_list.html')
@get('/manage/blogs')
def manage_blogs():
    u'博客列表页面'
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_attachment_list.html')
@get('/manage/attachments')
def manage_attachments():
    u'附件列表页面'
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_attachment_create.html')
@get('/manage/attachments/create')
def manage_attachments_create():
    u'创建附件页面'
    allow_file_type = "|".join(_UPLOAD_ALLOW_FILE_TYPE)
    return dict(id=None, action='/api/attachments', redirect='/manage/attachments', allow_file_type=allow_file_type, user=ctx.request.user)

@get('/attachment/:attachment_id')
def attachment(attachment_id):
    u'下载附件'
    attachment = Attachment.get(attachment_id)
    if attachment is None:
        raise notfound()
    local_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), attachment.file_path[1:]))
    if not os.path.exists(local_path):
        raise notfound()
    if not os.path.isfile(local_path):
        raise notfound()
    ctx.response.set_header('Content-Length', os.path.getsize(local_path))
    ctx.response.set_header('Content-Type', attachment.file_type)
    ctx.response.set_header('Content-Disposition', 'attachment;filename="%s"' % quote(attachment.file_name.encode('utf-8')))
    return static_file_generator(local_path)

@api
@get('/api/users')
def api_get_users():
    u'获取用户列表的API'
    total = User.count_all()
    page = Page(total, _get_page_index())
    users = User.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    # 把用户的口令隐藏掉
    for u in users:
        u.password = '******'
    return dict(users=users, page=page)

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
    user = User(name=name, email=email, password=password, image='https://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
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

@api
@get('/api/blogs/:blog_id')
def api_get_blog(blog_id):
    u'查看博客详情API'
    blog = Blog.get(blog_id)
    if blog:
        return blog
    raise APIResourceNotFoundError('Blog')

@api
@post('/api/blogs/:blog_id')
def api_update_blog(blog_id):
    u'更新博客API'
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
    blog = Blog.get(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    blog.name = name
    blog.summary = summary
    blog.content = content
    blog.update()
    return blog

@api
@post('/api/blogs/:blog_id/delete')
def api_delete_blog(blog_id):
    u'删除博客API'
    check_admin()
    blog = Blog.get(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    blog.delete()
    return dict(id=blog_id)

@api
@post('/api/blogs/:blog_id/comments')
def api_create_blog_comment(blog_id):
    u'创建博客评论API'
    user = ctx.request.user
    if user is None:
        raise APIPermissionError('Need signin.')
    blog = Blog.get(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    content = ctx.request.input(content='').content.strip()
    if not content:
        raise APIValueError('content')
    c = Comment(blog_id=blog_id, user_id=user.id, user_name=user.name, user_image=user.image, content=content)
    c.insert()
    return dict(comment=c)

@api
@post('/api/comments/:comment_id/delete')
def api_delete_comment(comment_id):
    u'删除博客评论API'
    check_admin()
    comment = Comment.get(comment_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment')
    comment.delete()
    return dict(id=comment_id)

@api
@get('/api/comments')
def api_get_comments():
    u'博客评论列表API'
    total = Comment.count_all()
    page = Page(total, _get_page_index())
    comments = Comment.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return dict(comments=comments, page=page)

@api
@post('/api/attachments')
def api_create_attachment():
    u'创建附件API'
    check_admin()

    # 获取上传的文件
    i = ctx.request.input(attachment_file='')
    f = i.attachment_file
    if not isinstance(f, MultipartFile):
        raise APIValueError('attachment_file', 'attachment_file must be a file.')

    # 检验文件参数
    file_name = f.filename # filename
    if not file_name:
        raise APIValueError('file_name', 'file_name cannot be empty.')

    fext = os.path.splitext(file_name)[1] # file ext
    if not fext[1:] in _UPLOAD_ALLOW_FILE_TYPE:
        raise APIValueError('file_type', '*%s file is not allowed to upload.' % fext)

    file_type = mimetypes.types_map.get(fext.lower(), 'application/octet-stream') # content-type
    if not file_type:
        raise APIValueError('file_type', 'file_type cannot be empty.')

    file_data = f.file # file data
    if not file_data:
        raise APIValueError('file_data', 'file_data cannot be empty.')

    # 保存上传的文件
    file_path = '%s/%s' % (_UPLOAD_PATH, next_id()) # file path
    local_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path[1:]))
    if not os.path.exists(os.path.dirname(local_path)):
        # 支持递归创建多级目录
        os.makedirs(os.path.dirname(local_path))

    # Buffer Size
    BLOCK_SIZE = 8192
    with open(local_path, 'wb') as upload_file:
        file_size = 0
        while True:
            data = file_data.read(BLOCK_SIZE)
            if not data:
                break
            file_size = file_size + len(data)
            if file_size > _UPLOAD_MAX_SIZE:
                break
            upload_file.write(data)

    # 文件过大不能上传
    if file_size > _UPLOAD_MAX_SIZE:
        os.remove(local_path)
        raise APIError('file too big to upload.')

    # 保存数据库记录
    user = ctx.request.user
    attachment = Attachment(user_id=user.id, file_name=file_name, file_path=file_path, file_type=file_type)
    attachment.insert()
    return attachment

@api
@post('/api/attachments/:attachment_id/delete')
def api_delete_attachment(attachment_id):
    u'删除附件API'
    check_admin()
    attachment = Attachment.get(attachment_id)
    if attachment is None:
        raise APIResourceNotFoundError('Attachment')
    # 删除本地文件
    local_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), attachment.file_path[1:]))
    if os.path.exists(local_path):
        os.remove(local_path)
    # 删除数据库记录
    attachment.delete()
    return dict(id=attachment_id)

@api
@get('/api/attachments')
def api_get_attachments():
    u'附件列表API'
    check_admin()
    total = Attachment.count_all()
    page = Page(total, _get_page_index())
    attachments = Attachment.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return dict(attachments=attachments, page=page)

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

