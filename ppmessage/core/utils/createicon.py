# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 PPMessage.
# Guijin Ding, dingguijin@gmail.com.
# All rights reserved.
#
# core/utils/createicon.py
#

from .identicon import Identicon
from .config import get_config_server_ssl
from .config import get_config_server_port
from .config import get_config_server_name
from .config import get_config_server_identicon_store

from ppmessage.db.models import FileInfo
from ppmessage.db.models import DeviceUser

from ppmessage.core.imageconverter import ImageConverter

import os
import hashlib

def _icon_url(_file_name):
    _ssl = get_config_server_ssl()
    _port = get_config_server_port()
    _server_name = get_config_server_name()

    if _ssl == None or _port == None or _server_name == None:
        logging.error("no ssl/port/server_name configed")
        return None

    _port = str(_port)
    _post = "/identicon/identicon/" + _file_name
    _protocol = "http"
    if _ssl == "on":
        _protocol = "https"
    _url = _protocol + "://" + _server_name + ":" + _port + _post
    return _url

def _url2local(_url):
    _file = _url[_url.rfind("/")+1:]
    _path = get_config_server_identicon_store()
    return _path + os.path.sep + _file

def create_user_icon(_uuid):
    _file_name = _uuid + ".png"
    _identicon_store = get_config_server_identicon_store()
    if _identicon_store == None:
        logging.error("no identicon_store configed")
        return None
    _path = _identicon_store + os.path.sep + _file_name
    if os.path.exists(_path):
        return _icon_url(_file_name)
    
    _image = Identicon(_uuid, 64)
    _image = _image.draw_image()
    _image.save(_path)
    return _icon_url(_file_name)

def create_group_icon(_redis, _users):
    _identicon_store = get_config_server_identicon_store()
    if _identicon_store == None:
        logging.error("no identicon_store configed")
        return None
    
    if len(_users) == 0:
        return None

    if len(_users) == 1:
        _user_key = DeviceUser.__tablename__ + ".uuid." + list(_users)[0]
        _user_icon = _redis.hget(_user_key, "user_icon")
        if _user_icon == None:
            return _icon_url("default_icon.png")
        return _user_icon
    
    _icon_list = []
    for _uuid in _users:
        _user_key = DeviceUser.__tablename__ + ".uuid." + _uuid
        _user_icon = _redis.hget(_user_key, "user_icon")
        if _user_icon != None:
            _icon_list.append(_user_icon)
        else:
            _icon_list.append(_icon_url("default_icon.png"))

    _icon_list = map(_url2local, _icon_list)
    
    _data = ImageConverter.conversation_icon(_icon_list)
    if _data == None:
        logging.error("conversation icon data is None, will not create icon file")
        return None
    _file_name = hashlib.sha1("".join(_users)).hexdigest() + ".png"
    _file_path = _identicon_store + os.path.sep + _file_name
    _file = open(_file_path, "wb")
    _file.write(_data)
    _file.close()
    return _icon_url(_file_name)
