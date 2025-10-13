# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import copy

from . import common


class TestModule(common.CommonCase):
    def test_init(self):
        mod = self._run_module_parser()
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertDictEqual(mod.code, self.module_code_stats)
        self.assertDictEqual(mod.models, self.module_models)

    def test_init_no_code_stats(self):
        mod = self._run_module_parser(code_stats=False)
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertFalse(mod.code)
        self.assertDictEqual(mod.models, self.module_models)

    def test_init_no_scan_models(self):
        mod = self._run_module_parser(scan_models=False)
        self.assertEqual(mod.name, self.module_name)
        self.assertTrue(mod.file_paths)
        self.assertDictEqual(mod.manifest, self.module_manifest)
        self.assertDictEqual(mod.code, self.module_code_stats)
        self.assertFalse(mod.models)

    def test_to_dict(self):
        mod = self._run_module_parser()
        self.assertDictEqual(mod.to_dict(), self.module_to_dict)

    def test_to_dict_no_code_stats(self):
        mod = self._run_module_parser(code_stats=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["code"]
        self.assertDictEqual(mod.to_dict(), mod_to_dict)

    def test_to_dict_no_scan_models(self):
        mod = self._run_module_parser(scan_models=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["models"]
        self.assertDictEqual(mod.to_dict(), mod_to_dict)
