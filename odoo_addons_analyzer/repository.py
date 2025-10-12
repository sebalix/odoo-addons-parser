# Copyright 2023 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import multiprocessing
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
        workers: int = 0,
        scan_models: bool = True,
    ):
        self.folder_path = pathlib.Path(folder_path).resolve()
        self.languages = languages
        self.name = self.folder_path.name if name is None else name
        self.workers = workers
        self._scan_models = scan_models

    @property
    def module_paths(self) -> list[os.PathLike]:
        return sorted(
            set(map(lambda fp: fp.parent, self.folder_path.glob("*/__manifest__.py")))
            | set(map(lambda fp: fp.parent, self.folder_path.glob("*/__openerp__.py")))
        )

    def _scan_module(self, module_path):
        analysis = ModuleAnalysis(
            module_path,
            languages=self.languages,
            repo_analysis=self,
            scan_models=self._scan_models,
        )
        return analysis.to_dict()

    def to_dict(self) -> dict:
        data = {}
        # Multiworkers
        if self.workers:
            with multiprocessing.Pool(self.workers) as pool:
                results = pool.map(self._scan_module, self.module_paths)

            for module_data in results:
                data[module_data["name"]] = module_data
        # Monoprocess
        else:
            for module_path in self.module_paths:
                module = module_path.name
                data[module] = self._scan_module(module_path)
        return data
