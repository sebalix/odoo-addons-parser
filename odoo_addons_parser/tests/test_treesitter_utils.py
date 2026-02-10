# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

"""Test cases for treesitter_utils module."""

import unittest

from odoo_addons_parser import treesitter_utils as ts_utils


class TestTreesitterUtils(unittest.TestCase):
    """Test cases for tree-sitter utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = ts_utils.get_parser()

    def _parse_code(self, code: str):
        """Helper to parse Python code and return the tree root node."""
        tree = self.parser.parse(code.encode())
        return tree.root_node

    # Tests for get_parser
    def test_get_parser_returns_parser(self):
        """Test that get_parser returns a valid Parser instance."""
        parser = ts_utils.get_parser()
        self.assertIsNotNone(parser)

    # Tests for find_class_definitions
    def test_find_class_definitions_single_class(self):
        """Test finding a single class definition."""
        code = "class MyClass: pass"
        root = self._parse_code(code)
        classes = list(ts_utils.find_class_definitions(root))
        self.assertEqual(len(classes), 1)

    def test_find_class_definitions_multiple_classes(self):
        """Test finding multiple class definitions."""
        code = """
class ClassA: pass
class ClassB: pass
class ClassC: pass
"""
        root = self._parse_code(code)
        classes = list(ts_utils.find_class_definitions(root))
        self.assertEqual(len(classes), 3)

    def test_find_class_definitions_nested_classes(self):
        """Test finding nested class definitions."""
        code = """
class Outer:
    class Inner:
        pass
"""
        root = self._parse_code(code)
        classes = list(ts_utils.find_class_definitions(root))
        self.assertEqual(len(classes), 2)

    def test_find_class_definitions_no_classes(self):
        """Test finding classes when there are none."""
        code = "x = 5"
        root = self._parse_code(code)
        classes = list(ts_utils.find_class_definitions(root))
        self.assertEqual(len(classes), 0)

    # Tests for get_class_name
    def test_get_class_name_simple(self):
        """Test getting the name of a simple class."""
        code = "class MyClass: pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        name = ts_utils.get_class_name(class_node)
        self.assertEqual(name, "MyClass")

    def test_get_class_name_with_bases(self):
        """Test getting the name of a class with base classes."""
        code = "class MyClass(BaseClass): pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        name = ts_utils.get_class_name(class_node)
        self.assertEqual(name, "MyClass")

    # Tests for get_class_bases
    def test_get_class_bases_no_bases(self):
        """Test getting bases when there are none."""
        code = "class MyClass: pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        bases = ts_utils.get_class_bases(class_node)
        self.assertEqual(bases, [])

    def test_get_class_bases_single_base(self):
        """Test getting a single base class."""
        code = "class MyClass(BaseClass): pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        bases = ts_utils.get_class_bases(class_node)
        self.assertEqual(bases, ["BaseClass"])

    def test_get_class_bases_multiple_bases(self):
        """Test getting multiple base classes."""
        code = "class MyClass(Base1, Base2, Base3): pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        bases = ts_utils.get_class_bases(class_node)
        self.assertEqual(bases, ["Base1", "Base2", "Base3"])

    def test_get_class_bases_attribute_reference(self):
        """Test getting base class with attribute reference (e.g., models.Model)."""
        code = "class MyClass(models.Model): pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        bases = ts_utils.get_class_bases(class_node)
        self.assertEqual(bases, ["models.Model"])

    def test_get_class_bases_mixed(self):
        """Test getting mixed base classes."""
        code = "class MyClass(Base1, models.Model, Base3): pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        bases = ts_utils.get_class_bases(class_node)
        self.assertEqual(bases, ["Base1", "models.Model", "Base3"])

    # Tests for get_attribute_full_name
    def test_get_attribute_full_name_single(self):
        """Test getting attribute name with single level."""
        code = "x = models.Model"
        root = self._parse_code(code)
        # Find the attribute node
        assignment = root.child(0).child(0)
        value = ts_utils.get_assignment_value(assignment)
        name = ts_utils.get_attribute_full_name(value)
        self.assertEqual(name, "models.Model")

    def test_get_attribute_full_name_nested(self):
        """Test getting attribute name with multiple levels."""
        code = "x = a.b.c.d"
        root = self._parse_code(code)
        assignment = root.child(0).child(0)
        value = ts_utils.get_assignment_value(assignment)
        name = ts_utils.get_attribute_full_name(value)
        self.assertEqual(name, "a.b.c.d")

    # Tests for get_class_body
    def test_get_class_body_returns_block(self):
        """Test that get_class_body returns a block node."""
        code = "class MyClass:\n    pass"
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        body = ts_utils.get_class_body(class_node)
        self.assertIsNotNone(body)
        self.assertEqual(body.type, "block")
        self.assertEqual(body.text.decode(), "pass")

    # Tests for find_assignments_in_block
    def test_find_assignments_in_block_single(self):
        """Test finding a single assignment in a block."""
        code = """
class MyClass:
    name = "test"
"""
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        block = ts_utils.get_class_body(class_node)
        assignments = list(ts_utils.find_assignments_in_block(block, "name"))
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].children[0].text.decode(), "name")

    def test_find_assignments_in_block_multiple(self):
        """Test finding multiple assignments with same target name."""
        code = """
class MyClass:
    x = 1
    x = 2
"""
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        block = ts_utils.get_class_body(class_node)
        assignments = list(ts_utils.find_assignments_in_block(block, "x"))
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0].children[0].text.decode(), "x")
        self.assertEqual(assignments[1].children[0].text.decode(), "x")

    def test_find_assignments_in_block_not_found(self):
        """Test when target assignment is not found."""
        code = """
class MyClass:
    name = "test"
"""
        root = self._parse_code(code)
        class_node = list(ts_utils.find_class_definitions(root))[0]
        block = ts_utils.get_class_body(class_node)
        assignments = list(ts_utils.find_assignments_in_block(block, "nonexistent"))
        self.assertEqual(len(assignments), 0)

    # Tests for get_assignment_target_name
    def test_get_assignment_target_name(self):
        """Test getting assignment target name."""
        code = "name = 'test'"
        root = self._parse_code(code)
        assignment = root.child(0).child(0)
        name = ts_utils.get_assignment_target_name(assignment)
        self.assertEqual(name, "name")

    # Tests for get_assignment_value
    def test_get_assignment_value_string(self):
        """Test getting assignment value as string."""
        code = 'x = "hello"'
        root = self._parse_code(code)
        assignment = root.child(0).child(0)
        value = ts_utils.get_assignment_value(assignment)
        self.assertEqual(value.type, "string")

    def test_get_assignment_value_number(self):
        """Test getting assignment value as number."""
        code = "x = 42"
        root = self._parse_code(code)
        assignment = root.child(0).child(0)
        value = ts_utils.get_assignment_value(assignment)
        self.assertEqual(value.type, "integer")

    def test_get_assignment_value_call(self):
        """Test getting assignment value as function call."""
        code = "x = func()"
        root = self._parse_code(code)
        assignment = root.child(0).child(0)
        value = ts_utils.get_assignment_value(assignment)
        self.assertEqual(value.type, "call")

    # Tests for type checking functions
    def test_is_string_constant_string(self):
        """Test is_string_constant with string node."""
        code = '"test"'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertTrue(ts_utils.is_string_constant(expr))

    def test_is_string_constant_not_string(self):
        """Test is_string_constant with non-string node."""
        code = "42"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertFalse(ts_utils.is_string_constant(expr))

    def test_is_list_literal_list(self):
        """Test is_list_literal with list node."""
        code = "[1, 2, 3]"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertTrue(ts_utils.is_list_literal(expr))

    def test_is_list_literal_not_list(self):
        """Test is_list_literal with non-list node."""
        code = '"test"'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertFalse(ts_utils.is_list_literal(expr))

    def test_is_dict_literal_dict(self):
        """Test is_dict_literal with dict node."""
        code = "{'key': 'value'}"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertTrue(ts_utils.is_dict_literal(expr))

    def test_is_dict_literal_not_dict(self):
        """Test is_dict_literal with non-dict node."""
        code = "[1, 2, 3]"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertFalse(ts_utils.is_dict_literal(expr))

    # Tests for extract_string_value
    def test_extract_string_value_double_quotes(self):
        """Test extracting string with double quotes."""
        code = '"hello"'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        value = ts_utils.extract_string_value(expr)
        self.assertEqual(value, "hello")

    def test_extract_string_value_single_quotes(self):
        """Test extracting string with single quotes."""
        code = "'hello'"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        value = ts_utils.extract_string_value(expr)
        self.assertEqual(value, "hello")

    def test_extract_string_value_triple_quotes(self):
        """Test extracting string with triple quotes."""
        code = '"""hello"""'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        value = ts_utils.extract_string_value(expr)
        self.assertEqual(value, "hello")

    def test_extract_string_value_not_string(self):
        """Test extracting value from non-string node."""
        code = "42"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        value = ts_utils.extract_string_value(expr)
        self.assertIsNone(value)

    # Tests for get_list_items
    def test_get_list_items_empty_list(self):
        """Test getting items from an empty list."""
        code = "[]"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        items = list(ts_utils.get_list_items(expr))
        self.assertEqual(len(items), 0)

    def test_get_list_items_single_item(self):
        """Test getting items from a single-item list."""
        code = "[1]"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        items = list(ts_utils.get_list_items(expr))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].type, "integer")

    def test_get_list_items_multiple_items(self):
        """Test getting items from a multi-item list."""
        code = "[1, 2, 3]"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        items = list(ts_utils.get_list_items(expr))
        self.assertEqual(len(items), 3)
        self.assertTrue(all(item.type == "integer" for item in items))

    # Tests for extract_dict_items
    def test_extract_dict_items_empty_dict(self):
        """Test extracting items from an empty dict."""
        code = "{}"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertEqual(expr.type, "dictionary")
        items = ts_utils.extract_dict_items(expr)
        self.assertEqual(items, {})

    def test_extract_dict_items_string_keys(self):
        """Test extracting dict items with string keys."""
        code = "{'key1': 'value1'}"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertEqual(expr.type, "dictionary")
        items = ts_utils.extract_dict_items(expr)
        self.assertTrue(items)
        self.assertIn("'key1'", items.keys())
        self.assertIn("'value1'", items.values())

    def test_extract_dict_items_identifier_keys(self):
        """Test extracting dict items with identifier keys."""
        code = "{name: value}"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        self.assertEqual(expr.type, "dictionary")
        items = ts_utils.extract_dict_items(expr)
        self.assertTrue(items)
        self.assertIn("name", items.keys())
        self.assertIn("value", items.values())

    # Tests for get_function_name
    def test_get_function_name(self):
        """Test getting function name."""
        code = "def my_function(): pass"
        root = self._parse_code(code)
        # Find function node
        func_node = None
        for child in root.children:
            if child.type == "function_definition":
                func_node = child
                break
        self.assertIsNotNone(func_node)
        name = ts_utils.get_function_name(func_node)
        self.assertEqual(name, "my_function")

    # Tests for get_function_parameters
    def test_get_function_parameters_no_params(self):
        """Test getting parameters from function with no parameters."""
        code = "def func(): pass"
        root = self._parse_code(code)
        func_node = None
        for child in root.children:
            if child.type == "function_definition":
                func_node = child
                break
        self.assertIsNotNone(func_node)
        params = ts_utils.get_function_parameters(func_node)
        self.assertEqual(params, ())

    def test_get_function_parameters_single_param(self):
        """Test getting parameters from function with one parameter."""
        code = "def func(x): pass"
        root = self._parse_code(code)
        func_node = None
        for child in root.children:
            if child.type == "function_definition":
                func_node = child
                break
        self.assertIsNotNone(func_node)
        params = ts_utils.get_function_parameters(func_node)
        self.assertEqual(params, ("x",))

    def test_get_function_parameters_multiple_params(self):
        """Test getting parameters from function with multiple parameters."""
        code = "def func(a, b, c): pass"
        root = self._parse_code(code)
        func_node = None
        for child in root.children:
            if child.type == "function_definition":
                func_node = child
                break
        self.assertIsNotNone(func_node)
        params = ts_utils.get_function_parameters(func_node)
        self.assertEqual(params, ("a", "b", "c"))

    def test_get_function_parameters_with_defaults(self):
        """Test getting parameters with default values."""
        code = 'def func(a, b=2, c="default"): pass'
        root = self._parse_code(code)
        func_node = None
        for child in root.children:
            if child.type == "function_definition":
                func_node = child
                break
        self.assertIsNotNone(func_node)
        params = ts_utils.get_function_parameters(func_node)
        self.assertIn("a", params)
        self.assertIn("b=2", params)
        self.assertIn("c='default'", params)

    def test_get_function_parameters_with_args_kwargs(self):
        """Test getting parameters with *args and **kwargs."""
        code = "def func(a, *args, **kwargs): pass"
        root = self._parse_code(code)
        func_node = None
        for child in root.children:
            if child.type == "function_definition":
                func_node = child
                break
        self.assertIsNotNone(func_node)
        params = ts_utils.get_function_parameters(func_node)
        self.assertIn("a", params)
        self.assertIn("*args", params)
        self.assertIn("**kwargs", params)

    # Tests for get_decorator_name
    def test_get_decorator_name_simple(self):
        """Test getting simple decorator name."""
        code = """
@decorator
def func(): pass
"""
        root = self._parse_code(code)
        for child in root.children:
            if child.type == "decorated_definition":
                for sub in child.children:
                    if sub.type == "decorator":
                        name = ts_utils.get_decorator_name(sub)
                        self.assertEqual(name, "decorator")
                return
        self.fail("Decorator not found")

    def test_get_decorator_name_attribute(self):
        """Test getting decorator name with attribute."""
        code = """
@api.depends('field')
def func(): pass
"""
        root = self._parse_code(code)
        for child in root.children:
            if child.type == "decorated_definition":
                for sub in child.children:
                    if sub.type == "decorator":
                        name = ts_utils.get_decorator_name(sub)
                        self.assertEqual(name, "api.depends")
                return
        self.fail("Decorator not found")

    # Tests for get_call_arguments
    def test_get_call_arguments_no_args(self):
        """Test extracting arguments from call with no arguments."""
        code = "func()"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        args, kwargs = ts_utils.get_call_arguments(expr)
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_get_call_arguments_positional_args(self):
        """Test extracting positional arguments."""
        code = 'func("arg1", "arg2", 42)'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        args, kwargs = ts_utils.get_call_arguments(expr)
        self.assertEqual(len(args), 3)
        self.assertEqual(args[0], "arg1")
        self.assertEqual(args[1], "arg2")
        self.assertEqual(args[2], 42)

    def test_get_call_arguments_keyword_args(self):
        """Test extracting keyword arguments."""
        code = 'func(name="John", age=30)'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        args, kwargs = ts_utils.get_call_arguments(expr)
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"name": "John", "age": 30})

    def test_get_call_arguments_mixed(self):
        """Test extracting mixed positional and keyword arguments."""
        code = 'func("arg1", 42, name="John", active=True)'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        args, kwargs = ts_utils.get_call_arguments(expr)
        self.assertEqual(len(args), 2)
        self.assertEqual(args[0], "arg1")
        self.assertEqual(args[1], 42)
        self.assertEqual(kwargs["name"], "John")
        self.assertEqual(kwargs["active"], True)

    def test_get_call_arguments_skips_comments(self):
        """Test that comments are skipped in argument parsing."""
        code = """func(
    # This is a comment
    "arg1",
    "arg2"
)"""
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        args, kwargs = ts_utils.get_call_arguments(expr)
        # Comments should not be in args
        self.assertEqual(len(args), 2)
        self.assertNotIn("# This is a comment", args)

    # Tests for node_to_string
    def test_node_to_string_identifier(self):
        """Test converting identifier node to string."""
        code = "x"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_string(expr)
        self.assertEqual(result, "x")

    def test_node_to_string_string(self):
        """Test converting string node to string representation."""
        code = '"hello"'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_string(expr)
        self.assertEqual(result, "'hello'")

    def test_node_to_string_integer(self):
        """Test converting integer node to string."""
        code = "42"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_string(expr)
        self.assertEqual(result, "42")

    def test_node_to_string_boolean(self):
        """Test converting boolean nodes to strings."""
        code = "True"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_string(expr)
        self.assertEqual(result, "True")

    def test_node_to_string_none(self):
        """Test converting None node to string."""
        code = "None"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_string(expr)
        self.assertEqual(result, "None")

    # Tests for node_to_value
    def test_node_to_value_boolean_true(self):
        """Test converting true node to value."""
        code = "True"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertEqual(result, True)

    def test_node_to_value_boolean_false(self):
        """Test converting false node to value."""
        code = "False"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertEqual(result, False)

    def test_node_to_value_none(self):
        """Test converting None node to value."""
        code = "None"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertIsNone(result)

    def test_node_to_value_string(self):
        """Test converting string node to value."""
        code = '"hello"'
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertEqual(result, "hello")

    def test_node_to_value_integer(self):
        """Test converting integer node to value."""
        code = "42"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertEqual(result, 42)

    def test_node_to_value_float(self):
        """Test converting float node to value."""
        code = "3.14"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertAlmostEqual(result, 3.14)

    def test_node_to_value_identifier(self):
        """Test converting identifier node to value."""
        code = "variable_name"
        root = self._parse_code(code)
        expr = root.child(0).child(0)
        result = ts_utils.node_to_value(expr)
        self.assertEqual(result, "variable_name")
