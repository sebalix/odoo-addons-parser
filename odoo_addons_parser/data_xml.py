# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import pathlib
import logging

_logger = logging.getLogger(__name__)

# TODO add support for root tags:
#   - <template>
#   - <menuitem>
#   - <report> (old Odoo versions)
#   - <act_window> (old Odoo versions)


class XmlRecord:
    """Representation of an Odoo XML record (`<record>` tag)."""

    def __init__(self, record_node: ET.Element, file_path: pathlib.Path):
        self.record_node = record_node
        self.file_path = file_path
        self.id_ = record_node.get("id")
        self.model = record_node.get("model")
        self.type_ = "normal" if self.model == "ir.ui.view" else None
        self.name = self._extract_name()
        self.data = self._extract_record_data()
        self.target_model = self._extract_target_model()

    def _extract_name(self) -> Optional[str]:
        """Extract the name field from the record."""
        name_field = self._find_field("name")
        return name_field.text if name_field is not None else None

    def _find_field(self, field_name: str) -> Optional[ET.Element]:
        """Find a field element by name."""
        for field in self.record_node.findall("field"):
            if field.get("name") == field_name:
                return field
        return None

    def _extract_record_data(self) -> Dict:
        """Extract all field data from the record."""
        data = {}
        for field in self.record_node.findall("field"):
            field_name = field.get("name")
            if field_name:
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
                        data[field_name] = field.text + arch
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
        result = {
            "id": self.id_,
            "model": self.model,
            "file_path": str(self.file_path),
        }
        if self.name:
            result["name"] = self.name
        if self.type_:
            result["type"] = self.type_
        if self.target_model:
            result["target_model"] = self.target_model
        if self.data:
            result["data"] = self.data
        return result


class XmlFile:
    """XML data file.

    Such file could contain record definitions such as views, menu, records...
    """

    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path
        self.records = self._parse_file()

    def _parse_file(self) -> List[XmlRecord]:
        """Parse the XML file and extract all <record> elements."""
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            # Handle both 'odoo' and 'openerp' root tags
            if root.tag not in ("odoo", "openerp"):
                _logger.warning(f"Unexpected root tag '{root.tag}' in {self.file_path}")
                return []
            records = []
            for record_node in root.findall("record"):
                try:
                    record_id = record_node.get("id")
                    record_model = record_node.get("model")
                    # Skip if essential attributes are missing
                    if not record_id or not record_model:
                        _logger.debug(
                            f"Skipping record in {self.file_path}: "
                            f"missing id or model attribute"
                        )
                        continue
                    xml_record = XmlRecord(record_node, self.file_path)
                    records.append(xml_record)
                except Exception as e:
                    _logger.warning(
                        f"Failed to parse record in {self.file_path}: {e}",
                        exc_info=True,
                    )
                    continue
            return records
        except ET.ParseError as e:
            _logger.warning(f"XML parse error in {self.file_path}: {e}")
            return []
        except Exception as e:
            _logger.warning(
                f"Unexpected error parsing {self.file_path}: {e}", exc_info=True
            )
            return []

    def to_dict(self) -> Dict:
        """Convert all records to simplified dictionary format."""
        result = {}
        for record in self.records:
            model_name = record.model  # Key is the record's model
            if model_name not in result:
                result[model_name] = []  # Direct list of records
            result[model_name].append(record.to_dict())
        return result
