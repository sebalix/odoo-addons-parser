# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from . import common


class TestRepository(common.CommonCase):
    def test_init(self):
        repo = self._run_repo_analysis()
        self.assertEqual(repo.name, self.repo_name)
        self.assertTrue(repo.module_paths)

    def test_to_dict(self):
        repo = self._run_repo_analysis()
        self.assertDictEqual(repo.to_dict(), {self.module_name: self.module_to_dict})
