# -*- coding: utf-8 -*-
'''
    The treehouse spontaneously generates imps, which are used to spawn your resources.

    Nodes allow control of additional CPU and GPU units.

    Nodes provide control for your cloud forest. 
    As your forces grow in number, you must spawn more nodes to control them.
'''

# This file is part of treehouse.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.

__author__ = 'Jean Chassoul'


import time
import zmq
import sys
import uuid
import itertools
import ujson as json
import logging
import arrow
import queries
import pylibmc as mc

from tornado.ioloop import PeriodicCallback as PeriodicCast

from tornado import gen, web

# from treehouse.system.client import publisher
# from treehouse.system.server import subscriber

from tornado import websocket

from treehouse.tools import options, indexes, periodic, new_resource

from treehouse.handlers import OverlordHandler, imps, nodes

from zmq.eventloop import ioloop

from zmq.eventloop.future import Context, Poller

from tornado import httpclient


# curl async http client
httpclient.AsyncHTTPClient.configure('tornado.curl_httpclient.CurlAsyncHTTPClient')

# ioloop
ioloop.install()

# iofun testing box
iofun = []
# e_tag
e_tag = False
# db global variable
db = False
# sql global variable
sql = False
# kvalue global variable
kvalue = False
# cache glogbal variable
cache = False


class OverlordWSHandler(websocket.WebSocketHandler):
    '''
        Websocket Handler
    '''

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}
    
    def open(self):
        if self not in iofun:
            iofun.append(self)

    def on_close(self):
        if self in iofun:
            iofun.remove(self)

def ws_send(message):
    '''
        Websocket send message
    '''
    for ws in iofun:
        if not ws.ws_connection.stream.socket:
            logging.error("Web socket does not exist anymore!!!")
            iofun.remove(ws)
        else:
            ws.write_message(message)
    
    if not iofun:
        pass
        # logging.info('there are no ws connections at this time')

@gen.coroutine
def periodic_ws_send():
    '''
        Periodic websocket send
    '''
    hb_time = arrow.utcnow()
    heartbeat = {"heartbeat":{"time":hb_time.timestamp, "info": "periodic_ws_send"}}
    message = json.dumps({'message':heartbeat})
    ws_send(message)

def main():
    '''
        Overlords allow control of additional CPU and GPU units.

        Overlords provide control for your cloud forest. 
        As your forces grow in number, you must spawn more Overlords to control them.
    '''
    # daemon options
    opts = options.options()

    @gen.coroutine
    def email_notifications():
        key = opts.mailgun_key
        url = opts.mailgun_api_url

        results = yield [
            periodic.consume_alert_callback(db, key, url)
        ]
        raise gen.Return(results)

    # Set document database
    # document = motor.MotorClient(opts.mongo_host, opts.mongo_port).overlord

    # Set memcached backend
    memcache = mc.Client(
        [opts.memcached_host],
        binary=opts.memcached_binary,
        behaviors={
            "tcp_nodelay": opts.memcached_tcp_nodelay,
            "ketama": opts.memcached_ketama
        }
    )

    # Set SQL URI
    postgresql_uri = queries.uri(
        host=opts.sql_host,
        port=opts.sql_port,
        dbname=opts.sql_database,
        user=opts.sql_user,
        password=None
    )

    # Set kvalue database
    global kvalue
    kvalue = kvalue

    # Set default cache
    global cache
    cache = memcache

    # Set SQL session
    global sql
    sql = queries.TornadoSession(uri=postgresql_uri)

    # Set default database
    global db
    db = document

    # logging system spawned
    logging.info('Overlord system {0} spawned'.format(uuid.uuid4()))

    # logging database hosts
    logging.info('MongoDB server: {0}:{1}'.format(opts.mongo_host, opts.mongo_port))
    logging.info('PostgreSQL server: {0}:{1}'.format(opts.sql_host, opts.sql_port))

    # Ensure 
    if opts.ensure_indexes:
        logging.info('Ensuring indexes...')
        indexes.ensure_indexes(db)
        logging.info('DONE.')

    # base url
    base_url = opts.base_url

    # system cache
    cache_enabled = opts.cache_enabled
    if cache_enabled:
        logging.info('Memcached server: {0}:{1}'.format(opts.memcached_host, opts.memcached_port))

    # overlord web application daemon
    application = web.Application(

        [
            # Overlord system knowledge (quotes) and realtime events.
            (r'/tree/?', OverlordHandler),

            # experiment with WS
            (r'/ws/alerts', OverlordWSHandler),

            # Imps resource
            (r'/imps/(?P<imp_uuid>.+)/?', imps.Handler),
            (r'/imps/?', imps.Handler),

            # Nodes resource
            (r'/nodes/(?P<node_uuid>.+)/?', nodes.Handler),
            (r'/nodes/?', nodes.Handler)
            
        ],

        # system database
        db=db,

        # system cache
        cache=cache,

        # cache enabled flag
        cache_enabled=cache_enabled,

        # document datastorage
        document=document,

        # kvalue datastorage
        kvalue=kvalue,

        # sql datastorage
        sql=sql,

        # debug mode
        debug=opts.debug,

        # application domain
        domain=opts.domain,

        # application timezone
        timezone=opts.timezone,

        # pagination page size
        page_size=opts.page_size,

        # cookie settings
        cookie_secret=opts.cookie_secret,

        # login url
        login_url='/login/'
    )
    # Overlord periodic cast callbacks
    #check_alerts = PeriodicCast(email_notifications, 3000)
    #check_alerts.start()

    #periodic_ws = PeriodicCast(periodic_ws_send, 3000)
    #periodic_ws.start()

    # Setting up overlord processor
    application.listen(opts.port)
    logging.info('Listening on http://%s:%s' % (opts.host, opts.port))
    loop = ioloop.IOLoop.instance()

    # Process heartbeat SUB/PUB
    #loop.add_callback(subscriber)
    #loop.add_callback(publisher, opts.overlord_host)

    loop.start()


if __name__ == '__main__':
    main()