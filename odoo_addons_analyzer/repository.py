# Copyright 2023 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import os
import pathlib
import typing

from .module import ModuleAnalysis


class RepositoryAnalysis:
    def __init__(
        self,
        folder_path: typing.Union[str, os.PathLike],
        languages: tuple[str, ...] = ("Python", "XML", "CSS", "JavaScript"),
        name: typing.Optional[str] = None,
        scan_models: bool = True,
    ):
        self.folder_path = pathlib.Path(folder_path).resolve()
        self.languages = languages
        self.name = self.folder_path.name if name is None else name
        self._scan_models = scan_models

    @property
    def module_paths(self) -> list[os.PathLike]:
        return sorted(
            set(map(lambda fp: fp.parent, self.folder_path.glob("*/__manifest__.py")))
            | set(map(lambda fp: fp.parent, self.folder_path.glob("*/__openerp__.py")))
        )

    def to_dict(self) -> dict:
        data = {}
        for module_path in self.module_paths:
            module = module_path.name
            analysis = ModuleAnalysis(
                module_path,
                languages=self.languages,
                repo_analysis=self,
                scan_models=self._scan_models,
            )
            data[module] = analysis.to_dict()
        return data
