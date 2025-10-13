# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import copy

from . import common


class TestRepository(common.CommonCase):
    def test_init(self):
        repo = self._run_repo_parser()
        self.assertEqual(repo.name, self.repo_name)
        self.assertTrue(repo.module_paths)

    def test_to_dict(self):
        repo = self._run_repo_parser()
        self.assertDictEqual(repo.to_dict(), {self.module_name: self.module_to_dict})

    def test_to_dict_no_code_stats(self):
        repo = self._run_repo_parser(code_stats=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["code"]
        self.assertDictEqual(repo.to_dict(), {self.module_name: mod_to_dict})

    def test_to_dict_no_scan_models(self):
        repo = self._run_repo_parser(scan_models=False)
        mod_to_dict = copy.deepcopy(self.module_to_dict)
        del mod_to_dict["models"]
        self.assertDictEqual(repo.to_dict(), {self.module_name: mod_to_dict})
