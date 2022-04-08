from google.protobuf import descriptor_pb2

from yamcs.api import annotations_pb2

DEFAULT_EXCLUDES = [
    ".google.protobuf.Duration",
    ".google.protobuf.Struct",
    ".google.protobuf.Timestamp",
    ".yamcs.api.HttpBody",
]


def path_to_symbol(file, path):
    items = iter(path)
    relto = file
    reltype = "file"
    symbol = "." + file.package
    for item in items:
        if reltype == "file":
            if item == 4:  # Message
                idx = next(items)
                reltype, relto = "message", relto.message_type[idx]
                symbol += "." + relto.name
            elif item == 5:  # Enum
                idx = next(items)
                reltype, relto = "enum", relto.enum_type[idx]
                symbol += "." + relto.name
            elif item == 6:  # Service
                idx = next(items)
                reltype, relto = "service", relto.service[idx]
                symbol += "." + relto.name
            elif item == 8:  # FileOptions
                pass
            elif item == 9:  # SourceCodeInfo
                pass
            else:
                raise Exception("Unexpected item {}".format(item))
        elif reltype == "message":
            if item == 1:  # Name
                pass
            elif item == 2:  # Field
                idx = next(items)
                reltype, relto = "field", relto.field[idx]
                symbol += "." + relto.name
            elif item == 3:  # Nested Type
                idx = next(items)
                reltype, relto = "message", relto.nested_type[idx]
                symbol += "." + relto.name
            elif item == 4:  # Enum
                idx = next(items)
                reltype, relto = "enum", relto.enum_type[idx]
                symbol += "." + relto.name
            elif item == 5:  # Extension Range
                pass
            elif item == 8:  # Oneof
                idx = next(items)
                reltype, relto = "oneof", relto.oneof_decl[idx]
                symbol += "." + relto.name
            else:
                raise Exception("Unexpected item {}".format(item))
        elif reltype == "enum":
            if item == 2:  # Value
                idx = next(items)
                symbol += "." + relto.value[idx].name
            else:
                raise Exception("Unexpected item {}".format(item))
        elif reltype == "service":
            if item == 2:  # Method
                idx = next(items)
                symbol += "." + relto.method[idx].name
            else:
                raise Exception("Unexpected item {}".format(item))

    return symbol


class ProtoParser:
    descriptors_by_symbol = {}
    comments_by_symbol = {}
    package_by_symbol = {}

    def __init__(self, data):
        self.proto = descriptor_pb2.FileDescriptorSet()
        self.proto.ParseFromString(data)

        for file in self.proto.file:
            for service in file.service:
                symbol = ".{}.{}".format(file.package, service.name)
                self.descriptors_by_symbol[symbol] = service
                for method_type in service.method:
                    self.descriptors_by_symbol[
                        symbol + "." + method_type.name
                    ] = method_type

            for message_type in file.message_type:
                symbol = ".{}.{}".format(file.package, message_type.name)
                self.package_by_symbol[symbol] = file.package
                self.descriptors_by_symbol[symbol] = message_type
                for enum_type in message_type.enum_type:
                    self.package_by_symbol[symbol] = file.package
                    self.descriptors_by_symbol[
                        symbol + "." + enum_type.name
                    ] = enum_type
                for nested_type in message_type.nested_type:
                    self.package_by_symbol[symbol] = file.package
                    self.descriptors_by_symbol[
                        symbol + "." + nested_type.name
                    ] = nested_type

            for enum_type in file.enum_type:
                symbol = ".{}.{}".format(file.package, enum_type.name)
                self.package_by_symbol[symbol] = file.package
                self.descriptors_by_symbol[symbol] = enum_type

            for location in file.source_code_info.location:
                if location.HasField("leading_comments"):
                    symbol = path_to_symbol(file, location.path)
                    self.comments_by_symbol[symbol] = location.leading_comments.rstrip()

    def find_types_related_to_method(self, symbol):
        descriptor = self.descriptors_by_symbol[symbol]
        body_symbol = self.get_body_symbol(descriptor)
        return self.find_related_types(
            [
                body_symbol or descriptor.input_type,
                descriptor.output_type,
            ],
            DEFAULT_EXCLUDES[:],
        )

    def find_enums_related_to_method(self, symbol):
        descriptor = self.descriptors_by_symbol[symbol]
        body_symbol = self.get_body_symbol(descriptor)
        return self.find_related_enums(
            [
                body_symbol or descriptor.input_type,
                descriptor.output_type,
            ],
            DEFAULT_EXCLUDES[:],
        )

    def find_related_types(self, symbols, excluded_types):
        related_types = []
        excluded_types += symbols[:]
        for symbol in symbols:
            if symbol in DEFAULT_EXCLUDES:
                continue
            descriptor = self.descriptors_by_symbol[symbol]
            for field in descriptor.field:
                if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                    nested_type = self.descriptors_by_symbol[field.type_name]
                    if nested_type.options.map_entry:
                        continue

                    if field.type_name not in excluded_types:
                        related_types += [field.type_name]
                        related_types += self.find_related_types(
                            [field.type_name], excluded_types
                        )
        return related_types

    def find_related_enums(self, symbols, excluded_types):
        related_enums = []
        excluded_types += symbols[:]
        for symbol in symbols:
            if symbol in DEFAULT_EXCLUDES:
                continue
            descriptor = self.descriptors_by_symbol[symbol]
            for field in descriptor.field:
                if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
                    if field.type_name not in related_enums:
                        related_enums.append(field.type_name)
                elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                    if field.type_name not in excluded_types:
                        related_enums += self.find_related_enums(
                            [field.type_name], excluded_types
                        )
        return related_enums

    def get_body_symbol(self, method_descriptor):
        # Transcoding would promote the body field to the actual
        # expected request body. (The actual input_type is in this
        # case only used for query/route parameters).
        if method_descriptor.options.HasExtension(annotations_pb2.route):
            route_options = method_descriptor.options.Extensions[annotations_pb2.route]
            if route_options.HasField("body") and route_options.body != "*":
                input_descriptor = self.descriptors_by_symbol[
                    method_descriptor.input_type
                ]
                for field in input_descriptor.field:
                    if field.json_name == route_options.body:
                        return field.type_name

        return method_descriptor.input_type

    def find_comment(self, symbol, indent="", prefix="//"):
        if symbol in self.comments_by_symbol:
            comment = self.comments_by_symbol[symbol]
            buf = ""
            for line in comment.split("\n"):
                trimmed = line.rstrip()
                buf += indent + prefix + trimmed + "\n"
            return buf
        return None

    def describe_enum(self, symbol, indent=""):
        descriptor = self.descriptors_by_symbol[symbol]
        buf = indent + "enum " + descriptor.name + " {\n"
        for value in descriptor.value:
            comment = self.find_comment(symbol + "." + value.name, indent=indent + "  ")
            if comment:
                buf += "\n"
                buf += comment
            buf += indent + "  " + value.name + ' = "' + value.name + '",\n'
        buf += indent + "}\n"
        return buf

    def describe_field_type(self, field):
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_BOOL:
            return "boolean"
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_BYTES:
            return "string"  # Base64
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE:
            return "number"
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            return self.message_name(field.type_name)
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT:
            return "number"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_INT32:
            return "number"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_INT64:
            return "string"  # Decimal string
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
            nested_type = self.descriptors_by_symbol[field.type_name]
            if nested_type.options.map_entry:
                key_type = self.describe_field_type(nested_type.field[0])
                value_type = self.describe_field_type(nested_type.field[1])
                return "{[key: " + key_type + "]: " + value_type + "}"
            if field.type_name == ".google.protobuf.Duration":
                return "string"
            elif field.type_name == ".google.protobuf.Timestamp":
                return "string"
            elif field.type_name == ".google.protobuf.Struct":
                return "{[key: string]: any}"
            else:
                return self.message_name(field.type_name)
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_SINT32:
            return "number"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_SINT64:
            return "string"  # Decimal string
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_STRING:
            return "string"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_UINT32:
            return "number"
        elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_UINT64:
            return "string"  # Decimal string
        else:
            raise Exception("Unexpected field type {}".format(field.type))

    def describe_message(self, symbol, indent="", related=False, excluded_fields=None):
        descriptor = self.descriptors_by_symbol[symbol]
        buf = ""

        comment = self.find_comment(symbol, indent=indent)
        if comment:
            buf += comment

        buf += "interface " + descriptor.name + " {\n"
        for field in descriptor.field:
            if field.json_name in (excluded_fields or []):
                continue

            comment = self.find_comment(symbol + "." + field.name, indent=indent + "  ")
            if comment:
                buf += "\n"
                buf += comment
            buf += indent + "  " + field.json_name + ": "
            buf += self.describe_field_type(field)

            is_array = field.label == field.LABEL_REPEATED

            if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                nested_type = self.descriptors_by_symbol[field.type_name]
                if nested_type.options.map_entry:
                    value_field = nested_type.field[1]
                    is_array = False

            if is_array:
                buf += "[]"

            buf += ";"

            if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_BYTES:
                buf += "  // Base64"
            elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                if field.type_name == ".google.protobuf.Timestamp":
                    buf += "  // RFC 3339 timestamp"
                elif field.type_name == ".google.protobuf.Duration":
                    buf += " // Duration in seconds. Example: \"3s\" or \"3.001s\""
            elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_INT64:
                buf += "  // String decimal"
            elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_UINT64:
                buf += "  // String decimal"
            elif field.type == descriptor_pb2.FieldDescriptorProto.TYPE_SINT64:
                buf += "  // String decimal"

            buf += "\n"
        buf += "}\n"
        return buf

    def message_name(self, symbol):
        return symbol[symbol.rfind(".") + 1 :]
