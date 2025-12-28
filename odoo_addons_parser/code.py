# Copyright 2023 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Parse Python module files and extract Odoo data models from them."""

import ast
import pathlib
import typing

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
        if not path.suffix == ".py":
            raise ValueError(f"{path} is not a Python file")
        self.path = path
        self.module_path = module_path
        self.lines, self.ast_content = self._parse_file()
        self.models = self._get_models()

    def _parse_file(self):
        try:
            with open(self.path) as file_:
                lines = file_.readlines()
                content = "".join(lines)
                return lines, ast.parse(content)
        except Exception as exc:
            raise RuntimeError(f"Unable to parse file {self.path}") from exc

    def _get_models(self) -> dict:
        models = {}
        for elt in self.ast_content.body:
            try:
                if isinstance(elt, ast.ClassDef) and OdooModel.is_model(elt):
                    model = OdooModel(self, elt)
                    # Support corner case where the same data model is
                    # declared/inherited multiple times in the same file
                    # (each of them will add a new model definition entry).
                    key = f"{self.path}:{elt.name};{elt.lineno}"
                    models[key] = model.to_dict()
                elif isinstance(elt, ast.ClassDef) and OdooModel.is_base_class(elt):
                    model = OdooModel(self, elt)
                    models[elt.name] = model.to_dict()
            except Exception as exc:
                raise RuntimeError(
                    f"Unable to parse class {elt.name}:{elt.lineno} "
                    f"in file {self.path}"
                ) from exc
        return models

    def to_dict(self):
        return {"models": self.models}


class OdooModel:
    """Odoo model definition representation."""

    def __init__(self, pyfile: PyFile, ast_cls: ast.ClassDef):
        self.pyfile = pyfile
        assert self.is_model(ast_cls) or self.is_base_class(ast_cls)
        self.file_path = self.pyfile.path
        if self.pyfile.module_path:
            self.file_path = self.file_path.relative_to(self.pyfile.module_path)
        self.class_name = ast_cls.name
        self.type_ = self._get_type(ast_cls)
        self.name = self._get_attr_value(ast_cls, "_name")
        self.inherit = self._get_attr_value(ast_cls, "_inherit")
        self.inherits = self._get_attr_value(ast_cls, "_inherits")
        self.auto = self._get_attr_value(ast_cls, "_auto")  # None / False / True
        self.order = self._get_attr_value(ast_cls, "_order")
        self.fields = self._get_fields(ast_cls)
        self.methods = self._get_methods(ast_cls)

    @classmethod
    def is_model(cls, ast_cls) -> bool:
        """Check if `ast_cls` is an Odoo model."""
        name = cls._get_attr_value(ast_cls, "_name")
        inherit = cls._get_attr_value(ast_cls, "_inherit")
        return bool(name or inherit)

    @classmethod
    def is_base_class(cls, ast_cls) -> bool:
        """Check if `ast_cls` is an Odoo base class."""
        bases = []
        for base in ast_cls.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)
        if ast_cls.name == "BaseModel" and not bases:
            return True
        if ast_cls.name in BASE_CLASSES and set(bases) & set(BASE_CLASSES):
            return True
        return False

    @staticmethod
    def _get_type(ast_cls) -> str:
        """Return the type of the Odoo model.

        Available types are 'Model', 'AbstractModel', 'TransientModel'...
        """
        for base in ast_cls.bases:
            # Support e.g.'models.Model'
            if isinstance(base, ast.Attribute):
                return base.attr
            # Support e.g. 'Model'
            if isinstance(base, ast.Name):
                return base.id

    @staticmethod
    def _get_attr_value(
        ast_cls: ast.ClassDef, attr_name: str
    ) -> typing.Union[str, dict]:
        """Return value of an attribute.

        It supports only attributes having basic values. E.g. if an attribute
        takes its value from a function call, nothing will be returned.
        """
        for elt in ast_cls.body:
            if isinstance(elt, ast.Assign) and elt.targets:
                for target in elt.targets:
                    # Skip any assignment that is not a direct class attribute
                    if not isinstance(target, ast.Name):
                        continue
                    # Skip attribute name that doesn't match
                    if target.id != attr_name:
                        continue
                    # _name, _inherit, _description, _auto, _order...
                    if isinstance(elt.value, ast.Constant):
                        return elt.value.value
                    #  _inherit = [...]
                    if isinstance(elt.value, ast.List):
                        values = []
                        for e in elt.value.elts:
                            # e.g. = ['my.model']
                            if isinstance(e, ast.Constant):
                                values.append(e.value)
                            # e.g. = [_name]
                            if isinstance(e, ast.Name):
                                value = OdooModel._get_attr_value(ast_cls, e.id)
                                if value:
                                    values.append(value)
                        return values
                    # _inherits
                    if isinstance(elt.value, ast.Dict):
                        # iterate on dict keys/values
                        values = {}
                        for key, value in zip(elt.value.keys, elt.value.values):
                            if isinstance(key, ast.Constant) and isinstance(
                                value, ast.Constant
                            ):
                                values[key.value] = value.value
                        if values:
                            return values

    def _get_fields(self, ast_cls: ast.ClassDef) -> dict:
        """Return the fields declared in current data model."""
        fields = {}
        for elt in ast_cls.body:
            if not OdooField.is_field(elt):
                continue
            try:
                field = OdooField(self.pyfile, elt)
            except Exception as exc:
                raise RuntimeError(
                    f"Unable to parse field {elt.name}:{elt.lineno} "
                    f"in file {self.pyfile.path}"
                ) from exc
            fields[field.name] = field.to_dict()
        return fields

    def _get_methods(self, ast_cls: ast.ClassDef) -> dict:
        """Return the methods declared in current data model."""
        methods = {}
        for elt in ast_cls.body:
            if not OdooMethod.is_method(elt):
                continue
            try:
                method = OdooMethod(self.pyfile, elt)
            except Exception as exc:
                raise RuntimeError(
                    f"Unable to parse method {elt.name}:{elt.lineno} "
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

    def __init__(self, pyfile: PyFile, ast_cls: ast.Assign):
        self.pyfile = pyfile
        assert self.is_field(ast_cls)
        self.name = ast_cls.targets[0].id
        self.type_ = self._extract_type(ast_cls)
        self.lineno, self.end_lineno = ast_cls.lineno, ast_cls.end_lineno
        self.code = "".join(self.pyfile.lines[self.lineno - 1 : self.end_lineno])

    @classmethod
    def is_field(cls, ast_cls: ast.Assign) -> bool:
        """Check if `ast_cls` is an Odoo field."""
        if isinstance(ast_cls, ast.Assign) and ast_cls.targets:
            if not isinstance(ast_cls.value, ast.Call):
                return False
            field_type = cls._extract_type(ast_cls)
            if not field_type:
                return False
            return True
        return False

    @classmethod
    def _extract_type(cls, ast_cls: ast.Assign) -> str:
        field_type = None
        # Support e.g.'fields.Char'
        if isinstance(ast_cls.value.func, ast.Attribute):
            field_type = ast_cls.value.func.attr
        # Support e.g. 'Char'
        elif isinstance(ast_cls.value.func, ast.Name):
            field_type = ast_cls.value.func.id
        if field_type in FIELD_TYPES:
            return field_type

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type_,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "code": self.code,
        }


class OdooMethod:
    """Odoo data model method representation."""

    def __init__(self, pyfile: PyFile, ast_cls: ast.FunctionDef):
        self.pyfile = pyfile
        assert self.is_method(ast_cls)
        self.name = ast_cls.name
        self.decorators = self._extract_decorators(ast_cls)
        self.signature = self._extract_method_signature(ast_cls)
        self.lineno, self.end_lineno = ast_cls.lineno, ast_cls.end_lineno
        self.code = "".join(self.pyfile.lines[self.lineno - 1 : self.end_lineno])

    @classmethod
    def is_method(cls, ast_cls: ast.FunctionDef) -> bool:
        """Check if `ast_cls` is a method/function."""
        if isinstance(ast_cls, ast.FunctionDef):
            # Skip private methods
            return not ast_cls.name.startswith("__")
        return False

    @classmethod
    def _extract_decorators(cls, ast_cls: ast.FunctionDef) -> tuple[str, ...]:
        decorators = []
        for dec in ast_cls.decorator_list:
            # E.g. @model
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                # E.g. @api.model
                decorators.append(f"{dec.value.id}.{dec.attr}")
            elif isinstance(dec, ast.Call):
                # E.g. @api.depends(...)
                if isinstance(dec.func, ast.Name):
                    deco = f"{dec.func.id}"
                elif isinstance(dec.func, ast.Attribute):
                    deco = f"{dec.func.value.id}.{dec.func.attr}"
                args = cls._extract_decorator_signature(dec)
                deco += "({})".format(", ".join(args))
                decorators.append(deco)
        return tuple(decorators)

    @classmethod
    def _extract_decorator_signature(cls, ast_cls: ast.Call) -> tuple[str, ...]:
        assert isinstance(ast_cls, ast.Call)
        args = []
        for arg in ast_cls.args:
            args.append(ast_to_string(arg))
        kwargs = []
        for keyword in ast_cls.keywords:
            kwargs.append(f"{keyword.arg}=" + ast_to_string(keyword.value))
        return tuple(args + kwargs)

    @classmethod
    def _extract_method_signature(cls, ast_cls: ast.FunctionDef) -> tuple[str, ...]:
        assert isinstance(ast_cls, ast.FunctionDef)
        # Positional arguments
        args = [arg.arg for arg in ast_cls.args.args]
        posonly_args = [arg.arg for arg in ast_cls.args.posonlyargs]
        # Defaults
        defaults = []
        for default in ast_cls.args.defaults:
            defaults.append(ast_to_string(default))
        signature = args[:] + posonly_args[:]
        defaults.reverse()
        for i, default in enumerate(defaults):
            arg = signature[-i - 1]
            signature[-i - 1] = f"{arg}={default}"
        # Kwarg (**)
        if ast_cls.args.kwarg:
            signature.append(f"**{ast_cls.args.kwarg.arg}")
        return tuple(signature)

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


def ast_to_string(elt) -> str:
    """Return the string representation of an ast element."""
    if isinstance(elt, ast.Name):
        return elt.id
    if isinstance(elt, ast.Constant):
        return repr(elt.value)
    return f"<{type(elt).__name__}()>"
