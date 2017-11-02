#!/usr/bin/env python
# -*- coding: utf-8 -*-

u'''
实体类

>>> u = User(name='Test', email='test@example.com', password='123456', image='about:blank')
>>> u.insert() #doctest: +ELLIPSIS
{'name': 'Test', ...
>>> u1 = User.find_first('where email=?', 'test@example.com')
>>> u1.name
u'Test'
>>> u1.delete() #doctest: +ELLIPSIS
{u'name': u'Test', ...
>>> u2 = User.find_first('where email=?', 'test@example.com')
>>> u2 == None
True
'''

import time, uuid

from transwarp.db import next_id
from transwarp.orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    u'用户'
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(updatable=False, dll='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(updatable=False, default=time.time)

class Blog(Model):
    u'博客'
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(updatable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)

class Comment(Model):
    u'评论'
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(updatable=False, ddl='varchar(50)')
    user_id = StringField(updatable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)

if __name__ == '__main__':
    # 生成schema.sql脚本
    import os
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema.sql'), 'w') as f:
        sql = ['-- schema.sql']
        sql.append('-- help:')
        sql.append('--   Login MySQL: mysql -u root -p')
        sql.append('--   Execute Script: source /path/to/schema.sql')
        sql.append('drop database if exists test;')
        sql.append('create database test;')
        sql.append('use test;')
        sql.append('create user if not exists \'www-data\'@\'localhost\' identified by \'www-data\';')
        sql.append('-- grant select, insert, update, delete on test.* to \'www-data\'@\'localhost\' identified by \'www-data\';')
        sql.append('grant all privileges on test.* to \'www-data\'@\'localhost\' identified by \'www-data\';')
        sql.append(User().__sql__())
        sql.append(Blog().__sql__())
        sql.append(Comment().__sql__())
        f.write('\n'.join(sql))
    # 执行doctest
    import logging
    logging.basicConfig(level=logging.DEBUG)
    from transwarp import db
    db.create_engine('www-data', 'www-data', 'test')
    import doctest
    doctest.testmod()
