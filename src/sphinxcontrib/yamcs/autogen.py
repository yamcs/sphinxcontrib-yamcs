import os
import re
from pathlib import Path

from sphinx.util.osutil import FileAvoidWrite
from sphinx.util.template import ReSTRenderer
from sphinxcontrib.yamcs import templates

from yamcs.api import annotations_pb2


def camel_to_slug(name, sep="-", lower=True):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1" + sep + r"\2", name)
    name = re.sub("([a-z0-9])([A-Z])", r"\1" + sep + r"\2", name)
    return name.lower() if lower else name


def titlecase(text):
    return camel_to_slug(text, sep=" ", lower=False)


def replace(a, b, c):
    return a.replace(b, c)


class YamcsReSTRenderer(ReSTRenderer):
    def __init__(self):
        super().__init__()
        self.env.filters["slug"] = camel_to_slug
        self.env.filters["replace"] = replace
        self.env.filters["titlecase"] = titlecase


def create_service_file(symbol, service, filename):
    context = {
        "symbol": symbol,
        "service": service,
    }
    text = YamcsReSTRenderer().render_string(templates.service, context)
    with FileAvoidWrite(filename) as f:
        f.write(text)


def create_route_file(symbol, method, filename, has_related):
    context = {
        "symbol": symbol,
        "method": method,
        "has_related": has_related,
        "route_options": method.options.Extensions[annotations_pb2.route],
    }
    text = YamcsReSTRenderer().render_string(templates.route, context)
    with FileAvoidWrite(filename) as f:
        f.write(text)


def create_websocket_file(symbol, method, filename, has_related):
    context = {
        "symbol": symbol,
        "method": method,
        "has_related": has_related,
        "websocket_options": method.options.Extensions[annotations_pb2.websocket],
    }
    text = YamcsReSTRenderer().render_string(templates.websocket, context)
    with FileAvoidWrite(filename) as f:
        f.write(text)


def generate(parser, destdir, title, additional_docs):
    service_count = 0
    for file in parser.proto.file:
        service_count += len(file.service)

    service_links = []
    method_links = []
    generated_files = []
    for file in parser.proto.file:
        for service in file.service:
            if service_count > 1:
                servicedirname = camel_to_slug(service.name).replace("-api", "")
                servicedir = Path(destdir, servicedirname)
                servicedir.mkdir(exist_ok=True)
                generated_files.append(servicedirname)

                servicefile = os.path.join(servicedir, "index.rst")
                symbol = "." + file.package + "." + service.name
                create_service_file(symbol, service, servicefile)
                service_links.append(servicedir.name + "/index")

                for method in service.method:
                    filename = camel_to_slug(method.name) + ".rst"
                    methodfile = os.path.join(servicedir, filename)
                    symbol = "." + file.package + "." + service.name + "." + method.name
                    related_types = parser.find_types_related_to_method(symbol)
                    related_enums = parser.find_enums_related_to_method(symbol)
                    has_related = len(related_types) > 0 or len(related_enums) > 0

                    if method.options.HasExtension(annotations_pb2.route):
                        create_route_file(symbol, method, methodfile, has_related)
                    elif method.options.HasExtension(annotations_pb2.websocket):
                        create_websocket_file(symbol, method, methodfile, has_related)
            else:
                for method in service.method:
                    filename = camel_to_slug(method.name) + ".rst"
                    methodfile = Path(destdir, filename)
                    symbol = "." + file.package + "." + service.name + "." + method.name
                    related_types = parser.find_types_related_to_method(symbol)
                    related_enums = parser.find_enums_related_to_method(symbol)
                    has_related = len(related_types) > 0 or len(related_enums) > 0
                    method_links.append(camel_to_slug(method.name))

                    if method.options.HasExtension(annotations_pb2.route):
                        create_route_file(symbol, method, methodfile, has_related)
                        generated_files.append(filename)
                    elif method.options.HasExtension(annotations_pb2.websocket):
                        create_websocket_file(symbol, method, methodfile, has_related)
                        generated_files.append(filename)

    service_links.sort()
    text = YamcsReSTRenderer().render_string(
        templates.index,
        {
            "title": title,
            "additional_docs": additional_docs,
            "service_links": service_links,
            "method_links": method_links,
        },
    )
    indexfile = os.path.join(destdir, "index.rst")
    with FileAvoidWrite(indexfile) as f:
        f.write(text)
    generated_files.append("index.rst")

    with Path(destdir, ".autogen").open("w") as f:
        for file in generated_files:
            f.write(file)
            f.write("\n")
