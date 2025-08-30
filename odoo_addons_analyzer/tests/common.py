# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import pathlib
import unittest

from odoo_addons_analyzer import ModuleAnalysis, RepositoryAnalysis


class CommonCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None  # to see assertDictEqual diff
        current_file_path = pathlib.Path(__file__).resolve()
        current_dir_path = current_file_path.parent
        cls.repo_name = "repo"
        cls.repo_path = current_dir_path.joinpath(cls.repo_name)
        cls.module_name = "module_test"
        cls.module_path = cls.repo_path.joinpath(cls.module_name)
        cls.module_code_stats = {
            "CSS": 0,
            "JavaScript": 0,
            "Python": 18,
            "XML": 14,
        }
        cls.module_manifest = {
            "author": "Camptocamp, Odoo Community Association (OCA)",
            "category": "Test Module",
            "data": ["views/res_partner.xml"],
            "demo": [],
            "depends": ["base"],
            "installable": True,
            "license": "AGPL-3",
            "name": "Test",
            "version": "1.0.0",
            "website": "https://example.com/odoo-addons-analyzer",
        }
        cls.module_models = {
            "res.partner": {
                "fields": {
                    "computed_field": {
                        "name": "computed_field",
                        "type": "Char",
                    },
                    "custom_field": {"name": "custom_field", "type": "Char"},
                    "new_custom_field": {"name": "new_custom_field", "type": "Char"},
                },
                "inherit": "res.partner",
                "methods": {
                    "_compute_computed_field": {
                        "decorators": ("api.depends('custom_field')",),
                        "name": "_compute_computed_field",
                        "signature": ("self",),
                    }
                },
                "type": "Model",
            }
        }
        cls.module_to_dict = {
            "code": cls.module_code_stats,
            "manifest": cls.module_manifest,
            "models": cls.module_models,
        }

    @classmethod
    def _run_module_analysis(cls, **kw):
        return ModuleAnalysis(cls.module_path, **kw)

    @classmethod
    def _run_repo_analysis(cls):
        return RepositoryAnalysis(cls.repo_path)
