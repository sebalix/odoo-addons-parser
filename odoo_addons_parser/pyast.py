import code_ast

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


class PyFileVisitor(code_ast.ASTVisitor):
    """Visit a Python module file.

    Will call the ClassVisitor as soon as a class is detected.
    """

    def __init__(self, pyfile):
        self.pyfile = pyfile
        self.data = {"models": {}}

    def visit_class_definition(self, node):
        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode()
                break
        class_visitor = ClassVisitor(self.pyfile, self.data, node, name)
        return class_visitor(node)

    # def on_visit(self, node):
    #     return super().on_visit(node)


class ClassVisitor(code_ast.ASTVisitor):
    """Visit class within a Python module.

    Will call the dedicated ModelVisitor as soon as an Odoo model is detected.
    """

    def __init__(self, pyfile, data, node, class_name):
        self.pyfile = pyfile
        self.data = data
        self.node = node
        self.class_name = class_name

    def visit_expression_statement(self, node):
        if node.parent.type != "block":
            return False

    def visit_assignment(self, node):
        if node.parent.type != "expression_statement":
            return False

    def visit_identifier(self, node):
        """Get the _name or _inherit attribute."""
        if node.parent.type != "assignment":
            return False
        value = node.text.decode()
        if value in ("_name", "_inherit"):
            model_visitor = ModelVisitor(
                self.pyfile, self.data, self.node, self.class_name
            )
            if model_visitor.key in self.data["models"]:
                return
            return model_visitor(self.node)


class ModelVisitor(code_ast.ASTVisitor):
    """Dedicated visitor for Odoo models.

    Will call the following visitors in cascade:
        - FieldVisitor
        - MethodVisitor
    """

    def __init__(self, pyfile, data, node, class_name):
        self.pyfile = pyfile
        self.file_path = self.pyfile.path
        if self.pyfile.module_path:
            self.file_path = self.file_path.relative_to(self.pyfile.module_path)
        self.data = data
        self.node = node
        self.block = list(
            filter(lambda node: node.type == "block", self.node.named_children)
        )[0]
        self.lineno = self.node.start_point.row
        self.end_lineno = self.node.end_point.row
        self.class_name = class_name
        self.type_ = self._get_type()
        self.name = self._get_attr_value("_name")
        self.inherit = self._get_attr_value("_inherit")
        self.inherits = self._get_attr_value("_inherits")
        self.auto = self._get_attr_value("_auto")  # None / False / True
        self.order = self._get_attr_value("_order")
        self.key = f"{self.file_path}:{self.class_name}:{self.node.start_point.row}"

    def _init_data(self):
        data = self.data["models"].setdefault(self.key, {})
        data.update(
            {
                "file_path": str(self.file_path),
                "lineno": self.lineno,
                "end_lineno": self.end_lineno,
                "class_name": self.class_name,
                "type": self.type_,
            }
        )
        if self.auto is not None:
            data["auto"] = self.auto
        for attr in ("name", "inherit", "inherits", "order"):
            if getattr(self, attr):
                data[attr] = getattr(self, attr)

    def __call__(self, root_node):
        self._init_data()
        return super().__call__(root_node)

    def visit_call(self, node):
        """Catch all fields declarations."""
        if node.parent.type != "assignment":
            return
        if node.parent.parent.type != "expression_statement":
            return
        if node.parent.parent.parent.type != "block":
            return
        nodes = [
            child
            for child in node.named_children
            if
            (
                # fields.Char
                (
                    child.type == "attribute"
                    and child.text.decode().split(".")[-1] in FIELD_TYPES
                )
                # Char
                or (child.type == "identifier")
            )
        ]
        if not nodes:
            return
        node = nodes[0]
        field_node = node.parent.parent
        id_ = field_node.named_children[0]
        if id_.type == "identifier":
            field_visitor = FieldVisitor(self.pyfile, self.data, field_node, model=self)
            field_visitor(field_node)

    def _get_type(self):
        """Return the type of the Odoo model.

        Available types are 'Model', 'AbstractModel', 'TransientModel'...
        """
        type_ = [
            identifier.text.decode()
            for arg_list in self.node.named_children
            if arg_list.type == "argument_list"
            for attribute in arg_list.named_children
            if attribute.type == "attribute"
            for identifier in attribute.named_children
            if identifier.type == "identifier"
            and identifier.text.decode() in BASE_CLASSES
        ]
        return type_[0] if type_ else None

    def _get_attr_value(self, attr: str):
        assignments = [
            identifier.parent
            for expr_stmt in self.block.named_children
            if expr_stmt.type == "expression_statement"
            for assignment in expr_stmt.named_children
            if assignment.type == "assignment"
            for identifier in assignment.named_children
            if identifier.type == "identifier"
            # Keep matching attribute name
            and identifier.text.decode() == attr
        ]
        if not assignments:
            return
        value = assignments[0].children[2]
        # _name, _inherit, _description, _auto, _order...
        if value.type == "string":
            return value.children[1].text.decode()
        #  _inherit = [...]
        if value.type == "list":
            values = []
            for child in value.named_children:
                # e.g. = ['my.model']
                if child.type == "string":
                    values.append(child.children[1].text.decode())
                # e.g. = [_name]
                if child.type == "identifier":
                    id_ = child.text.decode()
                    value = self._get_attr_value(id_)
                    if value:
                        values.append(value)
            return values


class FieldVisitor(code_ast.ASTVisitor):
    """Dedicated visitor for fields declared in Odoo models."""

    def __init__(self, pyfile, data, node, model):
        self.pyfile = pyfile
        self.data = data
        self.node = node
        self.model = model
        self.lineno = self.node.start_point.row
        self.end_lineno = self.node.end_point.row
        self.name = self.node.named_children[0].text.decode()
        self.type_ = self._get_type()
        self.code = "".join(self.pyfile.lines[self.lineno - 1 : self.end_lineno])

    def _init_data(self):
        data = (
            self.data["models"][self.model.key]
            .setdefault("fields", {})
            .setdefault(self.name, {})
        )
        data.update(
            {
                "lineno": self.lineno,
                "end_lineno": self.end_lineno,
                "name": self.name,
                "type": self.type_,
            }
        )

    def __call__(self, root_node):
        self._init_data()
        return super().__call__(root_node)

    def _get_type(self):
        """Return the type of the Odoo field."""
        type_ = [
            identifier.text.decode()
            for call in self.node.named_children
            if call.type == "call"
            for attribute in call.named_children
            if attribute.type == "attribute"
            for identifier in attribute.named_children
            if identifier.type == "identifier"
            and identifier.text.decode() in FIELD_TYPES
        ]
        return type_[0] if type_ else None


class MethodVisitor(code_ast.ASTVisitor):
    """Dedicated visitor for methods implemented in Odoo models."""

    # TODO
    def __init__(self, pyfile, data, node):
        self.pyfile = pyfile
        self.data = data
        self.node = node


class PrinterVisitor(code_ast.ASTVisitor):
    """Visitor used for debug purpose.

    It prints the AST tree of any node while keeping only relevant data.

        >>> printer = PrinterVisitor()
        >>> printer(any_node)
    """

    def __init__(self):
        self.count = 0

    def visit(self, node):
        tabs = "\t" * self.count
        nodes_to_skip = (
            "module",
            "import_from_statement",
            "class_definition",
            "function_definition",
            "block",
            "for_statement",
            "expression_statement",
            "decorated_definition",
            "assignment",
            "call",
            "argument_list",
            "keyword_argument",
            "list",
            "dictionary",
        )
        if node.type in nodes_to_skip:
            print(f"{tabs}[{node.type}] ...")
        else:
            print(f"{tabs}[{node.type}] {node.text.decode()}")
        self.count += 1

    def leave(self, node):
        self.count -= 1
