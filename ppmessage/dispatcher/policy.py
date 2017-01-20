# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 PPMessage.
# Guijin Ding, dingguijin@gmail.com
#

from ppmessage.core.constant import IOS_FAKE_TOKEN
from ppmessage.core.constant import CONVERSATION_TYPE
from ppmessage.core.constant import MESSAGE_SUBTYPE
from ppmessage.core.constant import MESSAGE_STATUS
from ppmessage.core.constant import MESSAGE_TYPE
from ppmessage.core.constant import TASK_STATUS

from ppmessage.core.constant import REDIS_DISPATCHER_NOTIFICATION_KEY
from ppmessage.core.constant import REDIS_PUSH_NOTIFICATION_KEY
from ppmessage.core.constant import REDIS_MQTTPUSH_KEY
from ppmessage.core.constant import REDIS_GCMPUSH_KEY
from ppmessage.core.constant import REDIS_IOSPUSH_KEY
from ppmessage.core.constant import REDIS_JPUSH_KEY
from ppmessage.core.constant import PPCOM_OFFLINE
from ppmessage.core.constant import YVOBJECT
from ppmessage.core.constant import DIS_SRV
from ppmessage.core.constant import OS

from ppmessage.db.models import DeviceUser
from ppmessage.db.models import DeviceInfo
from ppmessage.db.models import MessagePush
from ppmessage.db.models import MessagePushTask
from ppmessage.db.models import PCSocketInfo
from ppmessage.db.models import PCSocketDeviceData
from ppmessage.db.models import ConversationUserData

from ppmessage.core.redis import redis_hash_to_dict
from ppmessage.core.utils.datetimestring import datetime_to_timestamp
from ppmessage.core.utils.datetimestring import datetime_to_microsecond_timestamp

from operator import itemgetter

import uuid
import time
import json
import logging

class Meta(type):
   def __init__(cls, name, bases, dict_):
       type.__init__(cls, name, bases, dict_)
       return

Policy = Meta("Policy", (object,), {})
class AbstractPolicy(Policy):

    def __init__(self, dis):
        self._dis = dis
        self._task = dis._task

        self._redis = dis.application.redis
        
        self._online_users = set()
        self._offline_users = set()
        
        self._devices = set()

        self._devices_hash = {}
        self._users_hash = {}

        self._is_service_user = {}
        self._conversation_users = set()
        self._conversation_user_datas_uuid = {}
        self._conversation_user_datas_hash = {}
        
        self._users = set()
        return

    @classmethod
    def conversation_users(cls, _conversation_uuid, _redis):
        _key = ConversationUserData.__tablename__ + ".conversation_uuid." + _conversation_uuid
        _users = _redis.smembers(_key)
        return list(_users)

    @classmethod
    def conversation_datas(cls, _conversation_uuid, _users, _redis):
        _pi = _redis.pipeline()
        _pre = ConversationUserData.__tablename__ + ".user_uuid."
        _pos = ".conversation_uuid." + _conversation_uuid
        for _user_uuid in _users:
            _key = _pre + _user_uuid + _pos
            _pi.get(_key)
        _datas = _pi.execute()
        return _datas

    @classmethod
    def create_conversation_users(cls, _redis):
        return []
    
    @classmethod
    def app_users(cls, _is_service_user, _redis):
        _key = DeviceUser.__tablename__ + ".is_service_user." + str(_is_service_user)
        _users = _redis.smembers(_key)
        return list(_users)

    @classmethod
    def get_service_care_users(cls, _user_uuid, _redis):
        return None

    @classmethod
    def get_portal_care_users(cls, _user_uuid, _redis):
        return None
        
    def _body(self):
        _message = {}
        _message["id"] = self._task.get("uuid")
        _message["fi"] = self._task.get("from_uuid")
        _message["ti"] = self._task.get("to_uuid")
        _message["ft"] = self._task.get("from_type")
        _message["tt"] = self._task.get("to_type")
        _message["mt"] = self._task.get("message_type")
        _message["ms"] = self._task.get("message_subtype")
        _message["ci"] = self._task.get("conversation_uuid")
        _message["ct"] = self._task.get("conversation_type")
        _message["tl"] = self._task.get("title")
        _message["bo"] = self._task.get("body")

        if _message["ct"] == CONVERSATION_TYPE.S2P:
            _message["tt"] = YVOBJECT.AP
                
        if isinstance(self._task.get("title"), unicode):
            _message["tl"] = self._task.get("title").encode("utf-8")
        if isinstance(self._task.get("body"), unicode):
            _message["bo"] = self._task.get("body").encode("utf-8")

        _message["ts"] = datetime_to_microsecond_timestamp(self._task["createtime"])
        
        self._task["message_body"] = _message

        _message_body = json.dumps(self._task["message_body"])
        if isinstance(_message_body, unicode):
           _message_body = _message_body.encode("utf-8")
            
        _values = {
            "uuid": self._task["uuid"],
            "task_status": TASK_STATUS.PROCESSED,
            "message_body": _message_body,
        }
        _row = MessagePushTask(**_values)
        _row.async_update(self._redis)
        _row.update_redis_keys(self._redis)
        return

    def _user_devices(self, _user_uuid):
        _user = self._users_hash.get(_user_uuid)
        _is_service_user = self._is_service_user.get(_user_uuid)
        
        if _user == None or _is_service_user == None:
            logging.error("no user or is_service_user in hash: %s" % _user_uuid)
            return
        
        _user["_online_devices"] = {}
        _device_name = "ppkefu_browser_device_uuid"
        if _is_service_user == False:
            _device_name = "ppcom_browser_device_uuid"
            
        _device_uuid = self._users_hash[_user_uuid][_device_name]
        if not _device_uuid:
            return
         
        _device = redis_hash_to_dict(self._redis, DeviceInfo, _device_uuid)
        if not _device:
            return

        self._devices_hash[_device_uuid] = _device
        self._devices.add(_device_uuid)
            
        if _device.get("device_is_online") == True:
            _user["_online_devices"][_device_uuid] = _device

        if len(_user["_online_devices"]) > 0:
            self._online_users.add(_user_uuid)
        else:
            self._offline_users.add(_user_uuid)
        return

    def _users_devices(self):
        for _i in self._users:
            self._users_hash[_i] = redis_hash_to_dict(self._redis, DeviceUser, _i)

        for _i in self._users:
            self._user_devices(_i)

        logging.info("online : %d, %s" % (len(self._online_users), self._online_users))
        logging.info("offline : %d, %s" % (len(self._offline_users), self._offline_users))
        return

    def _pcsocket_data(self, _device_uuid):
        _redis = self._redis
        _key = PCSocketDeviceData.__tablename__ + ".device_uuid." + _device_uuid
        _pc_socket_uuid = _redis.get(_key)
        if _pc_socket_uuid == None:
            logging.error("device no pcsocket %s" % _device_uuid)
            return None
        _info = redis_hash_to_dict(_redis, PCSocketInfo, _pc_socket_uuid)
        if _info == None:
            logging.error("dispatcher cant not find pcsocket %s" % str(_pc_socket_uuid))
            return None
        _d = {"host": _info["host"], "port": _info["port"], "device_uuid": _device_uuid}
        return _d
    
    def _push_to_db(self, _user_uuid, _status=MESSAGE_STATUS.PUSHED):
        _values = {
            "uuid": str(uuid.uuid1()),
            "task_uuid": self._task["uuid"],
            "user_uuid": _user_uuid,
            "status": _status
        }
                    
        _row = MessagePush(**_values)
        _row.async_add(self._redis)
        _row.create_redis_keys(self._redis)
        return _row.uuid
    
    def _push_to_socket(self, _user_uuid, _device_uuid):
        _pcsocket = self._pcsocket_data(_device_uuid)
        if _pcsocket == None:
            logging.error("no pcsocket data for: %s" % _device_uuid)
            return
        
        _device = self._devices_hash.get(_device_uuid)

        # if _device == None:
        #     logging.error("no device hash for: %s" % _device_uuid)
        #     return
        
        _from_user = {}
        _from_type = self._task.get("from_type")
        
        _fields = [
            "uuid",
            "user_icon",
            "user_email",
            "user_fullname",
            "updatetime",
        ]
        
        if _from_type == YVOBJECT.DU:
            for _i in _fields:
                _from_user[_i] = self._task["_user"].get(_i)
            _from_user["updatetime"] = datetime_to_timestamp(_from_user["updatetime"])
                        
        if _from_type == YVOBJECT.AP:
            _from_user = self._task["_app"]

        _body = self._task.get("message_body")
        _body["pid"] = _device.get("push_uuid")
        _body["from_user"] = _from_user
        _push = {
            "pcsocket": _pcsocket,
            "body": _body
        }
        _key = REDIS_PUSH_NOTIFICATION_KEY + ".host." + _pcsocket["host"] + ".port." + _pcsocket["port"]
        self._redis.rpush(_key, json.dumps(_push))
        return
        
    def _push(self):
        if not self._online_users:
            logging.error("no online user")
            return

        for _user_uuid in self._online_users:
            _user = self._users_hash[_user_uuid]
            _online_devices = _user.get("_online_devices")
            _pid = self._push_to_db(_user_uuid)            
            for _device_uuid in _online_devices:
                self._devices_hash[_device_uuid]["push_uuid"] = _pid
                self._push_to_socket(_user_uuid, _device_uuid)

        return

    def _explicit(self):
        """
        explicit message SYS type
        """
        _device_uuid = self._task.get("to_device_uuid")
        _device = redis_hash_to_dict(self._redis, DeviceInfo, _device_uuid)
        if _device == None:
            logging.error("no device:%s" % _device_uuid)
            return

        _user_uuid = self._task.get("from_uuid")
        self._users_hash[_user_uuid] = self._task["_user"]
        self._devices_hash[_device_uuid] = _device
        # not save db for explicit message
        self._push_to_socket(_user_uuid, _device_uuid)
        return
        
    def users(self):
        _conversation_uuid = self._task["conversation_uuid"]

        _users = AbstractPolicy.conversation_users(_conversation_uuid, self._redis)
        _datas = AbstractPolicy.conversation_datas(_conversation_uuid, _users, self._redis)
        _datas = dict(zip(_users, _datas))

        self._is_service_user = {}
        for _user_uuid in _users:
           _key = DeviceUser.__tablename__ + ".uuid." + _user_uuid
           self._is_service_user[_user_uuid] = True
           if self._redis.hget(_key, "is_service_user") != "True":
              self._is_service_user[_user_uuid] = False
        
        # remove the sender self
        if self._task["from_type"] == YVOBJECT.DU:
            _user_uuid = self._task["from_uuid"]
            if _user_uuid in _users:
                _users.remove(_user_uuid)
            if _user_uuid in _datas:
                del _datas[_user_uuid]

        self._users = _users
        self._conversation_users = _users
        self._conversation_user_datas_uuid = _datas
        return

    def dispatch(self):
        self._body()
        
        if self._task.get("to_device_uuid") != None:
            self._explicit()
            return

        if self._task.get("conversation_uuid") == None:
            logging.error("no conversation should be explicit")
            return
        
        self.users()
        self._users_devices()
        self._push()
        return
    
class BroadcastPolicy(AbstractPolicy):
    def __init__(self, dis):
        super(BroadcastPolicy, self).__init__(dis)
        return

    def users(self):
        super(BroadcastPolicy, self).users()
        return

    @classmethod
    def create_conversation_users(cls, _redis):
        return AbstractPolicy.distributor_users(_redis)

    @classmethod
    def get_service_care_users(cls, _user_uuid, _redis):
        _a_users = AbstractPolicy.app_users(True, _redis)
        _b_users = AbstractPolicy.app_users(False, _redis)
        return _a_users + _b_users

    @classmethod
    def get_portal_care_users(cls, _user_uuid, _redis):
        _a_users = AbstractPolicy.app_users(True, _redis)
        return _a_users

