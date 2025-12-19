# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os
import pathlib
import typing

from .code import PyFile
from .repository import RepositoryParser


ODOO_BASE_MODELS_PATHS = (
    # Odoo < 19.0
    pathlib.Path("odoo").joinpath("models.py"),
    # Odoo >= 19.0
    pathlib.Path("odoo").joinpath("orm", "models.py"),
    pathlib.Path("odoo").joinpath("orm", "models_transient.py"),
)
ODOO_BASE_ADDONS_PATH = pathlib.Path("odoo").joinpath("addons")
ODOO_ADDONS_PATH = pathlib.Path("addons")


class OdooParser:
    """Dedicated parser for Odoo repository (https://github.com/odoo/odoo).

    It takes as input the path of the main Odoo source code repository,
    and will take care of parsing the different addons paths in it
    (`./odoo/addons/` and `./addons/` by default) and the special ORM files
    containing the base data models (BaseModel, Model and TransientModel).

    The ORM data will be available under the fake module name `__odoo__`
    by default. This can be changed with `base_models_key` parameter.
    In case `base_models_key` is set with an existing module name (e.g. `base`)
    the ORM data will be merged into that one.

    E.g:
        >>> data = OdooParser("./odoo/odoo", code_stats=False).to_dict()
        >>> list(data["__odoo__"]["models"])
        ['BaseModel', 'Model', 'TransientModel']
        >>> "res.partner" in data["base"]["models"]
        True
    """

    def __init__(
        self,
        folder_path: typing.Union[str, os.PathLike],
        languages: tuple[str, ...] = ("Python", "XML", "CSS", "JavaScript"),
        name: typing.Optional[str] = None,
        workers: int = 0,
        code_stats: bool = True,
        scan_models: bool = True,
        addons_paths: tuple[os.PathLike, ...] = (
            ODOO_BASE_ADDONS_PATH,
            ODOO_ADDONS_PATH,
        ),
        base_models_paths: tuple[os.PathLike, ...] = ODOO_BASE_MODELS_PATHS,
        base_models_key: str = "__odoo__",
    ):
        self.folder_path = pathlib.Path(folder_path).resolve()
        self.languages = languages
        self.name = self.folder_path.name if name is None else name
        self.workers = workers
        self._code_stats = code_stats
        self._scan_models = scan_models
        self._addons_paths = addons_paths
        self._base_models_paths = []
        for base_models_path in base_models_paths:
            # Keep only existing base models file paths
            if self.folder_path.joinpath(base_models_path).exists():
                self._base_models_paths.append(pathlib.Path(base_models_path))
        self._base_models_key = base_models_key
        self.base_models = []
        self.repositories = []
        self._run()

    def _run(self):
        # Scan base models
        for base_models_path in self._base_models_paths:
            base_models_path = self.folder_path.joinpath(base_models_path)
            self.base_models.append(
                PyFile(base_models_path, module_path=self.folder_path)
            )
        # Scan addons paths
        for addons_path in self._addons_paths:
            full_addons_path = self.folder_path.joinpath(addons_path)
            if not full_addons_path.exists():
                continue
            self.repositories.append(
                RepositoryParser(
                    full_addons_path,
                    languages=self.languages,
                    name=str(addons_path),
                    workers=self.workers,
                    code_stats=self._code_stats,
                    scan_models=self._scan_models,
                )
            )

    def to_dict(self) -> dict:
        data = {}
        # Base models
        for base_models in self.base_models:
            # Put these data in a special module name '__odoo__'
            data.setdefault(self._base_models_key, {})
            base_data = base_models.to_dict()
            for key in base_data.keys():
                # All values are dicts, so we can merge them
                # NOTE: only available key is 'models' currently
                if key in data[self._base_models_key]:
                    data[self._base_models_key][key].update(base_data[key])
                else:
                    data[self._base_models_key][key] = base_data[key]
        # Addons paths
        for repo in self.repositories:
            repo_data = repo.to_dict()
            # In case 'base_models_key' was set with an existing module name
            # we need to merge both dataset
            for module_name, module_data in repo_data.items():
                data.setdefault(module_name, {})
                # NOTE: only key to merge is 'models' currently
                for key in module_data:
                    if key == "models":
                        data[module_name].setdefault(key, {})
                        data[module_name][key].update(module_data[key])
                        continue
                    data[module_name][key] = module_data[key]
            else:
                data[module_name] = module_data
        return data
