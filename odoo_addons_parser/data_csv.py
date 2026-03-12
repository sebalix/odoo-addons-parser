# Copyright 2023 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import csv
import logging
import pathlib
from typing import Any, Dict, List, Optional

_logger = logging.getLogger(__name__)


class CsvParseError(Exception):
    """Exception raised for CSV parsing errors."""

    pass


class CsvFile:
    """Parse and extract data from Odoo CSV files."""

    def __init__(
        self, module_path: pathlib.Path, file_path: pathlib.Path, loaded: bool = False
    ):
        self.module_path = module_path
        self.module_name = self.module_path.name
        self.file_path = file_path
        self.relative_file_path = self.file_path.relative_to(self.module_path)
        self.loaded = loaded
        self.model_name = self._extract_model_name()
        self.records = self._parse_csv()

    def _extract_model_name(self) -> str:
        """Extract model name from filename.

        E.g. 'res.country.csv' -> 'res.country'.
        """
        if self.file_path.name.endswith(".csv"):
            return self.file_path.stem
        raise CsvParseError(f"Invalid CSV filename: {self.file_path.name}")

    def _parse_csv(self) -> List[Dict[str, Any]]:
        """Parse CSV file and return list of records."""
        records = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as file_:
                reader = csv.DictReader(file_)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        record = self._process_row(row, row_num)
                        if record:
                            records.append(record)
                    except Exception as e:
                        _logger.warning(
                            f"Error processing row {row_num} in {self.file_path}: {e}"
                        )
                        continue
        except Exception as e:
            raise CsvParseError(f"Error reading CSV file {self.file_path}: {e}")
        return records

    def _process_row(
        self, row: Dict[str, str], row_num: int
    ) -> Optional[Dict[str, Any]]:
        """Process a single CSV row into a structured record."""
        if not row:
            return None
        # Extract data from row
        data = {}
        for field_name, value in row.items():
            if ":" in field_name:
                # Handle field references like "country_id:id"
                base_field = field_name.split(":")[0]
                data[base_field] = value
            else:
                data[field_name] = value
        # Validate required fields
        if "id" not in data:
            _logger.warning(f"Row {row_num} missing 'id' field in {self.file_path}")
            return None
        # Create structured record
        record = {
            "id": data["id"],
            "model": self.model_name,
            "file_path": str(self.relative_file_path),
            "data": data,
            "loaded": self.loaded,
        }
        return record

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert parsed CSV data to dictionary format."""
        return {self.model_name: self.records}
