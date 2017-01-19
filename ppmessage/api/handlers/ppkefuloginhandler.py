# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 PPMessage.
# Guijin Ding, dingguijin@gmail.com
#
#

from ppmessage.api.handlers.basehandler import BaseHandler

from ppmessage.db.models import AppInfo
from ppmessage.db.models import DeviceUser
from ppmessage.db.models import DeviceInfo
from ppmessage.db.models import PCSocketInfo
from ppmessage.db.models import MessagePushTask
from ppmessage.db.models import PCSocketDeviceData

from ppmessage.api.error import API_ERR

from ppmessage.core.constant import OS
from ppmessage.core.constant import YVOBJECT
from ppmessage.core.constant import API_LEVEL
from ppmessage.core.constant import TASK_STATUS
from ppmessage.core.constant import MESSAGE_TYPE
from ppmessage.core.constant import PCSOCKET_SRV
from ppmessage.core.constant import ONLINE_STATUS
from ppmessage.core.constant import MESSAGE_SUBTYPE
from ppmessage.core.constant import SERVICE_USER_STATUS
from ppmessage.core.constant import REDIS_PPKEFU_ONLINE_KEY
from ppmessage.core.constant import REDIS_LOGOUT_NOTIFICATION_KEY

from ppmessage.core.utils.config import _get_config

from ppmessage.pcsocket.pcsocketapp import pcsocket_user_online
from ppmessage.core.redis import redis_hash_to_dict

import traceback
import datetime
import logging
import hashlib
import json
import uuid
import time

class PPKefuLoginHandler(BaseHandler):

    def _push_offline_message(self, _user_uuid, _device_uuid):
        _redis = self.application.redis
        _key = PCSocketDeviceData.__tablename__ + ".device_uuid." + _device_uuid
        _pcsocket_uuid = _redis.get(_key)
        if _pcsocket_uuid == None:
            return
        _pcsocket = redis_hash_to_dict(_redis, PCSocketInfo, _pcsocket_uuid)
        if _pcsocket == None:
            return
        _logout = {"device_uuid": _device_uuid, "other_device": self.device.get("uuid")}
        _key = REDIS_LOGOUT_NOTIFICATION_KEY + ".host." + _pcsocket["host"] + ".port." + _pcsocket["port"]
        _redis.rpush(_key, json.dumps(_logout))
        
        logging.info("force logout the same user with multiple devices")
        return

    def _offline_device(self, _device_uuid):
        _row = DeviceInfo(**{"uuid": _device_uuid, "device_is_online": False})
        _row.async_update(self.application.redis)
        _row.update_redis_keys(self.application.redis)
        return
    
    def _force_logout(self, _user_uuid, _device_uuid):
        self._offline_device(_device_uuid)
        self._push_offline_message(_user_uuid, _device_uuid)
        return
    
    def _create_device(self):

        _osmodel = self.input_data.get("osmodel")
        _osversion = self.input_data.get("osversion")
        _device_fullname = self.input_data.get("device_fullname")
        
        _is_development = bool(self.input_data.get("ios_app_development"))

        _device_ios_token = self.input_data.get("device_ios_token")
        _device_android_gcmtoken = self.input_data.get("device_android_gcmtoken")
        _device_android_jpush_registrationid = self.input_data.get("device_android_jpush_registrationid")
        
        _device_uuid = str(uuid.uuid1())
        _values = {
            "uuid": _device_uuid,
            "terminal_uuid": self._terminal_uuid,
            "user_uuid": self.user.get("uuid"),
            "device_ostype": self._ostype,
            "device_ios_model": _osmodel,
            "device_osversion": _osversion,
            "device_fullname": _device_fullname,

            "is_development": _is_development,
            
            "device_ios_token": _device_ios_token,
            "device_android_gcmtoken": _device_android_gcmtoken,
            "device_android_jpush_registrationid": _device_android_jpush_registrationid,

        }

        _row = DeviceInfo(**_values)
        _row.create_redis_keys(self.application.redis)
        _row.async_add(self.application.redis)
        return _values

    def _user_with_email(self):
        _redis = self.application.redis
        _key = DeviceUser.__tablename__ + ".user_email." + self._user_email

        if not _redis.exists(_key):
            self.setErrorCode(API_ERR.NO_USER)
            return False
        
        _user_uuid = _redis.get(_key)
        _user = redis_hash_to_dict(_redis, DeviceUser, _user_uuid)

        if _user == None:
            self.setErrorCode(API_ERR.NO_USER)
            return False

        self.user = _user
        return True
    
    def _update_user_with_device(self, _user_uuid, _device_uuid):
        _values = {"uuid": _user_uuid}
        _values["ppkefu_browser_device_uuid"] = _device_uuid
        _row = DeviceUser(**_values)
        _row.async_update(self.application.redis)
        _row.update_redis_keys(self.application.redis)
        return

    def _update_user_status(self, _user_uuid):
        _values = {"uuid": _user_uuid}
        _user_status = self.input_data.get("user_status")

        # NULL, READY, BUSY, REST
        if _user_status in SERVICE_USER_STATUS:
            _values["service_user_status"] = _user_status
        else:
            _values["service_user_status"] = SERVICE_USER_STATUS.READY
        _row = DeviceUser(**_values)
        _row.async_update(self.application.redis)
        _row.update_redis_keys(self.application.redis)
        return

    def _update_device_with_user(self, _device_uuid, _user_uuid):
        _values = {
            "uuid": _device_uuid,
            "user_uuid": _user_uuid,
        }
        _row = DeviceInfo(**_values)
        _row.update_redis_keys(self.application.redis)
        _row.async_update(self.application.redis)
        return

    def _update_device_with_token(self, _device_uuid):
        _device_android_jpush_registrationid = self.input_data.get("device_android_jpush_registrationid")
        _device_android_gcmtoken = self.input_data.get("device_android_gcmtoken")
        _device_ios_token = self.input_data.get("device_ios_token")
        _values = {
            "uuid": _device_uuid,
            "device_ios_token": _ios_token,
            "device_android_gcmtoken": _device_android_gcmtoken,
            "device_android_jpush_registrationid": _device_android_jpush_registrationid
        }
        _row = DeviceInfo(**_values)
        _row.update_redis_keys(self.application.redis)
        _row.async_update(self.application.redis)
        return
    
    def _reset_device_of_user(self, _user_uuid):
        _v = {
            "uuid": _user_uuid,
            "ppkefu_browser_device_uuid": "NULL"
        }
        _row = DeviceUser(**_v)
        _row.async_update(self.application.redis)
        _row.update_redis_keys(self.application.redis)
        return

    def _kick(self):
        _old_device_uuid = self.user.get("ppkefu_browser_device_uuid")
        if not _old_device_uuid:
            return
        
        if _old_device_uuid == self.device.get("uuid"):
            logging.info("old device and new device is same: %s" % _old_device_uuid)
            return

        _redis = self.application.redis
        _key = DeviceInfo.__tablename__ + ".uuid." + _old_device_uuid
        if not _redis.exists(_key):
            return
        
        _old_online = self.application.redis.hget(_key, "device_is_online")
        if _old_online == None or _old_online == "False":
            return

        logging.info("the same type device is online, send logout")
        self._force_logout(self.user.get("uuid"), _old_device_uuid)
        return

    def _update_device_online(self):
        _values = {
            "uuid": self.device.get("uuid"),
            "device_is_online": True
        }
        _row = DeviceInfo(**_values)
        _row.update_redis_keys(self.application.redis)
        _row.async_update(self.application.redis)
        return

    def _user_online_status(self):
        _user_uuid = self.user["uuid"]
        _device_uuid = self.device["uuid"]
        _redis = self.application.redis
        _key0 = REDIS_PPKEFU_ONLINE_KEY
        _redis.sadd(_key0, _user_uuid + "." + _device_uuid)

        _today = datetime.datetime.now().strftime("%Y-%m-%d")
        _key1 = _key0 + ".day." + _today
        _redis.sunionstore(_key1, _key0, _key0)

        _key2 = _key1 + ".hour." + str(datetime.datetime.now().hour)
        _redis.sunionstore(_key2, _key0, _key0)
        return
        
    #L2=========================================

    def _parameter(self, _p):
        if _p == None or len(_p) == 0:
            self.setErrorCode(API_ERR.NO_PARA)
            return False
        return True
    
    def _check_input(self):
        self.input_data = json.loads(self.request.body)

        self._terminal_uuid = self.input_data.get("terminal")
        if not self._parameter(self._terminal_uuid):
            return False
        
        self._user_email = self.input_data.get("user_email")
        if not self._parameter(self._user_email):
            return False

        self._ostype = self.input_data.get("ostype")
        if not self._parameter(self._ostype):
            return False
        self._ostype = self._ostype[:3].upper()

        return True

    def _device(self):
        self._terminal_uuid = self.input_data["terminal"]
        
        _device = None
        _redis = self.application.redis
        _key = DeviceInfo.__tablename__ + ".terminal_uuid." + self._terminal_uuid
        _device = redis_hash_to_dict(_redis, DeviceInfo, _redis.get(_key))
        
        if _device == None:
            return self._create_device()
        
        _old_device_user = _device.get("user_uuid")
        if self.user.get("uuid") != _old_device_user:
            self._reset_device_of_user(_old_device_user)

        return _device

    def _return(self):
        _redis = self.application.redis
        _user = redis_hash_to_dict(_redis, DeviceUser, self.user.get("uuid"))
        del _user["user_password"]
        _r = self.getReturnData()
        _r.update(_user)

        _app_uuid = _get_config().get("team").get("app_uuid")
        _key = AppInfo.__tablename__ + ".uuid." + _app_uuid
        _r["app"] = _redis.hgetall(_key)
        return

    def _send_online(self):
        _body = {
            "extra_data": None,
            "user_uuid": self.user.get("uuid"),
            "browser": ONLINE_STATUS.ONLINE
        }        
        pcsocket_user_online(self.application.redis, self.user.get("uuid"), _body)
        return

    #L1============================================
    def _login(self):
        self.input_data = None
        self.user = None
        self.ent = None
        self.device = None

        logging.info(self.request.body)
        if not self._check_input():
            self.setErrorCode(API_ERR.NO_PARA)
            return

        if not self._user_with_email():
            self.setErrorCode(API_ERR.NO_USER)
            return

        # have device or create it?
        self.device = self._device()
        if self.device == None:
            self.setErrorCode(API_ERR.NO_DEVICE)
            return

        self._update_device_with_user(self.device.get("uuid"), self.user.get("uuid"))        
        self._kick()
        self._update_user_with_device(self.user.get("uuid"), self.device.get("uuid"))
        self._update_user_status(self.user.get("uuid"))
        self._update_device_online()
        self._user_online_status()
        self._return()

        self._send_online()
        return

    #L0============================================
    def initialize(self):
        self.addPermission(api_level=API_LEVEL.PPKEFU)
        return

    def _Task(self):
        super(self.__class__, self)._Task()
        self._login()
        return
