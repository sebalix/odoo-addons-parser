# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import pathlib
import unittest

from odoo_addons_parser import ModuleParser, RepositoryParser


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
            "Python": 23,
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
            "website": "https://example.com/odoo-addons-parser",
        }
        cls.module_models = {
            "res.partner": {
                "file_path": "models/res_partner.py",
                "class_name": "ResPartner",
                "fields": {
                    "computed_field": {
                        "name": "computed_field",
                        "type": "Char",
                        "lineno": 11,
                        "end_lineno": 15,
                        "code": '    computed_field = fields.Char(\n        compute="_compute_computed_field",\n        readonly=False,\n        store=True,\n    )\n',
                    },
                    "custom_field": {
                        "name": "custom_field",
                        "type": "Char",
                        "lineno": 10,
                        "end_lineno": 10,
                        "code": '    custom_field = fields.Char(required=True, default="Test")\n',
                    },
                    "new_custom_field": {
                        "name": "new_custom_field",
                        "type": "Char",
                        "lineno": 30,
                        "end_lineno": 30,
                        "code": "    new_custom_field = fields.Char()\n",
                    },
                },
                "inherit": "res.partner",
                "methods": {
                    "_compute_computed_field": {
                        "decorators": ("api.depends('custom_field')",),
                        "name": "_compute_computed_field",
                        "signature": ("self",),
                        "lineno": 18,
                        "end_lineno": 20,
                        "code": "    def _compute_computed_field(self):\n        for rec in self:\n            rec.computed_field = rec.customer_field\n",
                    },
                    "action_custom": {
                        "name": "action_custom",
                        "signature": ("self", "data", "**kwargs"),
                        "lineno": 22,
                        "end_lineno": 23,
                        "code": "    def action_custom(self, data, **kwargs):\n        pass\n",
                    },
                },
                "type": "Model",
            },
            "res.users": {
                "file_path": "models/res_users.py",
                "class_name": "ResUsers",
                "name": "res.users",
                "inherit": ["res.users", "test"],
                "type": "Model",
            },
        }
        cls.module_to_dict = {
            "name": cls.module_name,
            "code": cls.module_code_stats,
            "manifest": cls.module_manifest,
            "models": cls.module_models,
        }

    @classmethod
    def _run_module_parser(cls, **kw):
        return ModuleParser(cls.module_path, **kw)

    @classmethod
    def _run_repo_parser(cls, **kw):
        return RepositoryParser(cls.repo_path, **kw)
