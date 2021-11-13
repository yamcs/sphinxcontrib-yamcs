import re

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.directives.code import CodeBlock
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from yamcs.api import annotations_pb2


class ProtoDirective(CodeBlock):
    required_arguments = 1

    def __init__(self, *args, **kwargs):
        super(ProtoDirective, self).__init__(*args, **kwargs)
        symbol = self.arguments[0]
        self.arguments = ["typescript"]
        parser = self.env.protoparser
        self.content = [parser.describe_message(symbol)]


def get_route_for_method_descriptor(descriptor, addmethod=True):
    route_options = descriptor.options.Extensions[annotations_pb2.route]
    if route_options.HasField("post"):
        return "POST " + route_options.post if addmethod else route_options.post
    if route_options.HasField("get"):
        return "GET " + route_options.get if addmethod else route_options.get
    if route_options.HasField("delete"):
        return "DELETE " + route_options.delete if addmethod else route_options.delete
    if route_options.HasField("put"):
        return "PUT " + route_options.put if addmethod else route_options.put
    if route_options.HasField("patch"):
        return "PATCH " + route_options.patch if addmethod else route_options.patch
    return None


def get_route_param_template(uri_template, param):
    return re.search(r"(\{" + param + r"[\*\?]*\})", uri_template).group(1)


def get_route_params(uri_template):
    return [p for p in re.findall(r"\{([^\}\*\?]*)[\*\?]*\}", uri_template)]


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
            excluded_fields = []

            if descriptor.options.HasExtension(annotations_pb2.route):
                route = get_route_for_method_descriptor(descriptor)
                # Remove route params from the message. Transcoding
                # fetches them from the URL directly
                excluded_fields += get_route_params(route)

            self.content.append(
                parser.describe_message(
                    body_symbol,
                    excluded_fields=excluded_fields,
                )
            )
        if "output" in self.options:
            self.content.append(parser.describe_message(descriptor.output_type))
        if "related" in self.options:
            for related_type in parser.find_types_related_to_method(symbol):
                self.content.append(parser.describe_message(related_type))
            for related_enum in parser.find_enums_related_to_method(symbol):
                self.content.append(parser.describe_enum(related_enum))


def produce_nodes(state, rst_text):
    # Deindent small indents to not trigger unwanted rst
    # blockquotes. This uses a simple algorithm that only
    # keeps indents in multiples of 4.
    deindented = []
    for line in rst_text.splitlines():
        indent_size = len(line) - len(line.lstrip())
        allowed_indent = int(indent_size / 4) * "    "
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

        comment = parser.find_comment(symbol, prefix="")
        if comment:
            result += produce_nodes(self.state, comment)

        return result


class ServiceDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        result = []
        symbol = self.arguments[0]
        parser = self.env.protoparser
        descriptor = parser.descriptors_by_symbol[symbol]

        comment = parser.find_comment(symbol, prefix="")
        if comment:
            result += produce_nodes(self.state, comment)

        return result


class RouteDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        result = []
        symbol = self.arguments[0]
        parser = self.env.protoparser
        descriptor = parser.descriptors_by_symbol[symbol]

        comment = parser.find_comment(symbol, prefix="")
        if comment:
            result += produce_nodes(self.state, comment)

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
        route_text = get_route_for_method_descriptor(descriptor)

        raw = ".. rubric:: URI Template\n"
        raw += ".. code-block:: uritemplate\n\n"
        raw += "    " + route_text + "\n"

        result += produce_nodes(self.state, raw)

        input_descriptor = parser.descriptors_by_symbol[descriptor.input_type]

        route_params = get_route_params(route_text)
        if route_params:
            dl_items = []
            for param in route_params:
                param_template = get_route_param_template(route_text, param)
                comment = (
                    parser.find_comment(descriptor.input_type + "." + param, prefix="")
                    or ""
                )

                dl_items.append(
                    nodes.definition_list_item(
                        "",
                        nodes.term("", "", nodes.literal("", param_template)),
                        nodes.definition("", nodes.paragraph(text=comment)),
                    )
                )

            result += [nodes.definition_list("", *dl_items)]

        if route_options.get:
            query_param_fields = []
            for field in input_descriptor.field:
                if field.json_name not in route_params:
                    query_param_fields.append(field)

            if query_param_fields:
                dl_items = []
                for field in query_param_fields:
                    field_symbol = descriptor.input_type + "." + field.name

                    comment_node = nodes.section()
                    comment = parser.find_comment(field_symbol, prefix="")
                    if comment:
                        for child in produce_nodes(self.state, comment):
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
