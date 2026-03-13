# Copyright 2023 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Parse Python module files and extract Odoo data models from them."""

import pathlib
import typing

from tree_sitter import Node

from . import treesitter_utils as ts_utils

BASE_CLASSES = [
    "AbstractModel",
    "BaseModel",
    "Model",
    "TransientModel",
]

FIELD_TYPES = [
    "Binary",
    "Boolean",
    "Char",
    "Date",
    "Datetime",
    "Float",
    "Html",
    "Id",
    "Image",
    "Integer",
    "Json",
    "Many2one",
    "Many2oneReference",
    "Many2many",
    "Monetary",
    "One2many",
    "Properties",
    "PropertiesDefinition",
    "Reference",
    "Selection",
    "Text",
    # Extra fields
    "Serialized",  # base_sparse_field from odoo
    "Many2manyCustom",  # base_m2m_custom_field from OCA
]


class PyFile:
    """Python module file.

    Such file could contain Odoo model definitions.
    """

    def __init__(self, path: pathlib.Path, module_path: pathlib.Path = None):
        self.path = path
        self.module_path = module_path
        self.lines, self.tree = self._parse_file()
        self.models = self._get_models()

    def _parse_file(self):
        try:
            with open(self.path, "rb") as file_:
                content = file_.read()
            lines = content.decode("utf-8").split("\n")
            parser = ts_utils.get_parser()
            tree = parser.parse(content)
            return lines, tree
        except Exception as exc:
            raise RuntimeError(f"Unable to parse file {self.path}") from exc

    def _get_models(self) -> dict:
        models = {}
        root_node = self.tree.root_node

        for class_node in ts_utils.find_class_definitions(root_node):
            try:
                if OdooModel.is_model(class_node):
                    model = OdooModel(self, class_node)
                    # Support corner case where the same data model is
                    # declared/inherited multiple times in the same file
                    # (each of them will add a new model definition entry).
                    class_name = ts_utils.get_class_name(class_node)
                    lineno = class_node.start_point[0] + 1
                    key = f"{self.path}:{class_name}:{lineno}"
                    models[key] = model.to_dict()
                elif OdooModel.is_base_class(class_node):
                    model = OdooModel(self, class_node)
                    class_name = ts_utils.get_class_name(class_node)
                    models[class_name] = model.to_dict()
            except Exception as exc:
                class_name = ts_utils.get_class_name(class_node) or "unknown"
                lineno = class_node.start_point[0] + 1
                raise RuntimeError(
                    f"Unable to parse class {class_name}:{lineno} in file {self.path}"
                ) from exc
        return models

    def to_dict(self):
        return {"models": self.models}


class OdooModel:
    """Odoo model definition representation."""

    def __init__(self, pyfile: PyFile, class_node: Node):
        self.pyfile = pyfile
        assert self.is_model(class_node) or self.is_base_class(class_node)
        self.file_path = self.pyfile.path
        if self.pyfile.module_path:
            self.file_path = self.file_path.relative_to(self.pyfile.module_path)
        self.class_name = ts_utils.get_class_name(class_node)
        self.type_ = self._get_type(class_node)
        self.name = self._get_attr_value(class_node, "_name")
        self.inherit = self._get_attr_value(class_node, "_inherit")
        self.inherits = self._get_attr_value(class_node, "_inherits")
        self.auto = self._get_attr_value(class_node, "_auto")  # None / False / True
        self.order = self._get_attr_value(class_node, "_order")
        self.fields = self._get_fields(class_node)
        self.methods = self._get_methods(class_node)

    @classmethod
    def is_model(cls, class_node: Node) -> bool:
        """Check if class_node is an Odoo model."""
        name = cls._get_attr_value(class_node, "_name")
        inherit = cls._get_attr_value(class_node, "_inherit")
        return bool(name or inherit)

    @classmethod
    def is_base_class(cls, class_node: Node) -> bool:
        """Check if class_node is an Odoo base class."""
        bases = ts_utils.get_class_bases(class_node)
        class_name = ts_utils.get_class_name(class_node)

        # Check "object" in bases for Python 2 compatibility (old Odoo versions)
        if class_name == "BaseModel" and (not bases or "object" in bases):
            return True
        if class_name in BASE_CLASSES and set(bases) & set(BASE_CLASSES):
            return True
        return False

    @staticmethod
    def _get_type(class_node) -> str:
        """Return the type of the Odoo model.

        Available types are 'Model', 'AbstractModel', 'TransientModel'...
        """
        bases = ts_utils.get_class_bases(class_node)
        for base in bases:
            # base is a string like 'Model' or 'models.Model'
            if "." in base:
                return base.split(".")[-1]
            return base
        return None

    @staticmethod
    def _get_attr_value(
        class_node, attr_name: str
    ) -> typing.Union[str, dict, list, None]:
        """Return value of an attribute.

        It supports only attributes having basic values. E.g. if an attribute
        takes its value from a function call, nothing will be returned.
        """
        block_node = ts_utils.get_class_body(class_node)
        if not block_node:
            return None

        for assign_node in ts_utils.find_assignments_in_block(block_node, attr_name):
            value_node = ts_utils.get_assignment_value(assign_node)
            if not value_node:
                continue

            # _name, _inherit, _description, _auto, _order...
            if ts_utils.is_string_constant(value_node):
                return ts_utils.extract_string_value(value_node)

            # _inherit = [...]
            if ts_utils.is_list_literal(value_node):
                values = []
                for item_node in ts_utils.get_list_items(value_node):
                    if ts_utils.is_string_constant(item_node):
                        val = ts_utils.extract_string_value(item_node)
                        if val is not None:
                            values.append(val)
                    elif item_node.type == "identifier":
                        # Try to resolve identifier to its value
                        ref_val = OdooModel._get_attr_value(
                            class_node, item_node.text.decode()
                        )
                        if ref_val:
                            values.append(ref_val)
                        else:
                            # Keep as-is if can't resolve
                            values.append(item_node.text.decode())
                    elif item_node.type in ("integer", "float"):
                        values.append(item_node.text.decode())
                return values if values else None

            # _inherits = {...}
            if ts_utils.is_dict_literal(value_node):
                items = ts_utils.extract_dict_items(value_node)
                return items if items else None

        return None

    def _get_fields(self, class_node: Node) -> dict:
        """Return the fields declared in current data model."""
        fields = {}
        block_node = ts_utils.get_class_body(class_node)
        if not block_node:
            return fields

        for child in block_node.children:
            if child.type != "expression_statement":
                continue
            expr = child.child(0) if child.child_count > 0 else None
            if not expr or expr.type != "assignment":
                continue

            if not OdooField.is_field(expr):
                continue

            try:
                field = OdooField(self.pyfile, expr)
            except Exception as exc:
                field_name = ts_utils.get_assignment_target_name(expr) or "unknown"
                lineno = expr.start_point[0] + 1
                raise RuntimeError(
                    f"Unable to parse field {field_name}:{lineno} "
                    f"in file {self.pyfile.path}"
                ) from exc
            fields[field.name] = field.to_dict()
        return fields

    def _get_methods(self, class_node: Node) -> dict:
        """Return the methods declared in current data model."""
        methods = {}
        block_node = ts_utils.get_class_body(class_node)
        if not block_node:
            return methods

        for child in block_node.children:
            func_node = None

            # Handle decorated functions
            if child.type == "decorated_definition":
                for sub in child.children:
                    if sub.type == "function_definition":
                        func_node = sub
                        break
            # Handle regular functions
            elif child.type == "function_definition":
                func_node = child

            if not func_node:
                continue

            if not OdooMethod.is_method(func_node):
                continue

            try:
                method = OdooMethod(self.pyfile, func_node)
            except Exception as exc:
                method_name = ts_utils.get_function_name(func_node) or "unknown"
                lineno = func_node.start_point[0] + 1
                raise RuntimeError(
                    f"Unable to parse method {method_name}:{lineno} "
                    f"in file {self.pyfile.path}"
                ) from exc
            methods[method.name] = method.to_dict()
        return methods

    def to_dict(self) -> dict:
        data = {
            "file_path": str(self.file_path),
            "class_name": self.class_name,
            "type": self.type_,
        }
        if self.auto is not None:
            data["auto"] = self.auto
        for attr in ("name", "inherit", "inherits", "fields", "methods", "order"):
            if getattr(self, attr):
                data[attr] = getattr(self, attr)
        return data


class OdooField:
    """Odoo field representation."""

    def __init__(self, pyfile: PyFile, assign_node: Node):
        self.pyfile = pyfile
        assert self.is_field(assign_node)
        self.name = ts_utils.get_assignment_target_name(assign_node)
        self.type_ = self._extract_type(assign_node)
        self.lineno = assign_node.start_point[0] + 1
        self.end_lineno = assign_node.end_point[0] + 1
        self.code = "\n".join(self.pyfile.lines[self.lineno - 1 : self.end_lineno])
        self.args, self.kwargs = self._extract_arguments(assign_node)
        self.comodel_name = self._extract_comodel_name()
        self.inverse_name = self._extract_inverse_name()
        self.string = self._extract_string()

    @classmethod
    def is_field(cls, assign_node: Node) -> bool:
        """Check if assign_node is an Odoo field."""
        if assign_node.type != "assignment":
            return False
        value_node = ts_utils.get_assignment_value(assign_node)
        if not value_node or value_node.type != "call":
            return False
        return cls._extract_type(assign_node) is not None

    @classmethod
    def _extract_type(cls, assign_node: Node) -> typing.Optional[str]:
        """Extract the field type from an assignment."""
        value_node = ts_utils.get_assignment_value(assign_node)
        if not value_node or value_node.type != "call":
            return None

        func_node = value_node.child(0)
        if not func_node:
            return None

        field_type = None
        if func_node.type == "identifier":
            field_type = func_node.text.decode()
        elif func_node.type == "attribute":
            # e.g. fields.Char
            field_type = ts_utils.get_attribute_full_name(func_node).split(".")[-1]

        return field_type if field_type in FIELD_TYPES else None

    @classmethod
    def _extract_arguments(
        cls, assign_node: Node
    ) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
        """Extract positional and keyword arguments from the field call."""
        value_node = ts_utils.get_assignment_value(assign_node)
        if not value_node or value_node.type != "call":
            return [], {}
        return ts_utils.get_call_arguments(value_node)

    def _extract_comodel_name(self) -> typing.Optional[str]:
        """Extract comodel_name from relational field arguments.

        Relational fields (Many2one, One2many, Many2many) have comodel_name
        as their first positional argument or as a keyword argument.
        """
        if self.type_ not in ("Many2one", "One2many", "Many2many"):
            return None

        # First check keyword arguments
        if "comodel_name" in self.kwargs:
            val = self.kwargs["comodel_name"]
            return val if isinstance(val, str) else None

        # Then check positional arguments (comodel_name is always first)
        if self.args and isinstance(self.args[0], str):
            return self.args[0]

        return None

    def _extract_inverse_name(self) -> typing.Optional[str]:
        """Extract inverse_name from One2many field arguments.

        One2many fields have inverse_name as their second positional argument
        or as a keyword argument.
        """
        if self.type_ != "One2many":
            return None

        # First check keyword arguments
        if "inverse_name" in self.kwargs:
            val = self.kwargs["inverse_name"]
            return val if isinstance(val, str) else None

        # Then check positional arguments (inverse_name is second for One2many)
        if len(self.args) >= 2 and isinstance(self.args[1], str):
            return self.args[1]

        return None

    def _extract_string(self) -> typing.Optional[str]:
        """Extract string (label) from field arguments.

        The string parameter is the human-readable label for the field.
        Position varies by field type:
        - Simple fields (Char, Integer, etc.): string is 1st positional arg
        - Relational fields: string is after comodel_name/inverse_name
        - Can also be passed as keyword argument: string="Label"
        """
        # First check keyword arguments (works for all field types)
        if "string" in self.kwargs:
            val = self.kwargs["string"]
            return val if isinstance(val, str) else None

        # For relational fields, determine position of string in args
        if self.type_ in ("Many2one", "One2many", "Many2many"):
            # String comes after comodel_name and possibly inverse_name
            if self.type_ == "One2many":
                # One2many: (comodel_name, inverse_name, string, ...)
                if len(self.args) >= 3 and isinstance(self.args[2], str):
                    return self.args[2]
            else:
                # Many2one/Many2many: (comodel_name, string, ...)
                if len(self.args) >= 2 and isinstance(self.args[1], str):
                    return self.args[1]
        else:
            # For simple fields, string is the first positional argument
            if self.args and isinstance(self.args[0], str):
                return self.args[0]

        return None

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "type": self.type_,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "code": self.code,
        }
        if self.args:
            data["args"] = self.args
        if self.kwargs:
            data["kwargs"] = self.kwargs
        if self.comodel_name is not None:
            data["comodel_name"] = self.comodel_name
        if self.inverse_name is not None:
            data["inverse_name"] = self.inverse_name
        if self.string is not None:
            data["string"] = self.string
        return data


class OdooMethod:
    """Odoo data model method representation."""

    def __init__(self, pyfile: PyFile, func_node: Node):
        self.pyfile = pyfile
        assert self.is_method(func_node)
        self.name = ts_utils.get_function_name(func_node)
        self.decorators = self._extract_decorators(func_node)
        self.signature = self._extract_method_signature(func_node)
        self.lineno = func_node.start_point[0] + 1
        self.end_lineno = func_node.end_point[0] + 1
        self.code = "\n".join(self.pyfile.lines[self.lineno - 1 : self.end_lineno])

    @classmethod
    def is_method(cls, func_node: Node) -> bool:
        """Check if func_node is a method/function."""
        if func_node.type != "function_definition":
            return False
        func_name = ts_utils.get_function_name(func_node)
        # Skip private methods
        return func_name and not func_name.startswith("__")

    @classmethod
    def _extract_decorators(cls, func_node: Node) -> tuple[str, ...]:
        """Extract decorators from a function definition."""
        decorators = []

        # Handle direct decorators on the function node
        if func_node.type == "function_definition":
            parent = func_node.parent
            if parent and parent.type == "decorated_definition":
                # Find decorators in the decorated_definition
                for child in parent.children:
                    if child.type == "decorator":
                        deco_name = ts_utils.get_decorator_name(child)
                        deco_args = ts_utils.get_decorator_arguments(child)
                        if deco_args:
                            deco_full = f"{deco_name}({', '.join(deco_args)})"
                        else:
                            deco_full = deco_name
                        if deco_full:
                            decorators.append(deco_full)

        return tuple(decorators)

    @classmethod
    def _extract_method_signature(cls, func_node: Node) -> tuple[str, ...]:
        """Extract method signature from a function definition."""
        return ts_utils.get_function_parameters(func_node)

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "signature": self.signature,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "code": self.code,
        }
        if self.decorators:
            data["decorators"] = self.decorators
        return data
