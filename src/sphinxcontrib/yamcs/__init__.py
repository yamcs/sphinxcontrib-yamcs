from sphinxcontrib.yamcs import lexers
from sphinxcontrib.yamcs.options import OptionsDirective
from sphinxcontrib.yamcs.proto import (
    ProtoDirective,
    RouteDirective,
    RPCDirective,
    ServiceDirective,
    WebSocketDirective,
)
from sphinxcontrib.yamcs.protoparse import ProtoParser


def parse_protobin(app, env, docnames):
    if app.config.yamcs_protobin:
        with open(app.config.yamcs_protobin, "rb") as f:
            data = f.read()

        env.protoparser = ProtoParser(data)


def setup(app):
    app.add_config_value("yamcs_protobin", None, "env")

    app.add_directive("options", OptionsDirective)
    app.add_directive("proto", ProtoDirective)
    app.add_directive("rpc", RPCDirective)
    app.add_directive("route", RouteDirective)
    app.add_directive("service", ServiceDirective)
    app.add_directive("websocket", WebSocketDirective)

    app.add_lexer("uritemplate", lexers.URITemplateLexer)
    app.add_lexer("urivariable", lexers.URIVariableLexer)

    app.connect("env-before-read-docs", parse_protobin)
