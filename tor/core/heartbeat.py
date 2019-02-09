import logging

import cherrypy

from tor.core.config import config

conf = {
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [
            ('Content-Type', 'application/json')
        ],
    }
}


def configure_heartbeat(config):
    """
    Sets up and starts the cherrypy server that operates the json api endpoint
    for the heartbeat. Usage:

    >>> import requests
    >>> requests.get('http://localhost:{portnumber}').json()
    returns:
    {
        'bot_name': 'this_is_an_awesome_bot',
        'bot_version': '9001',
        'core_version': '0.2.0'
    }

    :param config: the global config object
    :return: None
    """

    # update the global config (separate from the application config above)
    cherrypy.config.update(
        {
            'server.socket_port': config.heartbeat_port
        }
    )
    logging.info(f'Heartbeat port: {config.heartbeat_port}')

    if config.heartbeat_logging is False:  # defaults to false
        # disable logging of hits from the heartbeat checker
        cherrypy.log.error_log.propagate = False
        cherrypy.log.access_log.propagate = False
        cherrypy.log.screen = None

    # segment out the starting logic so that it only fires if we configure it
    # instead of starting on file load as normal
    start_heartbeat_server()


@cherrypy.expose
class heartbeat(object):
    @cherrypy.tools.json_out()
    def GET(self):
        return {
            'bot_name': config.name,
            'bot_version': config.bot_version,
            'core_version': config.core_version,
        }


def start_heartbeat_server():
    """
    Starts the cherrypy heartbeat server. Do not call directly; use
    configure_heartbeat() instead.

    :return: None
    """
    cherrypy.tree.mount(heartbeat(), '/', conf)
    cherrypy.server.socket_host = "127.0.0.1"
    cherrypy.engine.start()
    logging.info('Cherrypy heartbeat started!')


def stop_heartbeat_server():
    """
    Stops the cherrypy heartbeat server. I guess you can call this one
    directly if you need to, but I recommend using
    tor_core.helpers.stop_heartbeat() instead, since any other items relevant
    to shutting down the heartbeat will go there.

    :return: None
    """
    cherrypy.engine.exit()
