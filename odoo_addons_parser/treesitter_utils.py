# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Tree-sitter utilities for Python code parsing."""

import typing
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython


def get_parser() -> Parser:
    """Get a tree-sitter parser for Python."""
    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)
    return parser


def find_class_definitions(node: Node) -> typing.Iterator[Node]:
    """Yield all class definition nodes."""
    if node.type == "class_definition":
        yield node
    for child in node.children:
        yield from find_class_definitions(child)


def get_class_name(class_node: Node) -> typing.Optional[str]:
    """Get the name of a class definition."""
    assert class_node.type == "class_definition"
    for child in class_node.children:
        if child.type == "identifier":
            return child.text.decode()
    return None


def get_class_bases(class_node: Node) -> typing.List[str]:
    """Get base class names from a class definition."""
    assert class_node.type == "class_definition"
    bases = []
    for child in class_node.children:
        if child.type == "argument_list":
            # arguments_list contains base classes
            for arg_child in child.children:
                if arg_child.type == "identifier":
                    bases.append(arg_child.text.decode())
                elif arg_child.type == "attribute":
                    # Handle e.g. 'models.Model'
                    bases.append(get_attribute_full_name(arg_child))
    return bases


def get_attribute_full_name(node: Node) -> str:
    """Get full name of an attribute node (e.g., 'models.Model')."""
    if node.type != "attribute":
        return ""
    parts = []
    current = node
    while current.type == "attribute":
        # Find the object.attribute part
        children = [
            c for c in current.children if c.type in ("identifier", "attribute")
        ]
        if children:
            attr_part = current.child_by_field_name("attribute")
            if attr_part:
                parts.insert(0, attr_part.text.decode())
            current = current.child_by_field_name("object") or children[0]
        else:
            break
    # Add the final identifier
    if current.type == "identifier":
        parts.insert(0, current.text.decode())
    return ".".join(parts)


def get_class_body(class_node: Node) -> Node:
    """Get the block/body of a class definition."""
    assert class_node.type == "class_definition"
    for child in class_node.children:
        if child.type == "block":
            return child
    return None


def find_assignments_in_block(
    block_node: Node, target_name: str
) -> typing.Iterator[Node]:
    """Find assignment nodes in a block matching the target name."""
    if not block_node or block_node.type != "block":
        return
    for child in block_node.children:
        if child.type == "expression_statement":
            # Check if this is an assignment
            expr = child.child(0) if child.child_count > 0 else None
            if expr and expr.type == "assignment":
                # Check if left side matches target_name
                for target_child in expr.children:
                    if (
                        target_child.type == "identifier"
                        and target_child.text.decode() == target_name
                    ):
                        yield expr
                        break


def get_assignment_target_name(assign_node: Node) -> typing.Optional[str]:
    """Get the target variable name from an assignment."""
    assert assign_node.type == "assignment"
    for child in assign_node.children:
        if child.type == "identifier":
            return child.text.decode()
    return None


def get_assignment_value(assign_node: Node) -> Node:
    """Get the value node from an assignment."""
    assert assign_node.type == "assignment"
    # Find the value (after the '=' operator)
    for child in assign_node.children:
        if child.type != "identifier" and child.text.decode() != "=":
            return child
    return None


def is_string_constant(node: Node) -> bool:
    """Check if node is a string constant."""
    return node.type in ("string", "f_string")


def is_list_literal(node: Node) -> bool:
    """Check if node is a list literal."""
    return node.type == "list"


def is_dict_literal(node: Node) -> bool:
    """Check if node is a dict literal."""
    return node.type == "dictionary"


def extract_string_value(node: Node) -> typing.Optional[str]:
    """Extract string value from a string node."""
    if node.type not in ("string", "f_string"):
        return None
    text = node.text.decode()
    # Remove quotes
    for quote in ('"""', "'''", '"', "'"):
        if text.startswith(quote) and text.endswith(quote):
            return text[len(quote) : -len(quote)]
    return text


def get_list_items(list_node: Node) -> typing.Iterator[Node]:
    """Yield all items in a list literal."""
    if list_node.type != "list":
        return
    for child in list_node.children:
        if child.type not in (",", "[", "]"):
            yield child


def extract_dict_items(dict_node: Node) -> typing.Dict[str, typing.Any]:
    """Extract key-value pairs from a dict literal."""
    if dict_node.type != "dictionary":
        return {}
    items = {}

    # Handle pair nodes (newer tree-sitter format)
    for child in dict_node.children:
        if child.type == "pair":
            # pair node has: key, ":", value
            key_node = None
            val_node = None
            for pair_child in child.children:
                if pair_child.type != ":":
                    if key_node is None:
                        key_node = pair_child
                    else:
                        val_node = pair_child

            if key_node and val_node:
                key = None
                val = None

                # Extract key (use node_to_string to preserve quotes for string keys)
                if key_node.type == "string":
                    key = node_to_string(key_node)
                elif key_node.type == "identifier":
                    key = key_node.text.decode()

                # Extract value (use node_to_string to preserve quotes for string values)
                if val_node.type == "string":
                    val = node_to_string(val_node)
                elif val_node.type == "identifier":
                    val = val_node.text.decode()
                elif val_node.type in ("integer", "float"):
                    val = val_node.text.decode()

                if key and val is not None:
                    items[key] = val

    # Also handle legacy flat format (key, value pairs without pair nodes)
    children = [
        c for c in dict_node.children if c.type not in (":", ",", "{", "}", "pair")
    ]
    i = 0
    while i < len(children) - 1:
        key_node = children[i]
        val_node = children[i + 1]
        key = None
        val = None

        # Extract key (use node_to_string to preserve quotes for string keys)
        if key_node.type == "string":
            key = node_to_string(key_node)
        elif key_node.type == "identifier":
            key = key_node.text.decode()

        # Extract value (use node_to_string to preserve quotes for string values)
        if val_node.type == "string":
            val = node_to_string(val_node)
        elif val_node.type == "identifier":
            val = val_node.text.decode()
        elif val_node.type in ("integer", "float"):
            val = val_node.text.decode()

        if key and val is not None:
            items[key] = val
        i += 2
    return items


def get_function_name(func_node: Node) -> typing.Optional[str]:
    """Get the name of a function definition."""
    assert func_node.type == "function_definition"
    for child in func_node.children:
        if child.type == "identifier":
            return child.text.decode()
    return None


def get_function_parameters(func_node: Node) -> typing.Tuple[str, ...]:
    """Get function parameters as a tuple of strings.

    Returns a tuple of parameter names with defaults where applicable,
    plus *args and **kwargs.
    """
    assert func_node.type == "function_definition"
    signature = []

    for child in func_node.children:
        if child.type == "parameters":
            for param_child in child.children:
                if param_child.type == "identifier":
                    signature.append(param_child.text.decode())
                elif param_child.type == "default_parameter":
                    # Has name and default value: name=value
                    name = None
                    default_val = None
                    for sub in param_child.children:
                        if sub.type == "identifier":
                            name = sub.text.decode()
                        elif sub.type == "=":
                            continue
                        else:
                            default_val = node_to_string(sub)
                    if name and default_val:
                        signature.append(f"{name}={default_val}")
                elif param_child.type in (
                    "list_splat_pattern",
                    "dictionary_splat_pattern",
                ):
                    # *args or **kwargs
                    prefix = "*" if param_child.type == "list_splat_pattern" else "**"
                    for sub in param_child.children:
                        if sub.type == "identifier":
                            signature.append(f"{prefix}{sub.text.decode()}")
                            break

    return tuple(signature)


def get_decorator_name(decorator_node: Node) -> str:
    """Get the decorator name/identifier."""
    assert decorator_node.type == "decorator"
    for child in decorator_node.children:
        if child.type == "identifier":
            return child.text.decode()
        elif child.type == "attribute":
            return get_attribute_full_name(child)
        elif child.type == "call":
            # Handle @decorator(...) - get the function name
            for call_child in child.children:
                if call_child.type == "identifier":
                    return call_child.text.decode()
                elif call_child.type == "attribute":
                    return get_attribute_full_name(call_child)
    return ""


def get_decorator_arguments(decorator_node: Node) -> typing.List[str]:
    """Get arguments from a decorator call."""
    assert decorator_node.type == "decorator"
    args = []
    for child in decorator_node.children:
        if child.type == "call":
            for call_child in child.children:
                if call_child.type == "argument_list":
                    for arg_child in call_child.children:
                        if arg_child.type not in (",", "(", ")"):
                            args.append(node_to_string(arg_child))
    return args


def get_call_arguments(
    call_node: Node
) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
    """Extract positional and keyword arguments from a call node.

    Returns a tuple (args_list, kwargs_dict) with actual Python values for literals
    and string representation for callable expressions.
    """
    args = []
    kwargs = {}

    if call_node.type != "call":
        return args, kwargs

    for child in call_node.children:
        if child.type == "argument_list":
            for arg_child in child.children:
                if arg_child.type == "keyword_argument":
                    # Extract keyword: value pair
                    key_node = None
                    val_node = None
                    for sub in arg_child.children:
                        if sub.type == "identifier":
                            key_node = sub
                        elif sub.type == "=":
                            continue
                        elif key_node is not None and val_node is None:
                            val_node = sub
                    if key_node and val_node:
                        key = key_node.text.decode()
                        val = node_to_value(val_node)
                        kwargs[key] = val
                elif arg_child.type not in ("(", ")", ",", "comment"):
                    # Positional argument (skip comments)
                    args.append(node_to_value(arg_child))

    return args, kwargs


def node_to_string(node: Node) -> str:
    """Convert a tree-sitter node to its string representation."""
    if node.type == "identifier":
        return node.text.decode()
    if node.type == "string":
        return repr(extract_string_value(node))
    if node.type in ("integer", "float"):
        return node.text.decode()
    if node.type == "true":
        return "True"
    if node.type == "false":
        return "False"
    if node.type == "none":
        return "None"
    # For callable expressions (lambda, function calls, etc.), return full text
    if node.type in ("lambda", "call"):
        return node.text.decode()
    # For other complex expressions, return the full text
    if len(node.text) < 200:
        return node.text.decode()
    return f"<{node.type}>"


def node_to_value(node: Node) -> typing.Any:
    """Convert a tree-sitter node to its Python value.

    For literal values (strings, booleans, numbers): returns the actual value
    For callable expressions (lambda, function calls): returns string representation
    """
    if node.type == "true":
        return True
    if node.type == "false":
        return False
    if node.type == "none":
        return None
    if node.type == "string":
        return extract_string_value(node)
    if node.type in ("integer", "float"):
        text = node.text.decode()
        if node.type == "integer":
            return int(text)
        else:
            return float(text)
    if node.type == "identifier":
        # Identifiers are returned as strings (could be variable references)
        return node.text.decode()
    # For callable expressions and complex expressions, return text representation
    if node.type in ("lambda", "call"):
        return node.text.decode()
    # For other complex expressions, return full text if reasonable length
    if len(node.text) < 200:
        return node.text.decode()
    return f"<{node.type}>"
