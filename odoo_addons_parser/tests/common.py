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
            "XML": 78,
        }
        cls.module_manifest = {
            "author": "Camptocamp, Odoo Community Association (OCA)",
            "category": "Test Module",
            "data": [
                "data/res_partner.xml",
                "views/res_partner.xml",
                "views/assets.xml",
                "reports/reports.xml",
                "reports/templates.xml",
            ],
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
        cls.module_data = {
            "ir.ui.view": [
                {
                    "id": "res_partner_form_view",
                    "model": "ir.ui.view",
                    "type": "normal",
                    "target_model": "res.partner",
                    "name": "res.partner.form.inherit",
                    "file_path": "views/res_partner.xml",
                    "status": "data",
                    "data": {
                        "model": "res.partner",
                        "inherit_id": "base.res_partner_form_view",
                        "arch": '\n            <field name="name" position="after">\n                <field name="custom_field" />\n                <field name="computed_field" />\n            </field>\n        ',
                        "name": "res.partner.form.inherit",
                    },
                },
                {
                    "id": "res_partner_tree_view",
                    "model": "ir.ui.view",
                    "type": "normal",
                    "target_model": "res.partner",
                    "name": "res.partner.tree",
                    "file_path": "views/res_partner.xml",
                    "status": "data",
                    "data": {
                        "model": "res.partner",
                        "arch": '\n            <tree>\n                <field name="name" />\n                <field name="custom_field" />\n            </tree>\n        ',
                        "name": "res.partner.tree",
                    },
                },
                {
                    "id": "report_contact_badge",
                    "model": "ir.ui.view",
                    "type": "qweb",
                    "name": "report_contact_badge",
                    "file_path": "reports/templates.xml",
                    "status": "data",
                    "data": {
                        "arch": '<template id="report_contact_badge">\n        <t t-call="web.html_container">\n            <t t-foreach="docs" t-as="doc">\n                <h1 t-out="doc.name" />\n            </t>\n        </t>\n    </template>\n\n',
                    },
                },
            ],
            "ir.actions.act_window": [
                {
                    "id": "res_partner_action",
                    "model": "ir.actions.act_window",
                    "name": "Contacts",
                    "target_model": "res.partner",
                    "file_path": "views/res_partner.xml",
                    "status": "data",
                    "data": {
                        "name": "Contacts",
                        "type": "ir.actions.act_window",
                        "res_model": "res.partner",
                        "view_type": "form",
                        "view_id": "res_partner_view_tree",
                    },
                }
            ],
            "ir.actions.report": [
                {
                    "id": "action_report_badge",
                    "model": "ir.actions.report",
                    "name": "Badge",
                    "file_path": "reports/reports.xml",
                    "status": "data",
                    "data": {
                        "name": "Badge",
                        "model": "res.partner",
                        "report_type": "qweb-pdf",
                        "report_name": "module.report_contact_badge",
                        "report_file": "module.report_contact_badge",
                        "print_report_name": "'Badge - %s - %s' % (object.name or '', object.name)",
                        "binding_model_id": "model_res_partner",
                        "binding_type": "report",
                    },
                }
            ],
            "ir.ui.menu": [
                {
                    "id": "main_menu",
                    "model": "ir.ui.menu",
                    "name": "Main menu",
                    "file_path": "views/res_partner.xml",
                    "status": "data",
                    "data": {"name": "Main menu", "parent_id": "base.root_menu"},
                },
                {
                    "id": "submenu_menu",
                    "model": "ir.ui.menu",
                    "name": "Submenu",
                    "file_path": "views/res_partner.xml",
                    "status": "data",
                    "data": {"name": "Submenu"},
                },
                {
                    "id": "res_partner_menu",
                    "model": "ir.ui.menu",
                    "name": None,
                    "file_path": "views/res_partner.xml",
                    "status": "data",
                    "data": {"action": "res_partner_action"},
                },
            ],
            "ir.asset": [
                {
                    "id": "contact_badge_scss",
                    "model": "ir.asset",
                    "name": "Contact Badge SCSS",
                    "file_path": "views/assets.xml",
                    "status": "data",
                    "data": {"name": "Contact Badge SCSS"},
                }
            ],
            "res.partner": [
                {
                    "id": "director",
                    "model": "res.partner",
                    "name": "Director",
                    "file_path": "data/res_partner.xml",
                    "status": "data",
                    "noupdate": True,
                    "data": {"name": "Director"},
                },
                {
                    "id": "accountant",
                    "model": "res.partner",
                    "name": "Accountant",
                    "file_path": "data/res_partner.xml",
                    "status": "data",
                    "data": {"name": "Accountant"},
                },
            ],
        }

        cls.module_to_dict = {
            "name": cls.module_name,
            "code": cls.module_code_stats,
            "manifest": cls.module_manifest,
            "models": cls.module_models,
            "data": cls.module_data,
        }

    @classmethod
    def _run_module_parser(cls, **kw):
        return ModuleParser(cls.module_path, **kw)

    @classmethod
    def _run_repo_parser(cls, **kw):
        return RepositoryParser(cls.repo_path, **kw)
