# Copyright 2023 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import ast
import logging
import os
import pathlib
import typing

import pygount

from .code import PyFile
from .data_xml import XmlBackendFile, XmlFrontendFile

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
        self.backend_data = {}
        self.frontend_data = []
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
            if self._scan_data and file_path.suffix == ".xml":
                self._run_scan_data(file_path)
        if self._code_stats:
            summaries = dict.fromkeys(self.languages, 0)
            for summary in self.summary.language_to_language_summary_map.values():
                for language in self.languages:
                    if not summary.language.startswith(language):
                        continue
                    summaries[language] += summary.code_count
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
            if key not in self.models:
                self.models.setdefault(key, {}).update(model)
            else:
                if model.get("fields"):
                    self.models[key].setdefault("fields", {}).update(model["fields"])
                if model.get("methods"):
                    self.models[key].setdefault("methods", {}).update(model["methods"])
                # Handle cases where more than one file declare the same data model
                # in current scanned module, and one of them is the original
                # declaration w/o inheritance).
                #   => Consider the data model as original/new for current module.
                if model.get("name") == key and self.models[key].get("inherit") == key:
                    self.models[key]["name"] = key
                    del self.models[key]["inherit"]

    def _run_scan_data(self, file_path: pathlib.Path):
        """Parse XML files and extract data records."""
        manifest = self.manifest
        data_paths = [pathlib.Path(path) for path in manifest.get("data", [])]
        demo_paths = [pathlib.Path(path) for path in manifest.get("demo", [])]
        try:
            # Make file path relative to module path for consistency
            relative_file_path = file_path.relative_to(self.folder_path)
            # Frontend (static) files
            if relative_file_path.parts[0] == "static":
                xml_file = XmlFrontendFile(self.name, file_path)
                xml_data = xml_file.to_dict()
                for key, templates in xml_data.items():
                    if key not in self.frontend_data:
                        self.frontend_data[key] = []
                    self.frontend_data[key].extend(templates)
            # Backend files
            else:
                # Classify the file as data/demo or not loaded
                if relative_file_path in data_paths:
                    status = "data"
                elif relative_file_path in demo_paths:
                    status = "demo"
                else:
                    status = "not_loaded"
                xml_file = XmlBackendFile(self.name, file_path, status=status)
                xml_data = xml_file.to_dict()
                # Merge into self.backend_data structure
                for model_name, records in xml_data.items():
                    if model_name not in self.backend_data:
                        self.backend_data[model_name] = []
                    # Update file paths to be relative
                    # FIXME: should be done in XmlTag.to_dict(), not there
                    for record in records:
                        record["file_path"] = str(relative_file_path)
                    self.backend_data[model_name].extend(records)
        except NotImplementedError:
            _logger.error(f"Unable to parse XML file {file_path}")
            raise
        except Exception as exc:
            _logger.warning(f"Unable to parse XML file {file_path}: {exc}")

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "manifest": self.manifest,
        }
        if self._code_stats:
            data["code"] = self.code
        if self._scan_models:
            data["models"] = self.models
        if self._scan_data and self.backend_data:
            data["backend_data"] = self.backend_data
        if self._scan_data and self.frontend_data:
            data["frontend_data"] = self.frontend_data
        return data
