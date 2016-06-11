# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 PPMessage.
# Jin He, jin.he@ppmessage.com
#
#

from .basehandler import BaseHandler

from ppmessage.api.error import API_ERR
from ppmessage.db.models import DeviceUser
from ppmessage.core.constant import API_LEVEL
from ppmessage.core.constant import SERVICE_USER_STATUS

import json
import logging

class PPKefuSetServiceUserStatus(BaseHandler):

    def _set(self):
        _request = json.loads(self.request.body)

        _user_uuid = _request.get("user_uuid")
        _user_status = _request.get("user_status")
        if _user_uuid == None or len(_user_uuid) == 0:
            self.setErrorCode(API_ERR.NO_PARA)
            return

        # NULL, READY, BUSY, REST
        if _user_status not in SERVICE_USER_STATUS:
            self.setErrorCode(API_ERR.INVALID_PARAM)
            return

        _key = DeviceUser.__tablename__ + ".uuid." + _user_uuid
        if not self.application.redis.exists(_key):
            self.setErrorCode(API_ERR.NO_USER)
            return
            
        _user = DeviceUser(uuid=_user_uuid, service_user_status=_user_status)
        _user.async_update(self.application.redis)
        _user.update_redis_keys(self.application.redis)
        return

    def initialize(self):
        self.addPermission(app_uuid=True)
        self.addPermission(api_level=API_LEVEL.PPKEFU)
        self.addPermission(api_level=API_LEVEL.THIRD_PARTY_KEFU)
        return

    def _Task(self):
        super(PPKefuSetServiceUserStatus, self)._Task()
        self._set()
        return
