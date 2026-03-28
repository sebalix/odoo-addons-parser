# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import copy

from odoo_addons_parser import ModuleParser

from . import common


class TestModule(common.CommonCase):
    def test_init(self):
        mod = self._run_module_parser()
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertDictEqual(mod.code, self.module_code_stats)
        self.assertDictEqual(mod.models, self.module_models)
        self.assertEqual(set(mod.data), set(self.module_data))

    def test_init_no_code_stats(self):
        mod = self._run_module_parser(code_stats=False)
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertFalse(mod.code)
        self.assertDictEqual(mod.models, self.module_models)
        self.assertEqual(set(mod.data), set(self.module_data))

    def test_init_no_scan_models(self):
        mod = self._run_module_parser(scan_models=False)
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertDictEqual(mod.code, self.module_code_stats)
        self.assertFalse(mod.models)
        self.assertEqual(set(mod.data), set(self.module_data))

    def test_init_no_scan_data(self):
        mod = self._run_module_parser(scan_data=False)
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertDictEqual(mod.code, self.module_code_stats)
        self.assertDictEqual(mod.models, self.module_models)
        self.assertFalse(mod.data)

    def test_init_folder_not_exist(self):
        with self.assertRaises(ValueError):
            ModuleParser("folder/not/exist")

    def test_init_folder_not_odoo_module(self):
        self.assertTrue(self.repo_path.exists())
        with self.assertRaises(ValueError):
            ModuleParser(self.repo_path)

    def test_to_dict(self):
        mod = self._run_module_parser()
        mod_data = self._order_mod_data(mod.to_dict())
        self.assertDictEqual(mod_data, self.module_to_dict)

    def test_to_dict_no_code_stats(self):
        mod = self._run_module_parser(code_stats=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["code"]
        mod_data = self._order_mod_data(mod.to_dict())
        self.assertDictEqual(mod_data, mod_to_dict)

    def test_to_dict_no_scan_models(self):
        mod = self._run_module_parser(scan_models=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["models"]
        mod_data = self._order_mod_data(mod.to_dict())
        self.assertDictEqual(mod_data, mod_to_dict)

    def test_to_dict_no_scan_data(self):
        mod = self._run_module_parser(scan_data=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["data"]
        del mod_to_dict["demo"]
        self.assertDictEqual(mod.to_dict(), mod_to_dict)
