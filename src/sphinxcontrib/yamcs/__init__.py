import os
import shutil
from pathlib import Path

from sphinxcontrib.yamcs import autogen, lexers
from sphinxcontrib.yamcs.options import OptionsDirective
from sphinxcontrib.yamcs.proto import (
    ProtoDirective,
    RouteDirective,
    RPCDirective,
    ServiceDirective,
    WebSocketDirective,
)
from sphinxcontrib.yamcs.protoparse import ProtoParser


def config_inited(app, config):
    """
    Autogenerate GPB documents.
    """
    if config.yamcs_api_protobin:
        with open(config.yamcs_api_protobin, "rb") as f:
            data = f.read()

        parser = ProtoParser(data)
        destdir = Path(app.srcdir, app.config.yamcs_api_destdir)
        if destdir.exists():
            shutil.rmtree(destdir)
        destdir.mkdir()

        title = app.config.yamcs_api_title

        autogen.generate(parser, destdir, title)


def env_before_read_docs(app, env, docnames):
    """
    Cache a ProtoParser for use by any directives.
    """
    if app.config.yamcs_api_protobin:
        with open(app.config.yamcs_api_protobin, "rb") as f:
            data = f.read()

        env.protoparser = ProtoParser(data)


def setup(app):
    app.add_config_value("yamcs_api_protobin", None, "env")
    app.add_config_value("yamcs_api_destdir", "http-api", "env")
    app.add_config_value("yamcs_api_title", "HTTP API", "env")

    app.add_directive("options", OptionsDirective)
    app.add_directive("proto", ProtoDirective)
    app.add_directive("rpc", RPCDirective)
    app.add_directive("route", RouteDirective)
    app.add_directive("service", ServiceDirective)
    app.add_directive("websocket", WebSocketDirective)

    app.add_lexer("uritemplate", lexers.URITemplateLexer)
    app.add_lexer("urivariable", lexers.URIVariableLexer)

    app.connect("config-inited", config_inited)
    app.connect("env-before-read-docs", env_before_read_docs)
