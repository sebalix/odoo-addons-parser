# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os
import pathlib
import unittest
import urllib.request
import zipfile

from odoo_addons_parser import OdooParser

from . import common


if not os.environ.get("TEST_ODOO_PARSER"):
    raise unittest.SkipTest("Tests of OdooParser are disabled.")


ODOO_LAST_VERSION = 19
SUPPORT_X_VERSIONS = 3
ODOO_VERSIONS = [
    float(version)
    for version in range(
        ODOO_LAST_VERSION - SUPPORT_X_VERSIONS + 1, ODOO_LAST_VERSION + 1
    )
]
ODOO_TPL_URL = "https://github.com/odoo/odoo/archive/refs/heads/{version}.zip"


class TestOdoo(common.CommonCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Download locally Odoo tarballs
        cls.download_path = pathlib.Path(
            os.environ.get("ODOO_DOWNLOAD_DIR_PATH", ".odoo_download_dir_path")
        )
        cls.download_path.mkdir(parents=True, exist_ok=True)
        for version in ODOO_VERSIONS:
            file_path = cls.download_path.joinpath(f"odoo-{version}.zip")
            if not file_path.exists():
                url = ODOO_TPL_URL.format(version=version)
                print(f"Downloading {url}...")
                urllib.request.urlretrieve(url, file_path)
            folder_path = cls.download_path.joinpath(f"odoo-{version}")
            if not folder_path.exists():
                print(f"Extracting {file_path}...")
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(cls.download_path)

    def test_init(self):
        for version in ODOO_VERSIONS:
            folder_path = self.download_path.joinpath(f"odoo-{version}")
            parser = OdooParser(folder_path)
            self.assertEqual(parser.name, f"odoo-{version}")
            self.assertTrue(parser.repositories)

    def test_to_dict(self):
        for version in ODOO_VERSIONS:
            folder_path = self.download_path.joinpath(f"odoo-{version}")
            # Disable code_stats to make tests faster
            parser = OdooParser(folder_path, code_stats=False)
            data = parser.to_dict()
            self.assertIn("__odoo__", data)
            framework_models = list(data["__odoo__"]["models"])
            self.assertIn("BaseModel", framework_models)
            self.assertIn("Model", framework_models)
            self.assertIn("TransientModel", framework_models)
            self.assertIn("res.partner", list(data["base"]["models"]))
            # 'res.partner' and 'res.users' are declared several times in 'base'
            # module (one with '_name' and another ones with '_inherit'), but it's
            # not considered as inherited at the module level (ignoring any use
            # of '_inherit')
            for model in ("res.partner", "res.users"):
                record = data["base"]["models"][model]
                self.assertIn("name", record)
                self.assertTrue(record["name"], model)
                self.assertNotIn(model, record.get("inherit", ""))
            # While in 'sale' it is inheriting 'res.partner'
            sale_res_partner = data["sale"]["models"]["res.partner"]
            self.assertNotIn("name", sale_res_partner)
            self.assertIn("inherit", sale_res_partner)
            self.assertIn("res.partner", sale_res_partner["inherit"])

    def test_to_dict_merge_base_models_into_base_module(self):
        version = ODOO_VERSIONS[-1]
        folder_path = self.download_path.joinpath(f"odoo-{version}")
        # Disable code_stats to make tests faster
        # + collect BaseModel, Model, TransientModel into 'base' module
        parser = OdooParser(folder_path, code_stats=False, base_models_key="base")
        data = parser.to_dict()
        self.assertNotIn("__odoo__", data)
        self.assertIn("base", data)
        models = list(data["base"]["models"])
        self.assertIn("BaseModel", models)
        self.assertIn("Model", models)
        self.assertIn("TransientModel", models)
        self.assertIn("res.partner", models)
        self.assertIn("base", models)
