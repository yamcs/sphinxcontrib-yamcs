import yaml
from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles


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


class OptionsDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        result = []
        yaml_file = self.arguments[0]
        with open(yaml_file) as f:
            descriptor = yaml.load(f, Loader=yaml.FullLoader)
            options = descriptor["options"].items()
            head = []
            tail = []
            self.generate_nodes(options, head=head, tail=tail)
            result += head + tail
        return result

    def generate_nodes(self, options, head, tail):
        head_items = []
        for option_name, option in options:
            type_string = option["type"]
            if option["type"] == "LIST":
                type_string += " of " + option["elementType"] + "s"
            elif option["type"] == "LIST_OR_ELEMENT":
                type_string = (
                    option["elementType"] + " or list of " + option["elementType"] + "s"
                )

            term_nodes = [
                nodes.literal("", option_name),
                nodes.Text(" ("),
                nodes.Text(type_string.lower()),
                nodes.Text(")"),
            ]

            definition_nodes = []

            if "deprecationMessage" in option:
                continue

            if "description" in option:
                for idx, para in enumerate(option["description"]):
                    para_nodes = []
                    if idx == 0 and option.get("required", False):
                        para_nodes.append(nodes.strong("", "Required."))
                        para_nodes.append(nodes.Text(" "))
                    para_nodes.append(nodes.Text(para))
                    definition_nodes.append(nodes.paragraph("", "", *para_nodes))

            if "choices" in option:
                choices = option["choices"]
                para_nodes = [nodes.Text("One of ")]
                for idx, choice in enumerate(choices):
                    if idx == 0:
                        para_nodes += [nodes.literal("", str(choice))]
                    elif idx < len(choices) - 1:
                        para_nodes += [nodes.Text(", "), nodes.literal("", str(choice))]
                    else:
                        para_nodes += [
                            nodes.Text(" or "),
                            nodes.literal("", str(choice)),
                        ]
                definition_nodes.append(nodes.paragraph("", "", *para_nodes))

            if "default" in option:
                default_value = option["default"]
                if option["type"] == "BOOLEAN":  # True, False ==> true, false
                    default_value = str(default_value).lower()
                default_nodes = [
                    nodes.Text("Default: "),
                    nodes.literal("", default_value),
                ]
                definition_nodes.append(nodes.paragraph("", "", *default_nodes))

            if option["type"] == "MAP":
                title = option.get("title", option_name) + " sub-configuration"
                definition_nodes.append(
                    nodes.paragraph(text='See "' + title + '" section below.')
                )
                tail += [nodes.rubric("", title)]
                new_tail = []
                self.generate_nodes(
                    option["suboptions"].items(), head=tail, tail=new_tail
                )
                tail += new_tail

            if option["type"] == "LIST" or option["type"] == "LIST_OR_ELEMENT":
                if option["elementType"] == "MAP":
                    title = option.get("title", option_name) + " sub-configuration"
                    definition_nodes.append(
                        nodes.paragraph(text='See "' + title + '" section below.')
                    )
                    tail += [nodes.rubric("", title)]
                    new_tail = []
                    self.generate_nodes(
                        option["suboptions"].items(), head=tail, tail=new_tail
                    )
                    tail += new_tail

            head_items.append(
                nodes.definition_list_item(
                    "",
                    nodes.term("", "", *term_nodes),
                    nodes.definition("", *definition_nodes),
                )
            )
        head += [nodes.definition_list("", *head_items)]
