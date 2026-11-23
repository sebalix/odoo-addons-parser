# Copyright 2023 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import ast
import logging
import os
import pathlib
import typing

import pygount

from .code import PyFile
from .data_csv import CsvFile
from .data_xml import XmlFile

if typing.TYPE_CHECKING:
    from .repository import RepositoryParser

_logger = logging.getLogger(__name__)

MANIFEST_FILES = ["__openerp__.py", "__manifest__.py"]


class ModuleParser:
    def __init__(
        self,
        folder_path: typing.Union[str, os.PathLike],
        languages: tuple = ("Python", "XML", "CSS", "JavaScript"),
        repo_parser: typing.Optional["RepositoryParser"] = None,
        code_stats: bool = True,
        scan_models: bool = True,
        scan_data: bool = True,
    ):
        self.folder_path = pathlib.Path(folder_path).resolve()
        if not self.folder_path.exists():
            raise ValueError(f"'{folder_path}' doesn't exist")
        if not self._get_manifest_path(self.folder_path):
            raise ValueError(f"'{folder_path}' is not an Odoo module")
        self.languages = languages
        self.repo_parser = repo_parser
        self._code_stats = code_stats
        self._scan_models = scan_models
        self._scan_data = scan_data
        self.summary = pygount.ProjectSummary()
        self.code = {}
        self.models = {}
        self.data = {}
        self.demo = {}
        self._owned_models = set()
        self._run()

    @staticmethod
    def _get_manifest_path(folder_path):
        for manifest_name in MANIFEST_FILES:
            manifest_path = pathlib.Path(folder_path, manifest_name)
            if manifest_path.exists():
                return manifest_path

    @property
    def name(self) -> str:
        return self.folder_path.name

    @property
    def file_paths(self) -> list[pathlib.Path]:
        paths = []
        for dirpath, _dirnames, filenames in os.walk(
            self.folder_path, followlinks=False
        ):
            for f in filenames:
                file_path = pathlib.Path(dirpath).joinpath(f)
                if file_path.is_symlink():
                    continue
                paths.append(file_path)
        return paths

    @property
    def manifest(self) -> dict:
        manifest_path = self._get_manifest_path(self.folder_path)
        with open(manifest_path) as file_:
            try:
                manifest = ast.literal_eval(file_.read())
            except ValueError:
                return {}
            return manifest

    def _run(self):
        for file_path in self.file_paths:
            if self._code_stats:
                self._run_code_stats(file_path)
            if self._scan_models and file_path.suffix == ".py":
                self._run_scan_models(file_path)
            if self._scan_data and file_path.suffix in [".xml", ".csv"]:
                self._run_scan_data(file_path)
        if self._scan_models:
            self._finalize_models()
        if self._code_stats:
            summaries = dict.fromkeys(self.languages, 0)
            for summary in self.summary.language_to_language_summary_map.values():
                for language in self.languages:
                    if not summary.language.startswith(language):
                        continue
                    summaries[language] += summary.source_count
            self.code = summaries

    def _run_code_stats(self, file_path: pathlib.Path):
        try:
            source_analysis = pygount.SourceAnalysis.from_file(
                file_path,
                group=self.folder_path.name,
                encoding="utf-8",
            )
        except Exception:
            _logger.warning(
                f"Unable to analyze {file_path}", stack_info=True, exc_info=True
            )
        else:
            self.summary.add(source_analysis)

    @staticmethod
    def _get_inherit_list(inherit) -> list:
        """Return an `_inherit` value as a list of model names."""
        if not inherit:
            return []
        if isinstance(inherit, str):
            return [inherit]
        return list(inherit)

    @classmethod
    def _merge_inherit(cls, current, new):
        """Merge two `_inherit` values, keeping declaration order."""
        if not current:
            return new
        if not new:
            return current
        values = []
        for inherit in (current, new):
            for value in cls._get_inherit_list(inherit):
                if value not in values:
                    values.append(value)
        if not values:
            return None
        # Keep the string representation when there is a single value declared
        # as a string.
        if isinstance(current, str) and isinstance(new, str) and len(values) == 1:
            return values[0]
        return values

    @classmethod
    def _is_model_owner(cls, model, key) -> bool:
        """Check if the module implements the model declared by `model`.

        A `_name` declaration inheriting itself redefines a model coming from
        another module, it doesn't mean current module implements it.
        """
        return (
            key is not None
            and model.get("name") == key
            and key not in cls._get_inherit_list(model.get("inherit"))
        )

    def _run_scan_models(self, file_path: pathlib.Path):
        try:
            pyfile = PyFile(file_path, module_path=self.folder_path)
        except RuntimeError as exc:
            _logger.warning(str(exc))
            return
        data = pyfile.to_dict()
        for model in data["models"].values():
            key = model.get("name") or model.get("inherit")
            if isinstance(key, list):
                # Data model declared without `_name` but with `_inherit = [...]`,
                # e.g. `_inherit = ['res.partner']`, considers - like Odoo - first
                # element as current model name
                key = key[0]
            if self._is_model_owner(model, key):
                self._owned_models.add(key)
            current = self.models.get(key)
            if current is None:
                self.models[key] = dict(model)
                continue

            # Merge fields and methods, the latest declaration wins.
            fields = dict(current.get("fields") or {})
            fields.update(model.get("fields") or {})
            methods = dict(current.get("methods") or {})
            methods.update(model.get("methods") or {})
            inherit = self._merge_inherit(current.get("inherit"), model.get("inherit"))
            inherits = dict(current.get("inherits") or {})
            inherits.update(model.get("inherits") or {})

            # A declaration with `_name` is the original/new definition of the
            # data model for current module. Its metadata (file path, class
            # name, type, `_order`...) must prevail over the ones coming from
            # `_inherit`-only declarations, whatever the scan order.
            if key is not None and model.get("name") == key and not current.get("name"):
                aggregated = dict(model)
            else:
                aggregated = current
            if fields:
                aggregated["fields"] = fields
            if methods:
                aggregated["methods"] = methods
            if inherit is not None:
                aggregated["inherit"] = inherit
            if inherits:
                aggregated["inherits"] = inherits
            self.models[key] = aggregated

    def _finalize_models(self):
        """Remove self-inheritance from models implemented by this module."""
        for key in self._owned_models:
            model = self.models.get(key)
            if not model or "inherit" not in model:
                continue
            inherit = model["inherit"]
            values = []
            for value in self._get_inherit_list(inherit):
                if value != key and value not in values:
                    values.append(value)
            if not values:
                del model["inherit"]
            elif isinstance(inherit, str):
                model["inherit"] = values[0]
            else:
                model["inherit"] = values

    def _run_scan_data(self, file_path: pathlib.Path):
        """Parse XML and CSV files and extract data records."""
        manifest = self.manifest
        data_paths = [pathlib.Path(path) for path in manifest.get("data", [])]
        demo_paths = [pathlib.Path(path) for path in manifest.get("demo", [])]
        try:
            # Make file path relative to module path for consistency
            relative_file_path = file_path.relative_to(self.folder_path)
            # Ignore frontend (static) and tests files
            if relative_file_path.parts[0] in ("static", "tests"):
                return
            # Backend files
            else:
                # Classify the file as data/demo or not loaded
                demo = loaded = False
                if relative_file_path in data_paths:
                    loaded = True
                elif relative_file_path in demo_paths:
                    loaded = True
                    demo = True
                # Handle different file types
                if file_path.suffix == ".xml":
                    xml_file = XmlFile(self.folder_path, file_path, loaded=loaded)
                    file_data = xml_file.to_dict()
                elif file_path.suffix == ".csv":
                    csv_file = CsvFile(self.folder_path, file_path, loaded=loaded)
                    file_data = csv_file.to_dict()
                else:
                    return
                # Merge into self.data or self.demo structure
                collection = self.demo if demo else self.data
                for model_name, records in file_data.items():
                    if model_name not in collection:
                        collection[model_name] = []
                    collection[model_name].extend(records)
        except NotImplementedError:
            _logger.error(f"Unable to parse data file {file_path}")
            raise
        except Exception as exc:
            _logger.warning(f"Unable to parse data file {file_path}: {exc}")

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "manifest": self.manifest,
        }
        if self._code_stats:
            data["code"] = self.code
        if self._scan_models:
            data["models"] = self.models
        if self._scan_data:
            if self.data:
                data["data"] = self.data
            if self.demo:
                data["demo"] = self.demo
        return data
