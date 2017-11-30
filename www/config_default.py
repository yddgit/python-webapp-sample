#!/usr/bin/env python
# -*- coding: utf-8 -*-

u'''
默认配置
'''

configs = {
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'www-data',
        'password': 'www-data',
        'database': 'test'
    },
    'session': {
        'secret': 'AwEsOmE'
    },
    'upload': {
        'path': '/attachment',
        'allowFileType': ['jpg', 'jpeg', 'gif', 'png', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
        'maxSize': 10 * 1024 * 1024 #10MB
    }
}
