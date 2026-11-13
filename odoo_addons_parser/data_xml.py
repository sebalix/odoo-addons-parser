# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import xml.etree.ElementTree as ET
import xml.parsers.expat
from typing import Dict, Optional, Any
import pathlib
import logging

_logger = logging.getLogger(__name__)

# Root tags can be found in 'odoo/tools/convert.py',
# method 'xml_import.parse()'. They can be nested in data files.
ROOT_TAGS = ("data", "odoo", "openerp")

# Field types whose value is the serialization of the field's children
# (see 'odoo/tools/convert.py', method '_eval_xml()'). Their content is
# already preserved in the raw 'xml' source of the record.
MARKUP_FIELD_TYPES = ("xml", "html")


class XmlParseError(Exception):
    """Exception raised for XML parsing errors."""

    pass


class XmlValidationError(Exception):
    """Exception raised for XML validation errors."""

    pass


def _fixname(name: str) -> str:
    """Expand a namespace name the same way as ElementTree does.

    With namespace processing enabled, expat reports namespaced names as
    'uri}local', while ElementTree exposes them as '{uri}local'.
    """
    return "{" + name if "}" in name else name


def parse_xml_with_positions(
    source: bytes,
) -> tuple[ET.Element, Dict[ET.Element, tuple[int, int]]]:
    """Parse an XML source and return the root node with element positions.

    Build the same element tree as `ET.parse()` (same expat parser under
    the hood), and record for each element the byte span of its source:
    a tuple ``(start_index, end_index)``, where 'start_index' is the
    position of the opening tag's '<' in the source, and 'end_index' the
    position reported by expat at the end event (position of the closing
    tag's '<' for regular elements, position right after the tag's final
    '>' for empty/self-closing elements).
    """
    parser = xml.parsers.expat.ParserCreate(None, "}")
    # Same option as 'ET.XMLParser'
    parser.buffer_text = True
    builder = ET.TreeBuilder()
    stack = []
    positions = {}

    def start(name, attrs):
        attrs = {_fixname(attr): value for attr, value in attrs.items()}
        stack.append((builder.start(_fixname(name), attrs), parser.CurrentByteIndex))

    def end(name):
        element, start_index = stack.pop()
        positions[element] = (start_index, parser.CurrentByteIndex)
        builder.end(_fixname(name))

    def chardata(text):
        builder.data(text)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chardata
    parser.Parse(source, True)
    return builder.close(), positions


def _slice_source(source: bytes, start: int, end_index: int) -> bytes:
    """Return the raw source of an element, from its opening tag's '<'
    to the end of its closing tag (or of its self-closing tag)."""
    if end_index > start and source[end_index : end_index + 2] == b"</":
        # Regular element: 'end_index' is the position of the closing tag's '<'
        return source[start : source.index(b">", end_index) + 1]
    if end_index > start and source[end_index - 1 : end_index] == b">":
        # Empty element: 'end_index' is the position right after the tag's '>'
        return source[start:end_index]
    # Fallback: search the end of the opening tag, skipping quoted '>' characters
    quote = None
    for index in range(start, len(source)):
        char = source[index : index + 1]
        if quote:
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == ">":
            return source[start : index + 1]
    raise ValueError("unterminated tag")


class XmlFile:
    """XML backend data file.

    Such file could contain record definitions such as views, menu, records...
    """

    def __init__(
        self, module_path: pathlib.Path, file_path: pathlib.Path, loaded: bool = False
    ):
        self.module_path = module_path
        self.module_name = self.module_path.name
        self.file_path = file_path
        self.relative_file_path = self.file_path.relative_to(self.module_path)
        self.loaded = loaded
        self._source = b""
        self._positions: Dict[ET.Element, tuple[int, int]] = {}
        self.elements = self._parse_file()

    def _parse_file(self) -> Dict:
        """Parse the XML file and extract relevant elements."""
        try:
            self._source = self.file_path.read_bytes()
            root, self._positions = parse_xml_with_positions(self._source)
            # Handle both 'odoo' and 'openerp' root tags
            if root.tag not in ROOT_TAGS:
                _logger.warning(f"Unexpected root tag '{root.tag}' in {self.file_path}")
                return {tag: [] for tag in TAGS}
            return self._parse_root_node(root)
        except xml.parsers.expat.ExpatError as e:
            _logger.warning(f"XML parse error in {self.file_path}: {e}")
            return {tag: [] for tag in TAGS}
        except NotImplementedError:
            raise
        except Exception as e:
            _logger.warning(
                f"Unexpected error parsing {self.file_path}: {e}", exc_info=True
            )
            return {tag: [] for tag in TAGS}

    def _parse_root_node(self, root):
        elements = {tag: [] for tag in TAGS}
        # Process direct children
        for node in root:
            if node.tag in IGNORED_TAGS:
                continue
            # Root tags ('odoo', 'openerp', 'data') can be nested in data files
            # (see 'odoo/tools/convert.py', method 'xml_import.parse()'):
            # process them as root nodes
            if node.tag in ROOT_TAGS:
                data_elements = self._parse_root_node(node)
                for tag, elts in data_elements.items():
                    elements[tag].extend(elts)
            # Easy way to know when new Odoo releases introduce new tags: raise
            elif node.tag not in TAGS:
                raise NotImplementedError(f"Tag {node.tag} is not supported.")
            try:
                parser = TAGS.get(node.tag)
                if parser:
                    try:
                        element = parser(self, node, root_node=root)
                        elements[node.tag].append(element)
                    except (XmlValidationError, XmlParseError) as e:
                        _logger.debug(
                            f"Skipping invalid {node.tag} in {self.file_path}: {e}"
                        )
                        continue
                    except Exception as e:
                        _logger.warning(
                            f"Unexpected error parsing {node.tag} in {self.file_path}: {e}",
                            exc_info=True,
                        )
                        continue
            except Exception as e:
                _logger.warning(
                    f"Failed to parse XML elements in {self.file_path}: {e}",
                    exc_info=True,
                )
                continue
            # Recursively process nested elements for tags that can contain children
            if node.tag in ["menuitem"]:
                nested_elements = self._parse_root_node(node)
                for tag, elts in nested_elements.items():
                    elements[tag].extend(elts)
        return elements

    def get_source(self, element: ET.Element) -> Optional[str]:
        """Return the raw source of an element, from its opening tag's '<'
        to the end of its closing tag (or of its self-closing tag).

        Return 'None' if the source is not available (e.g. element not
        found in the recorded positions).
        """
        span = self._positions.get(element)
        if span is None:
            return None
        start, end_index = span
        try:
            raw = _slice_source(self._source, start, end_index)
        except ValueError:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            _logger.warning(f"Unable to decode XML source as UTF-8 in {self.file_path}")
            return raw.decode("latin-1")

    def to_dict(self) -> Dict:
        """Convert all elements to simplified dictionary format."""
        result = {}
        for tag, elts in self.elements.items():
            for elt in elts:
                model_name = elt.model  # Key is the record's model
                if model_name not in result:
                    result[model_name] = []
                result[model_name].append(elt.to_dict())
        return result


class XmlTag:
    """Base class for Odoo XML tags (record, template, etc.)."""

    _tag = None  # Defined by subclasses
    _tag_required_attrs = ("id",)
    _tag_name_attr = "id"

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        root_node: ET.Element,
        model: str,
    ):
        self.xmlfile = xmlfile
        self.node = node
        self.root_node = root_node
        self._check_node()
        self.id_ = node.get("id")
        self.model = model
        self.type_ = self._get_type()
        self.name = self._extract_name()
        self.data = self._extract_data()
        self.loaded = self.xmlfile.loaded
        self.noupdate = self._get_noupdate()

    def _check_node(self):
        """Check node validity."""
        for attr in self._tag_required_attrs:
            if not self.node.get(attr):
                raise XmlValidationError(
                    f"Missing required 'id' attribute in <{self._tag}> tag in"
                    f" {self.xmlfile.file_path}"
                )

    def _get_type(self) -> Optional[str]:
        return None

    def _extract_name(self) -> Optional[str]:
        """Extract the name field from the tag."""
        return self.node.get(self._tag_name_attr)

    def _extract_data(self) -> Dict:
        """Extract data from the tag (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _extract_data()")

    def _get_noupdate(self) -> bool:
        """Extract noupdate attribute from root node."""
        noupdate = self.root_node.attrib.get("noupdate", "")
        noupdate = noupdate.strip() if noupdate else noupdate
        if not noupdate:
            return False
        # Values checked copied from 'odoo.tools.convert.str2bool'
        return noupdate.lower() not in ("0", "false", "off")

    def _get_xml(self) -> str:
        """Return the raw XML source of the tag, from its opening tag
        to its closing tag."""
        source = self.xmlfile.get_source(self.node)
        if source is None:
            # Fallback: re-serialize the element from the parsed tree
            self.node.tail = None
            source = ET.tostring(self.node, encoding="unicode")
        return source

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        result = {
            "id": self.id_,
            "model": self.model,
            "file_path": str(self.xmlfile.relative_file_path),
            "data": self.data,
            "xml": self._get_xml(),
            "loaded": self.loaded,
        }
        if self.name:
            result["name"] = self.name
        if self.type_:
            result["type"] = self.type_
        if self.noupdate:
            result["noupdate"] = True
        return result


class XmlSpecialTag(XmlTag):
    """Base class for XML special tags with model and attribute-to-field mappings.

    Subclasses should define:
    - _model: model name this tag represents
    - _attribute_mapping: dict mapping XML attributes to Odoo fields
    - _default_data: dict of default field values
    """

    _model = None  # Defined by subclasses
    _attribute_mapping: Dict[str, str] = {}
    _default_data: Dict[str, Any] = {}

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        root_node: ET.Element,
    ):
        model = self._model
        if callable(self._model):
            model = self._model(xmlfile, node)
        super().__init__(xmlfile, node, root_node, model=model)

    def _extract_data(self) -> Dict:
        """Extract data using configured attribute mappings."""
        data = self._default_data.copy()
        for xml_attr, odoo_field in self._attribute_mapping.items():
            if value := self.node.get(xml_attr):
                data[odoo_field] = value
        return data


class XmlRecord(XmlTag):
    """Representation of an Odoo XML record (`<record>` tag)."""

    _tag = "record"
    _tag_required_attrs = ("id", "model")

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        root_node: ET.Element,
    ):
        model = node.get("model")
        if model is None:
            raise XmlValidationError(
                "Missing required 'model' attribute in <record> tag"
            )
        super().__init__(xmlfile, node, root_node, model=model)
        self.target_model = self._extract_target_model()

    def _get_type(self) -> Optional[str]:
        return "normal" if self.model == "ir.ui.view" else None

    def _extract_name(self) -> Optional[str]:
        """Extract the name field from the record."""
        name_field = self._find_field("name")
        return name_field.text if name_field is not None else None

    def _find_field(self, field_name: str) -> Optional[ET.Element]:
        """Find a field element by name."""
        for field in self.node.findall("field"):
            if field.get("name") == field_name:
                return field
        return None

    def _extract_data(self) -> Dict:
        """Extract all field data from the record."""
        data = {}
        for field in self.node.findall("field"):
            if field_name := field.get("name"):
                # Skip markup fields: their value is the serialization of
                # the field's children, already preserved in the raw 'xml'
                # source of the record
                if field.get("type") in MARKUP_FIELD_TYPES:
                    continue
                # Field value: mirror the source priority of Odoo (see
                # 'odoo/tools/convert.py', methods '_tag_record()' and
                # '_eval_xml()'); the value-bearing attributes are mutually
                # exclusive in practice
                if search := field.get("search"):
                    data[field_name] = search
                elif ref := field.get("ref"):
                    data[field_name] = ref
                elif eval_expr := field.get("eval"):
                    data[field_name] = eval_expr
                elif file_path := field.get("file"):
                    data[field_name] = file_path
                else:
                    # Otherwise use the text content
                    data[field_name] = field.text
        return data

    def _extract_target_model(self) -> Optional[str]:
        """Extract the target model this record applies to."""
        if self.model in ("ir.ui.view",):
            return self.data.get("model")
        elif self.model in ("ir.actions.act_window",):
            return self.data.get("res_model")
        elif self.model in ("ir.model.access", "ir.rule"):
            model_id = self.data.get("model_id", "")
            return model_id.split(".")[-1] if model_id else None
        return None

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        result = super().to_dict()
        if self.target_model:
            result["target_model"] = self.target_model
        return result


class XmlTemplate(XmlTag):
    """Representation of an Odoo XML template (`<template>` tag)."""

    _tag = "template"

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        root_node: ET.Element,
    ):
        super().__init__(xmlfile, node, root_node, model="ir.ui.view")

    def _get_type(self) -> str:
        # Templates are always ir.ui.view records with type 'qweb'
        return "qweb"

    def _extract_data(self) -> Dict:
        """Extract template data and convert to ir.ui.view format."""
        data = {}
        # Handle template inheritance if present
        if inherit_id := self.node.get("inherit_id"):
            data["inherit_id"] = inherit_id
        return data


class XmlMenuItem(XmlSpecialTag):
    """Representation of an Odoo XML menuitem (`<menuitem>` tag)."""

    _model = "ir.ui.menu"
    _tag = "menuitem"
    _tag_name_attr = "name"

    _attribute_mapping = {
        "name": "name",
        "parent": "parent_id",
        "action": "action",
        "groups": "groups_id",
    }

    def _extract_data(self) -> Dict:
        data = super()._extract_data()
        if not data.get("parent_id") and self.root_node.tag == "menuitem":
            data["parent_id"] = self.root_node.get("id")
        return data


class XmlAsset(XmlSpecialTag):
    """Representation of an Odoo XML asset (`<asset>` tag)."""

    _model = lambda self, xmlfile, node: (  # noqa: E731
        "theme.ir.asset" if xmlfile.module_name.startswith("theme_") else "ir.asset"
    )
    _tag = "asset"
    _tag_name_attr = "name"
    _attribute_mapping = {
        "name": "name",
    }


class XmlReport(XmlSpecialTag):
    """Representation of an Odoo XML report (`<report>` tag)."""

    _model = "ir.actions.report"
    _tag = "report"
    _tag_name_attr = "string"
    _attribute_mapping = {
        "string": "name",
        "model": "model",
        "report_type": "report_type",
        "name": "report_name",
        "file": "report_file",
        "print_report_name": "print_report_name",
    }


class XmlActWindow(XmlSpecialTag):
    """Representation of an Odoo XML act_window (`<act_window>` tag)."""

    _model = "ir.actions.act_window"
    _tag = "act_window"
    _tag_name_attr = "name"
    _attribute_mapping = {
        "name": "name",
        "res_model": "res_model",
        "src_model": "src_model",
        "view_mode": "view_mode",
        "view_type": "view_type",
        "target": "target",
        "multi": "multi",
        "key2": "key2",
        "groups": "groups_id",
        "context": "context",
    }
    _default_data = {"type": "ir.actions.act_window"}


# Backend tags can be found in 'odoo/tools/convert.py',
# method 'xml_import.__init__()'.
# NOTE:
#   - only tags from Odoo >= 11.0 are supported. Tags such as <workflow> or
#     <ir_set> are not part of them (dropped in Odoo 11.0), and are ignored
#     (see IGNORED_TAGS).
#   - <delete>, <function> and <assert> tags are not added neither as they're not
#     representing resources that can be used in code or reverse dependencies
TAGS = {
    "record": XmlRecord,
    "template": XmlTemplate,
    "menuitem": XmlMenuItem,
    "asset": XmlAsset,
    "report": XmlReport,
    "act_window": XmlActWindow,
}
IGNORED_TAGS = [
    "delete",
    "function",
    "assert",  # Odoo <= 12.0, old way of writing tests
    "xpath",  # OCA/OpenUpgrade#19.0 using it in noupdate.xml files
    "wizard",  # Odoo <= 7.0, dead code (not handled by Odoo >= 8.0 either)
    "workflow",  # Odoo <= 10.0, dropped in Odoo 11.0
    "ir_set",  # Odoo <= 10.0, deprecated since 9.0, dropped in Odoo 11.0
    "url",  # Odoo 8.0 only
]
