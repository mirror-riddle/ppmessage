# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 PPMessage.
# Guijin Ding, dingguijin@gmail.com
# All rights reserved
#
# backend/main.py 
# The entry of PPMessage
#


from ppmessage.core.constant import MAIN_PORT
from ppmessage.core.constant import REDIS_HOST
from ppmessage.core.constant import REDIS_PORT
from ppmessage.core.constant import CONFIG_STATUS

from ppmessage.core.main import get_total_handlers
from ppmessage.core.main import get_total_delegates
from ppmessage.core.utils.config import _get_config
from ppmessage.core.utils.getipaddress import get_ip_address

from ppmessage.core.downloadhandler import DownloadHandler

from ppmessage.api.apiapp import ApiWebService
from ppmessage.backend.send import SendWebService
from ppmessage.cache.cacheapp import CacheWebService
from ppmessage.backend.ppcomapp import PPComWebService
from ppmessage.backend.ppkefuapp import PPKefuWebService
from ppmessage.backend.ppauthapp import PPAuthWebService
from ppmessage.backend.ppconfigapp import PPConfigWebService
from ppmessage.backend.dispatcher import DispatcherWebService
from ppmessage.backend.identiconapp import IdenticonWebService
from ppmessage.pcsocket.pcsocketapp import PCSocketWebService
from ppmessage.backend.tornadouploadapp import UploadWebService
from ppmessage.backend.downloadapplication import DownloadWebService

import os
import sys
import redis
import logging
import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpserver

tornado.options.define("main_port", default=MAIN_PORT, help="", type=int)  

class EntryHandler(tornado.web.RequestHandler):
    def get(self):
        if _get_config() == None or _get_config().get("config_status") != CONFIG_STATUS.RESTART:
            self.redirect("/ppconfig/")
        else:
            self.redirect("/ppkefu/")
        return

class MainApplication(tornado.web.Application):
    
    def __init__(self):
        settings = {}
        settings["debug"] = True
        settings["cookie_secret"] = "24oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo="
        settings["template_path"]= os.path.join(os.path.dirname(__file__), "../resource/template")

        self.redis = redis.Redis(REDIS_HOST, REDIS_PORT, db=1)

        DownloadHandler.set_cls_redis(self.redis)
        
        self.total_handlers = get_total_handlers()
        self.total_delegates = get_total_delegates(self)
        
        handlers = [(r"/", EntryHandler)]
        for i in self.total_handlers:
            _name = "/" + i["name"].lower() + i["handler"][0]
                        
            handler = (_name, i["handler"][1])
            if len(i["handler"]) == 3:
                handler = (_name, i["handler"][1], i["handler"][2])
            handlers.append(handler)

        tornado.web.Application.__init__(self, handlers, **settings)        
        return

    def get_delegate(self, name):
        return self.total_delegates.get(name)

    def run_periodic(self):
        for name in self.total_delegates:
            self.total_delegates[name].run_periodic()
        return

    def load_db_to_cache(self):
        if _get_config() == None or _get_config().get("config_status") != CONFIG_STATUS.RESTART:
            self.redis.flushdb()
            return
        else:
            from ppmessage.core.utils.db2cache import load
            load(self.redis)
        return
    def copy_default_icon(self):
        if _get_config() == None or _get_config().get("config_status") != CONFIG_STATUS.RESTART:
            return
        _src = os.path.join(os.path.dirname(__file__), "../core/default_icon.png")
        _dst = os.path.join(_get_config().get("server").get("identicon_store"), "default_icon.png")
        if os.path.exists(_dst):
            return
        from shutil import copyfile
        copyfile(_src, _dst)
        return


def _main():
    import sys
    reload(sys)
    sys.setdefaultencoding('utf8')

    tornado.options.parse_command_line()

    _app = MainApplication()

    _app.copy_default_icon()

    _app.load_db_to_cache()
    
    tornado.httpserver.HTTPServer(_app).listen(tornado.options.options.main_port)
    _app.run_periodic()
    
    _str = "Access http://%s:%d/ to %s PPMessage."
    if _get_config() == None or _get_config().get("config_status") != CONFIG_STATUS.RESTART:
        logging.info(_str % (get_ip_address(), tornado.options.options.main_port, "config"))
    else:
        logging.info(_str % (get_ip_address(), tornado.options.options.main_port, "use"))
    tornado.ioloop.IOLoop.instance().start()
    return

if __name__ == "__main__":
    _main()
