# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import xml.etree.ElementTree as ET
from typing import Dict, Optional
import pathlib
import logging

_logger = logging.getLogger(__name__)


class XmlParseError(Exception):
    """Exception raised for XML parsing errors."""

    pass


class XmlValidationError(Exception):
    """Exception raised for XML validation errors."""

    pass


class XmlFile:
    """XML data file.

    Such file could contain record definitions such as views, menu, records...

    It has three status:
        - data: loaded by the manifest file in `data` key
        - demo: loaded by the manifest file in `demo` key
        - not_loaded: not loaded by the manifest file (e.g a XSD schema)
    """

    def __init__(self, module_name: str, file_path: pathlib.Path, status="not_loaded"):
        self.module_name = module_name
        self.file_path = file_path
        self.status = status
        self.elements = self._parse_file()

    def _parse_file(self) -> Dict:
        """Parse the XML file and extract relevant elements."""
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            # Handle both 'odoo' and 'openerp' root tags
            if root.tag not in ("odoo", "openerp"):
                _logger.warning(f"Unexpected root tag '{root.tag}' in {self.file_path}")
                return {tag: [] for tag in TAGS}
            return self._parse_root_node(root)
        except ET.ParseError as e:
            _logger.warning(f"XML parse error in {self.file_path}: {e}")
            return {tag: [] for tag in TAGS}
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
            # <data> could exist alongside other tags, process it as a root node
            if node.tag == "data":
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
                        element = parser(
                            self, node, file_path=self.file_path, root_node=root
                        )
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

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        file_path: pathlib.Path,
        root_node: ET.Element,
        model: str,
    ):
        self.xmlfile = xmlfile
        self.node = node
        self.file_path = file_path
        self.root_node = root_node
        self._check_node()
        self.id_ = node.get("id")
        self.model = model
        self.type_ = self._get_type()
        self.name = self._extract_name()
        self.data = self._extract_data()
        self.status = self.xmlfile.status
        self.noupdate = self._get_noupdate()

    def _check_node(self):
        """Check node validity (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _check_node()")

    def _get_type(self) -> Optional[str]:
        return None

    def _extract_name(self) -> Optional[str]:
        """Extract the name field from the tag."""
        # Default implementation: use ID as name
        return self.id_ if self.id_ else None

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

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        result = {
            "id": self.id_,
            "model": self.model,
            "file_path": str(self.file_path),
            "data": self.data,
            "status": self.status,
        }
        if self.name:
            result["name"] = self.name
        if self.type_:
            result["type"] = self.type_
        if self.noupdate:
            result["noupdate"] = True
        return result


class XmlRecord(XmlTag):
    """Representation of an Odoo XML record (`<record>` tag)."""

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        file_path: pathlib.Path,
        root_node: ET.Element,
    ):
        model = node.get("model")
        if model is None:
            raise XmlValidationError(
                "Missing required 'model' attribute in <record> tag"
            )
        super().__init__(xmlfile, node, file_path, root_node, model=model)
        self.target_model = self._extract_target_model()

    def _check_node(self):
        if not self.node.get("id"):
            raise XmlValidationError(
                f"Missing required 'id' attribute in <record> tag in {self.file_path}"
            )
        if not self.node.get("model"):
            raise XmlValidationError(
                f"Missing required 'model' attribute in <record> tag in {self.file_path}"
            )

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
                # If field has a 'ref' attribute, use that as the value
                # This handles cases like <field name="inherit_id" ref="base.view_id"/>
                if field.get("ref"):
                    data[field_name] = field.get("ref")
                else:
                    # For XML fields, extract the full XML content including child elements
                    if self.model == "ir.ui.view" and field.get("name") == "arch":
                        arch = "".join(
                            ET.tostring(child, encoding="unicode") for child in field
                        )
                        data[field_name] = (field.text or "") + arch
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

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        file_path: pathlib.Path,
        root_node: ET.Element,
    ):
        super().__init__(xmlfile, node, file_path, root_node, model="ir.ui.view")

    def _check_node(self):
        id_ = self.node.get("id")
        if not id_:
            raise XmlValidationError(
                f"Missing required 'id' attribute in <template> tag in {self.file_path}"
            )

    def _get_type(self) -> str:
        # Templates are always ir.ui.view records with type 'qweb'
        return "qweb"

    def _extract_data(self) -> Dict:
        """Extract template data and convert to ir.ui.view format."""
        data = {
            # Extract arch field - this contains the template content
            "arch": ET.tostring(self.node, encoding="unicode"),
        }
        # Handle template inheritance if present
        if inherit_id := self.node.get("inherit_id"):
            data["inherit_id"] = inherit_id
        return data


class XmlMenuItem(XmlTag):
    """Representation of an Odoo XML menuitem (`<menuitem>` tag)."""

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        file_path: pathlib.Path,
        root_node: ET.Element,
    ):
        super().__init__(xmlfile, node, file_path, root_node, model="ir.ui.menu")

    def _check_node(self):
        if not self.node.get("id"):
            raise XmlValidationError(
                f"Missing required 'id' attribute in <menuitem> tag in {self.file_path}"
            )

    def _extract_data(self) -> Dict:
        """Extract menuitem data and convert to ir.ui.menu format."""
        data = {}
        if name := self.node.get("name"):
            data["name"] = name
        if parent := self.node.get("parent"):
            data["parent_id"] = parent
        if action := self.node.get("action"):
            data["action"] = action
        if sequence := self.node.get("sequence"):
            data["sequence"] = int(sequence)
        if groups := self.node.get("groups"):
            data["groups_id"] = groups
        return data

    def _extract_name(self) -> Optional[str]:
        """Extract the name field from the menuitem."""
        return self.node.get("name")

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        result = super().to_dict()
        # Always include name field for menuitems, even if None
        # This matches the expected test format
        result["name"] = self.name
        return result


class XmlAsset(XmlTag):
    """Representation of an Odoo XML asset (`<asset>` tag)."""

    def __init__(
        self,
        xmlfile: XmlFile,
        node: ET.Element,
        file_path: pathlib.Path,
        root_node: ET.Element,
    ):
        model = (
            "theme.ir.asset" if xmlfile.module_name.startswith("theme_") else "ir.asset"
        )
        super().__init__(xmlfile, node, file_path, root_node, model=model)

    def _check_node(self):
        if not self.node.get("id"):
            raise XmlValidationError(
                f"Missing required 'id' attribute in <asset> tag in {self.file_path}"
            )

    def _extract_data(self) -> Dict:
        """Extract asset data and convert to ir.asset format."""
        data = {}
        if name := self.node.get("name"):
            data["name"] = name
        return data

    def _extract_name(self) -> Optional[str]:
        """Extract the name field from the asset."""
        return self.node.get("name")


# Root tags can be found in 'odoo/tools/convert.py', method 'xml_import.__init__()'
# NOTE:
#   - only root tags from Odoo >= 11.0 are supported. Tags such as <workflow> or
#     <ir_set> are not part of them (dropped in Odoo 11.0).
#   - <delete>, <function> and <assert> tags are not added neither as they're not
#     representing resources that can be used in code or reverse dependencies
TAGS = {
    "record": XmlRecord,
    "template": XmlTemplate,
    "menuitem": XmlMenuItem,
    "asset": XmlAsset,
    # TODO add support for these root tags:
    # <report> (Odoo <= 16.0, create an 'ir.actions.report' record)
    # <act_window> (Odoo <= 16.0)
}
IGNORED_TAGS = [
    "delete",
    "function",
    "assert",  # Odoo <= 12.0, old way of writing tests
]
