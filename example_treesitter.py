#!/usr/bin/env python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor

BASE_CLASSES = [
    "AbstractModel",
    "BaseModel",
    "Model",
    "TransientModel",
]

# Setup
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

# Code to parse
code = """
def greet():
    print("Hello, Tree-Sitter!")
"""

# Parse the code
with open(
    "odoo_addons_parser/tests/repo/module_test/models/res_partner.py", "rb"
) as file_:
    lines = file_.readlines()
    content = b"".join(lines)
    tree = parser.parse(content)

# Define query
query = Query(
    PY_LANGUAGE,
    """
(function_definition
  name: (identifier) @function.def
  body: (block) @function.block)

(call
  function: (identifier) @function.call
  arguments: (argument_list) @function.args)
""",
)

models_query = """
    (class_definition
        name: (identifier) @class_name
        superclasses: (argument_list
            [
                (identifier) @model_type
                (attribute
                    object: (identifier)
                    attribute: (identifier) @model_type
                )
            ]
            (#any-of? @model_type {base_classes})
        )
    ) @models
""".format(base_classes=" ".join(BASE_CLASSES))

model_query = """
        body: (block
            (expression_statement
                (assignment
                    left: (identifier) @name_inherit
                    right: (string
                        (string_content) @model
                    )
                )
                (#any-of? @name_inherit "_name" "_inherit")
            )
            (expression_statement
                (assignment
                    left: (identifier) @attr
                    right: (string
                        (string_content) @order
                    )
                )
                (#eq? @attr "_order")
            )?
        )
"""

fields_query = """
body: (block
    (expression_statement
        (assignment
            left: (identifier) @name_inherit
            right: (string
                (string_content) @model
            )
        )
    )
    (expression_statement
        (assignment
            left: (identifier) @field_name
            right: [
                (call
                    function: (identifier) @field_type
                )
                (call
                    function: (attribute
                        attribute: (identifier) @field_type
                    )
                )
            ]
        ) @field
    )
)
"""

captures = QueryCursor(Query(PY_LANGUAGE, models_query)).captures(tree.root_node)
for x, y, z in zip(captures["class_name"], captures["model_type"], captures["models"]):
    class_name = x.text.decode()
    type_ = y.text.decode()
    model_node = z
    data = QueryCursor(Query(PY_LANGUAGE, model_query)).captures(model_node)
    print(class_name, type_)
    __import__("pdb").set_trace()
# for model_node in captures.get("models", []):
#     # print(model_node)
#     data = QueryCursor(Query(PY_LANGUAGE, model_query)).captures(model_node)
#     __import__("pdb").set_trace()

# for node in nodes:
#     print(f"\tCapture {name}: {node.text.decode('utf8')}")

# Inspect the root node
# root_node = tree.root_node
# print(f"Root node type: {root_node.type}")  # Output: module
# print(f"Root node text:\n{root_node.text.decode('utf8')}")
