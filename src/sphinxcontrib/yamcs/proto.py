import re
from dataclasses import dataclass

from docutils import nodes
from docutils.core import publish_doctree
from docutils.parsers import get_parser_class
from docutils.statemachine import ViewList
from docutils.utils import new_document
from sphinx.directives.code import CodeBlock
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles
from yamcs.api import annotations_pb2

MystParser = get_parser_class("myst")


class ProtoDirective(CodeBlock):
    required_arguments = 1

    def __init__(self, *args, **kwargs):
        super(ProtoDirective, self).__init__(*args, **kwargs)
        symbol = self.arguments[0]
        self.arguments = ["typescript"]
        parser = self.env.protoparser
        self.content = [parser.describe_message(symbol)]


def get_uri_templates_for_method_descriptor(descriptor):
    route = descriptor.options.Extensions[annotations_pb2.route]
    uri_templates = [get_uri_template_for_route(route)]
    for route in route.additional_bindings:
        if not route.deprecated:
            uri_templates.append(get_uri_template_for_route(route))
    return uri_templates


def get_route_for_method_descriptor(descriptor, addmethod=True):
    route_options = descriptor.options.Extensions[annotations_pb2.route]
    return get_uri_template_for_route(route_options, addmethod=addmethod)


def get_uri_template_for_route(route, addmethod=True):
    if route.HasField("post"):
        return "POST " + route.post if addmethod else route.post
    if route.HasField("get"):
        return "GET " + route.get if addmethod else route.get
    if route.HasField("delete"):
        return "DELETE " + route.delete if addmethod else route.delete
    if route.HasField("put"):
        return "PUT " + route.put if addmethod else route.put
    if route.HasField("patch"):
        return "PATCH " + route.patch if addmethod else route.patch
    return None


@dataclass
class RouteParam:
    template: str
    param: str
    star: bool
    optional: bool


def simplify_uri_template(uri_template):
    """
    Removes ?, *, ** symbols from route parameters
    """
    return uri_template.replace("?}", "}").replace("**}", "}").replace("*}", "}")


def get_route_params(uri_template):
    params = []
    for match in re.finditer(r"\{([^\}\*\?]*)([\*\?]*)\}", uri_template):
        params.append(
            RouteParam(
                template=match.group(0),
                param=match.group(1),
                star=match.group(2) in ("*", "**"),
                optional=match.group(2) in ("?", "**"),
            )
        )

    return params


class RPCDirective(CodeBlock):
    required_arguments = 1
    own_option_spec = dict(input=bool, output=bool, related=bool)

    option_spec = CodeBlock.option_spec.copy()
    option_spec.update(own_option_spec)

    def __init__(self, *args, **kwargs):
        super(RPCDirective, self).__init__(*args, **kwargs)
        symbol = self.arguments[0]
        self.arguments = ["typescript"]

        parser = self.env.protoparser
        descriptor = parser.descriptors_by_symbol[symbol]
        body_symbol = parser.get_body_symbol(descriptor)

        self.content = []
        if "input" in self.options:
            if body_symbol == ".google.protobuf.Struct":
                self.content.append("{[key: string]: any}")
            else:
                excluded_fields = []

                if descriptor.options.HasExtension(annotations_pb2.route):
                    route = get_route_for_method_descriptor(descriptor)
                    # Remove route params from the message. Transcoding
                    # fetches them from the URL directly
                    excluded_fields += [p.param for p in get_route_params(route)]

                # Check if there's actually any body fields
                body_descriptor = parser.descriptors_by_symbol[body_symbol]
                body_fields = [
                    f
                    for f in body_descriptor.field
                    if f.json_name not in excluded_fields
                ]

                if body_fields:
                    self.content.append(
                        parser.describe_message(
                            body_symbol,
                            excluded_fields=excluded_fields,
                        )
                    )
                else:
                    self.content.append("// Not applicable")

        if "output" in self.options:
            if body_symbol == ".google.protobuf.Struct":
                self.content.append("{[key: string]: any}")
            else:
                self.content.append(parser.describe_message(descriptor.output_type))

        if "related" in self.options:
            for related_type in parser.find_types_related_to_method(symbol):
                self.content.append(parser.describe_message(related_type))
            for related_enum in parser.find_enums_related_to_method(symbol):
                self.content.append(parser.describe_enum(related_enum))


def produce_nodes(state, text, markdown):
    if markdown:
        return produce_nodes_from_md(state, text)
    else:
        return produce_nodes_from_rst(state, text)


def produce_nodes_from_md(state, md_text):
    settings = state.document.settings
    document = new_document("<markdown-input>", settings)
    parser = MystParser()
    parser.parse(md_text, document)
    return list(document.children)


def produce_nodes_from_rst(state, rst_text):
    # Deindent small indents to not trigger unwanted rst
    # blockquotes. This uses a simple algorithm that only
    # keeps indents in multiples of 2.
    deindented = []
    for line in rst_text.splitlines():
        indent_size = len(line) - len(line.lstrip())
        allowed_indent = int(indent_size / 2) * "  "
        deindented.append(allowed_indent + line.lstrip())

    unprocessed = ViewList()
    for line in deindented:
        unprocessed.append(line, "fakefile.rst", 1)

    temp_node = nodes.section()
    temp_node.document = state.document
    nested_parse_with_titles(state, unprocessed, temp_node)
    return [node for node in temp_node.children]


class WebSocketDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        result = []
        symbol = self.arguments[0]
        parser = self.env.protoparser
        descriptor = parser.descriptors_by_symbol[symbol]

        # From the service, determine if we are to read Markdown
        service_symbol = symbol.rsplit(".", 1)[0]
        service_descriptor = parser.descriptors_by_symbol[service_symbol]
        markdown = service_descriptor.options.Extensions[annotations_pb2.markdown]

        comment = parser.find_comment(symbol, prefix="")
        if comment:
            result += produce_nodes(self.state, comment, markdown)

        return result


class ServiceDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        result = []
        symbol = self.arguments[0]
        parser = self.env.protoparser
        descriptor = parser.descriptors_by_symbol[symbol]

        markdown = descriptor.options.Extensions[annotations_pb2.markdown]

        comment = parser.find_comment(symbol, prefix="")
        if comment:
            result += produce_nodes(self.state, comment, markdown)

        return result


class RouteDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        result = []
        symbol = self.arguments[0]
        parser = self.env.protoparser
        descriptor = parser.descriptors_by_symbol[symbol]

        # From the service, determine if we are to read Markdown
        service_symbol = symbol.rsplit(".", 1)[0]
        service_descriptor = parser.descriptors_by_symbol[service_symbol]
        markdown = service_descriptor.options.Extensions[annotations_pb2.markdown]

        comment = parser.find_comment(symbol, prefix="")
        if comment:
            result += produce_nodes(self.state, comment, markdown)

        if descriptor.client_streaming:
            text = "This method uses client-streaming."
            result.append(
                nodes.warning(
                    "",
                    nodes.paragraph("", "", nodes.Text(text)),
                )
            )

        if descriptor.server_streaming:
            text = (
                "This method uses server-streaming. "
                + "Yamcs sends an unspecified amount of data "
                + "using chunked transfer encoding."
            )
            result.append(
                nodes.warning(
                    "",
                    nodes.paragraph("", "", nodes.Text(text)),
                )
            )

        route_options = descriptor.options.Extensions[annotations_pb2.route]

        raw = ".. rubric:: URI Template\n"
        uri_templates = get_uri_templates_for_method_descriptor(descriptor)
        for idx, uri_template in enumerate(uri_templates):
            if idx > 0:
                raw += "\n\n"
            raw += ".. code-block:: uritemplate\n\n"
            raw += "    " + simplify_uri_template(uri_template) + "\n\n"

        result += produce_nodes_from_rst(self.state, raw)

        input_descriptor = parser.descriptors_by_symbol[descriptor.input_type]

        route_text = uri_templates[0]
        route_params = get_route_params(route_text)
        if route_params:
            dl_items = []
            for route_param in route_params:
                comment_node = nodes.section()
                comment = (
                    parser.find_comment(
                        descriptor.input_type + "." + route_param.param, prefix=""
                    )
                    or ""
                )
                if comment:
                    for child in produce_nodes(self.state, comment, markdown):
                        comment_node += child

                    if route_param.star:
                        comment_node += produce_nodes_from_rst(
                            self.state,
                            "This route parameter may contain forward slashes. Alternatively "
                            r"you may also use URL-encoded characters, such as ``%2F``",
                        )

                dl_items.append(
                    nodes.definition_list_item(
                        "",
                        nodes.term("", "", nodes.literal("", route_param.param)),
                        nodes.definition("", comment_node),
                    )
                )

            result += [nodes.definition_list("", *dl_items)]

        if route_options.get:
            query_param_fields = []
            for field in input_descriptor.field:
                if field.json_name not in [p.param for p in route_params]:
                    query_param_fields.append(field)

            if query_param_fields:
                dl_items = []
                for field in query_param_fields:
                    field_symbol = descriptor.input_type + "." + field.name

                    comment_node = nodes.section()
                    comment = parser.find_comment(field_symbol, prefix="")
                    if comment:
                        for child in produce_nodes(self.state, comment, markdown):
                            comment_node += child

                    dl_items.append(
                        nodes.definition_list_item(
                            "",
                            nodes.term("", "", nodes.literal("", field.json_name)),
                            nodes.definition("", comment_node),
                        )
                    )
                result += [
                    nodes.rubric("", "Query Parameters"),
                    nodes.definition_list("", *dl_items),
                ]

        return result
