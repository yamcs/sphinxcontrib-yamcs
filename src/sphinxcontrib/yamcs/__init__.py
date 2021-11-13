from sphinxcontrib.yamcs import lexers
from sphinxcontrib.yamcs.options import OptionsDirective


def setup(app):
    app.add_directive("options", OptionsDirective)

    app.add_lexer("uritemplate", lexers.URITemplateLexer)
    app.add_lexer("urivariable", lexers.URIVariableLexer)
