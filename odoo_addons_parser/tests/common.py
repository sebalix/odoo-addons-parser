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
            "Python": 42,
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
                        "lineno": 14,
                        "end_lineno": 18,
                        "code": '    computed_field = fields.Char(\n        compute="_compute_computed_field",\n        readonly=False,\n        store=True,\n    )',
                        "kwargs": {
                            "compute": "_compute_computed_field",
                            "readonly": False,
                            "store": True,
                        },
                    },
                    "custom_field": {
                        "name": "custom_field",
                        "type": "Char",
                        "lineno": 13,
                        "end_lineno": 13,
                        "code": '    custom_field = fields.Char(required=True, default="Test")',
                        "kwargs": {
                            "required": True,
                            "default": "Test",
                        },
                    },
                    "good_customer": {
                        "name": "good_customer",
                        "type": "Boolean",
                        "lineno": 19,
                        "end_lineno": 19,
                        "code": "    good_customer = Boolean(default=lambda self: self._default_good_customer())",
                        "kwargs": {
                            "default": "lambda self: self._default_good_customer()",
                        },
                    },
                    "foo_id": {
                        "name": "foo_id",
                        "type": "Many2one",
                        "lineno": 21,
                        "end_lineno": 26,
                        "code": '    foo_id = fields.Many2one(\n        # Relation as keyword parameter\n        comodel_name="foo.model",\n        ondelete="restrict",\n        string="Foo",\n    )',
                        "kwargs": {
                            "comodel_name": "foo.model",
                            "ondelete": "restrict",
                            "string": "Foo",
                        },
                        "comodel_name": "foo.model",
                        "string": "Foo",
                    },
                    "bar_ids": {
                        "name": "bar_ids",
                        "type": "One2many",
                        "lineno": 27,
                        "end_lineno": 32,
                        "code": '    bar_ids = fields.One2many(\n        # Relation as positional parameter\n        "bar.model",\n        "partner_id",\n        string="Bars",\n    )',
                        "args": ["bar.model", "partner_id"],
                        "kwargs": {
                            "string": "Bars",
                        },
                        "comodel_name": "bar.model",
                        "inverse_name": "partner_id",
                        "string": "Bars",
                    },
                    "new_bar_ids": {
                        "name": "new_bar_ids",
                        "type": "One2many",
                        "lineno": 33,
                        "end_lineno": 37,
                        "code": '    new_bar_ids = fields.One2many(\n        comodel_name="bar.model",\n        inverse_name="partner_id",\n        string="New Bars",\n    )',
                        "kwargs": {
                            "comodel_name": "bar.model",
                            "inverse_name": "partner_id",
                            "string": "New Bars",
                        },
                        "comodel_name": "bar.model",
                        "inverse_name": "partner_id",
                        "string": "New Bars",
                    },
                    "new_custom_field": {
                        "name": "new_custom_field",
                        "type": "Char",
                        "lineno": 57,
                        "end_lineno": 57,
                        "code": "    new_custom_field = fields.Char()",
                    },
                },
                "inherit": "res.partner",
                "methods": {
                    "_compute_computed_field": {
                        "decorators": ("api.depends('custom_field')",),
                        "name": "_compute_computed_field",
                        "signature": ("self",),
                        "lineno": 40,
                        "end_lineno": 42,
                        "code": "    def _compute_computed_field(self):\n        for rec in self:\n            rec.computed_field = rec.customer_field",
                    },
                    "action_custom": {
                        "name": "action_custom",
                        "signature": ("self", "data", "**kwargs"),
                        "lineno": 44,
                        "end_lineno": 50,
                        "code": '    def action_custom(self, data, **kwargs):\n        # Use of \'match/case\' syntax, available from Python 3.10+\n        match data:\n            case 0:\n                print("Win")\n            case 1:\n                print("Lost")',
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
