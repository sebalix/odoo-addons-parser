# Copyright 2023 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import ast
import logging
import os
import pathlib
import typing

import pygount

from .code import PyFile

if typing.TYPE_CHECKING:
    from .repository import RepositoryParser

_logger = logging.getLogger(__name__)


class ModuleParser:
    def __init__(
        self,
        folder_path: typing.Union[str, os.PathLike],
        languages: tuple = ("Python", "XML", "CSS", "JavaScript"),
        repo_parser: typing.Optional["RepositoryParser"] = None,
        scan_models: bool = True,
    ):
        self.folder_path = pathlib.Path(folder_path).resolve()
        self.languages = languages
        self.repo_parser = repo_parser
        self._scan_models = scan_models
        self.summary = pygount.ProjectSummary()
        self.models = {}
        self._run()

    @property
    def name(self) -> str:
        return self.folder_path.name

    @property
    def file_paths(self) -> list[os.PathLike]:
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
        for manifest_name in ("__openerp__.py", "__manifest__.py"):
            manifest_path = pathlib.Path(self.folder_path, manifest_name)
            if manifest_path.exists():
                with open(manifest_path) as file_:
                    try:
                        manifest = ast.literal_eval(file_.read())
                    except ValueError:
                        return {}
                    return manifest
        return {}

    def _run(self):
        for file_path in self.file_paths:
            self._code_stats(file_path)
            if self._scan_models:
                self._scan_models_from_file(file_path)

    def _code_stats(self, file_path: os.PathLike):
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

    def _scan_models_from_file(self, file_path: os.PathLike):
        try:
            pyfile = PyFile(file_path, module_path=self.folder_path)
        except ValueError:
            return
        except RuntimeError as exc:
            _logger.warning(str(exc))
            return
        data = pyfile.to_dict()
        for model in data["models"].values():
            key = model.get("name") or model.get("inherit")
            if key not in self.models:
                self.models.setdefault(key, {}).update(model)
            else:
                if model.get("fields"):
                    self.models[key].setdefault("fields", {}).update(model["fields"])
                if model.get("methods"):
                    self.models[key].setdefault("methods", {}).update(model["methods"])

    def to_dict(self) -> dict:
        summaries = dict.fromkeys(self.languages, 0)
        data = {
            "name": self.name,
            "code": summaries,
            "manifest": self.manifest,
        }
        if self._scan_models:
            data["models"] = self.models
        for summary in self.summary.language_to_language_summary_map.values():
            for language in self.languages:
                if not summary.language.startswith(language):
                    continue
                summaries[language] += summary.code_count
        return data
