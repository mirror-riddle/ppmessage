
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 PPMessage.
# Guijin Ding, dingguijin@gmail.com
# All rights reserved.
#
# core/utils/db2cache.py
#

from .datetimeencoder import DateTimeEncoder

from ppmessage.db.dbinstance import getDBSessionClass

from ppmessage.db.models import AppInfo

from ppmessage.db.models import DeviceUser
from ppmessage.db.models import DeviceInfo

from ppmessage.db.models import MessagePushTask
from ppmessage.db.models import MessagePush

from ppmessage.db.models import FileInfo

from ppmessage.db.models import ConversationInfo
from ppmessage.db.models import ConversationUserData

from ppmessage.db.models import PCSocketInfo
from ppmessage.db.models import PCSocketDeviceData

from ppmessage.db.models import ApiInfo

from sqlalchemy import DateTime

import redis
import logging
import datetime
import traceback

def _load_generic(_cls, _redis, _session):
    _all = _session.query(_cls).all()
    for _i in _all:
        _i.create_redis_keys(_redis, _is_load=True)
    return

def load(_redis):
    _redis.flushdb()
    _session_class = getDBSessionClass()
    _session = _session_class()

    _cls_list = [
        DeviceUser,
        DeviceInfo,            
        
        ConversationInfo,
        ConversationUserData,
        
        FileInfo,
        
        AppInfo,
        
        MessagePushTask,
        MessagePush,
        
        PCSocketInfo,
        PCSocketDeviceData,

        ApiInfo
              
    ]
    
    try:
        for _i in _cls_list:
            logging.info("Loading %s...", _i.__tablename__)
            _load_generic(_i, _redis, _session)
            logging.info("Loading .... done.")
    except:
        traceback.print_exc()
    finally:
        _session_class.remove()
        
    logging.info("$$$$$$$$$$$ LOAD DONE $$$$$$$$$$$$$")
    return
