index = r"""{{ title | heading(1) }}

.. toctree::
    :maxdepth: 1
    :titlesonly:

{%- if additional_docs %}
{% for additional_doc in additional_docs %}
    {{ additional_doc }}
{%- endfor %}

.. toctree::
    :maxdepth: 1
    :titlesonly:
    :caption: Methods

{% for link in service_links %}
    {{ link }}
{%- endfor %}

{% for link in method_links %}
    {{ link }}
{%- endfor %}


{% else %}
{%- for link in service_links %}
    {{ link }}
{%- endfor %}

{% for link in method_links %}
    {{ link }}
{%- endfor %}


{% endif %}
"""


route = r"""{{ method.name | titlecase | heading(1) }}

.. route:: {{ symbol }}

{% if route_options.HasField('body') -%}
.. rubric:: Request Body
.. rpc:: {{ symbol }}
    :input:
{%- endif %}

{% if method.output_type not in ('.google.protobuf.Empty', '.yamcs.api.HttpBody') -%}
.. rubric:: Response Type
.. rpc:: {{ symbol }}
    :output:
{%- endif %}

{% if has_related -%}
.. rubric:: Related Types
.. rpc:: {{ symbol }}
    :related:
{%- endif %}
"""


service = r"""{{ service.name | titlecase | replace(' Api', '') | heading(1) }}

.. service:: {{ symbol }}

.. toctree::
    :maxdepth: 1
    :caption: Methods
{% for method in service.method %}
    {{ method.name | slug }}
{%- endfor %}
"""


websocket = r"""{{ method.name | titlecase | heading(1) }}

.. websocket:: {{ symbol }}

.. rubric:: WebSocket

This method requires to upgrade an HTTP connection to WebSocket. See details on `how Yamcs uses WebSocket <https://docs.yamcs.org/yamcs-http-api/websocket>`_.

Use the message type ``{{ websocket_options.topic }}``.

{% if method.client_streaming %}
This method supports client-streaming. The reply on the first message includes the call identifier assigned by Yamcs. Ensure to specify this call identifier on subsequent messages, or Yamcs will assume that you are making a new unrelated call.
{% endif %}


{% if method.input_type not in ('.google.protobuf.Empty', '.yamcs.api.HttpBody') -%}
.. rubric:: Input Type
.. rpc:: {{ symbol }}
    :input:
{%- endif %}

{% if method.output_type not in ('.yamcs.api.HttpBody') -%}
.. rubric:: Output Type
.. rpc:: {{ symbol }}
    :output:
{%- endif %}

{% if has_related -%}
.. rubric:: Related Types
.. rpc:: {{ symbol }}
    :related:
{%- endif %}
"""
