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
            "XML": 148,
        }
        cls.module_manifest = {
            "author": "Camptocamp, Odoo Community Association (OCA)",
            "category": "Test Module",
            "data": [
                "security/security.xml",
                "security/ir.model.access.csv",
                "data/res_partner.xml",
                "data/nested_root_tags.xml",
                "data/mail_template.xml",
                "views/res_partner.xml",
                "views/assets.xml",
                "reports/reports.xml",
                "reports/templates.xml",
            ],
            "demo": ["demo/res_partner.xml"],
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
            "ir.model.access": [
                {
                    "id": "access_res_partner_group_account",
                    "model": "ir.model.access",
                    "file_path": "security/ir.model.access.csv",
                    "loaded": True,
                    "data": {
                        "id": "access_res_partner_group_account",
                        "name": "res_partner group account",
                        "model_id": "model_res_partner",
                        "group_id": "group_user",
                        "perm_read": "1",
                        "perm_write": "1",
                        "perm_create": "1",
                        "perm_unlink": "0",
                    },
                },
            ],
            "ir.ui.view": [
                {
                    "id": "res_partner_form_view",
                    "model": "ir.ui.view",
                    "type": "normal",
                    "target_model": "res.partner",
                    "name": "res.partner.form.inherit",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {
                        "model": "res.partner",
                        "inherit_id": "base.res_partner_form_view",
                        "name": "res.partner.form.inherit",
                    },
                    "xml": '<record id="res_partner_form_view" model="ir.ui.view">\n        <field name="name">res.partner.form.inherit</field>\n        <field name="model">res.partner</field>\n        <field name="inherit_id" ref="base.res_partner_form_view"/>\n        <field name="arch" type="xml">\n            <field name="name" position="after">\n                <field name="custom_field" />\n                <field name="computed_field" />\n            </field>\n        </field>\n    </record>',
                },
                {
                    "id": "res_partner_tree_view",
                    "model": "ir.ui.view",
                    "type": "normal",
                    "target_model": "res.partner",
                    "name": "res.partner.tree",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {
                        "model": "res.partner",
                        "name": "res.partner.tree",
                    },
                    "xml": '<record id="res_partner_tree_view" model="ir.ui.view">\n        <field name="name">res.partner.tree</field>\n        <field name="model">res.partner</field>\n        <field name="arch" type="xml">\n            <tree>\n                <field name="name" />\n                <field name="custom_field" />\n            </tree>\n        </field>\n    </record>',
                },
                {
                    "id": "report_contact_badge",
                    "model": "ir.ui.view",
                    "type": "qweb",
                    "name": "report_contact_badge",
                    "file_path": "reports/templates.xml",
                    "loaded": True,
                    "data": {},
                    "xml": '<template id="report_contact_badge">\n        <t t-call="web.html_container">\n            <t t-foreach="docs" t-as="doc">\n                <h1 t-out="doc.name" />\n            </t>\n        </t>\n    </template>',
                },
            ],
            "ir.actions.act_window": [
                {
                    "id": "res_partner_action",
                    "model": "ir.actions.act_window",
                    "name": "Contacts",
                    "target_model": "res.partner",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {
                        "name": "Contacts",
                        "type": "ir.actions.act_window",
                        "res_model": "res.partner",
                        "view_type": "form",
                        "view_id": "res_partner_view_tree",
                    },
                    "xml": '<record id="res_partner_action" model="ir.actions.act_window">\n        <field name="name">Contacts</field>\n        <field name="type">ir.actions.act_window</field>\n        <field name="res_model">res.partner</field>\n        <field name="view_type">form</field>\n        <field name="view_id" ref="res_partner_view_tree" />\n    </record>',
                },
                {
                    "id": "act_window_partner_simple",
                    "model": "ir.actions.act_window",
                    "name": "Partner Simple Action",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {
                        "name": "Partner Simple Action",
                        "type": "ir.actions.act_window",
                        "res_model": "res.partner",
                        "view_mode": "tree,form",
                        "view_type": "tree",
                        "target": "current",
                    },
                    "xml": '<act_window\n        id="act_window_partner_simple"\n        name="Partner Simple Action"\n        res_model="res.partner"\n        view_mode="tree,form"\n        view_type="tree"\n        target="current"\n    />',
                },
            ],
            "ir.actions.report": [
                {
                    "id": "action_report_badge",
                    "model": "ir.actions.report",
                    "name": "Badge",
                    "file_path": "reports/reports.xml",
                    "loaded": True,
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
                    "xml": '<record id="action_report_badge" model="ir.actions.report">\n        <field name="name">Badge</field>\n        <field name="model">res.partner</field>\n        <field name="report_type">qweb-pdf</field>\n        <field name="report_name">module.report_contact_badge</field>\n        <field name="report_file">module.report_contact_badge</field>\n        <field name="print_report_name">\'Badge - %s - %s\' % (object.name or \'\', object.name)</field>\n        <field name="binding_model_id" ref="model_res_partner"/>\n        <field name="binding_type">report</field>\n    </record>',
                },
                {
                    "id": "report_partner_simple",
                    "model": "ir.actions.report",
                    "name": "Partner Simple Report",
                    "file_path": "reports/reports.xml",
                    "loaded": True,
                    "data": {
                        "name": "Partner Simple Report",
                        "model": "res.partner",
                        "report_type": "qweb-pdf",
                        "report_name": "module_test.report_partner_simple",
                        "report_file": "module_test.report_partner_simple",
                    },
                    "xml": '<report\n        id="report_partner_simple"\n        string="Partner Simple Report"\n        model="res.partner"\n        report_type="qweb-pdf"\n        name="module_test.report_partner_simple"\n        file="module_test.report_partner_simple"\n    />',
                },
                {
                    "id": "report_partner_detailed",
                    "model": "ir.actions.report",
                    "name": "Partner Detailed Report",
                    "file_path": "reports/reports.xml",
                    "loaded": True,
                    "data": {
                        "name": "Partner Detailed Report",
                        "model": "res.partner",
                        "report_type": "qweb-pdf",
                        "report_name": "module_test.report_partner_detailed",
                        "report_file": "module_test.report_partner_detailed",
                        "print_report_name": "'Partner Report - %s' % (object.name)",
                    },
                    "xml": '<report\n        id="report_partner_detailed"\n        string="Partner Detailed Report"\n        model="res.partner"\n        report_type="qweb-pdf"\n        name="module_test.report_partner_detailed"\n        file="module_test.report_partner_detailed"\n        print_report_name="\'Partner Report - %s\' % (object.name)"\n    />',
                },
            ],
            "ir.ui.menu": [
                {
                    "id": "main_menu",
                    "model": "ir.ui.menu",
                    "name": "Main menu",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {"name": "Main menu", "parent_id": "base.root_menu"},
                    "xml": '<menuitem id="main_menu" parent="base.root_menu" name="Main menu" >\n        <menuitem id="submenu_menu" name="Submenu">\n            <menuitem id="res_partner_menu" action="res_partner_action" />\n        </menuitem>\n    </menuitem>',
                },
                {
                    "id": "submenu_menu",
                    "model": "ir.ui.menu",
                    "name": "Submenu",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {"name": "Submenu", "parent_id": "main_menu"},
                    "xml": '<menuitem id="submenu_menu" name="Submenu">\n            <menuitem id="res_partner_menu" action="res_partner_action" />\n        </menuitem>',
                },
                {
                    "id": "res_partner_menu",
                    "model": "ir.ui.menu",
                    "file_path": "views/res_partner.xml",
                    "loaded": True,
                    "data": {
                        "action": "res_partner_action",
                        "parent_id": "submenu_menu",
                    },
                    "xml": '<menuitem id="res_partner_menu" action="res_partner_action" />',
                },
            ],
            "ir.asset": [
                {
                    "id": "contact_badge_scss",
                    "model": "ir.asset",
                    "name": "Contact Badge SCSS",
                    "file_path": "views/assets.xml",
                    "loaded": True,
                    "data": {"name": "Contact Badge SCSS"},
                    "xml": '<asset id="contact_badge_scss" name="Contact Badge SCSS" active="True">\n        <field name="key">module_test.contact_badge_scss</field>\n        <bundle>web.assets_frontend</bundle>\n        <path>/module_test/static/src/scss/contact_badge.scss</path>\n    </asset>',
                }
            ],
            "res.partner": [
                {
                    "id": "director",
                    "model": "res.partner",
                    "name": "Director",
                    "file_path": "data/res_partner.xml",
                    "loaded": True,
                    "noupdate": True,
                    "data": {"name": "Director"},
                    "xml": '<record id="director" model="res.partner">\n            <field name="name">Director</field>\n        </record>',
                },
                {
                    "id": "accountant",
                    "model": "res.partner",
                    "name": "Accountant",
                    "file_path": "data/res_partner.xml",
                    "loaded": True,
                    "data": {"name": "Accountant"},
                    "xml": '<record id="accountant" model="res.partner">\n        <field name="name">Accountant</field>\n    </record>',
                },
                {
                    "id": "partner_alongside_root_tags",
                    "model": "res.partner",
                    "name": "Partner Alongside Root Tags",
                    "file_path": "data/nested_root_tags.xml",
                    "loaded": True,
                    "data": {"name": "Partner Alongside Root Tags"},
                    "xml": '<record id="partner_alongside_root_tags" model="res.partner">\n        <field name="name">Partner Alongside Root Tags</field>\n    </record>',
                },
                {
                    "id": "partner_nested_in_data",
                    "model": "res.partner",
                    "name": "Nested Partner in Data",
                    "file_path": "data/nested_root_tags.xml",
                    "loaded": True,
                    "data": {"name": "Nested Partner in Data"},
                    "xml": '<record id="partner_nested_in_data" model="res.partner">\n                <field name="name">Nested Partner in Data</field>\n            </record>',
                },
            ],
            "res.groups": [
                {
                    "id": "group_test",
                    "model": "res.groups",
                    "name": "Test",
                    "file_path": "security/security.xml",
                    "loaded": True,
                    "data": {"name": "Test"},
                    "xml": '<record id="group_test" model="res.groups">\n        <field name="name">Test</field>\n    </record>',
                },
            ],
            "res.users": [
                {
                    "id": "base.default_user",
                    "model": "res.users",
                    "file_path": "security/security.xml",
                    "loaded": True,
                    "data": {"groups_id": "[(4,ref('module_test.group_test'))]"},
                    "xml": '<record id="base.default_user" model="res.users">\n        <field name="groups_id" eval="[(4,ref(\'module_test.group_test\'))]"/>\n    </record>',
                },
            ],
            "mail.template": [
                {
                    "id": "partner_mail_template",
                    "model": "mail.template",
                    "name": "Partner: Test Template",
                    "file_path": "data/mail_template.xml",
                    "loaded": True,
                    "data": {
                        "name": "Partner: Test Template",
                        "model_id": "model_res_partner",
                    },
                    "xml": '<record id="partner_mail_template" model="mail.template">\n        <field name="name">Partner: Test Template</field>\n        <field name="model_id" ref="model_res_partner"/>\n        <field name="body_html" type="html">\n            <p>Dear <t t-out="object.name"/>,</p>\n            <p>This is a test template.</p>\n        </field>\n    </record>',
                },
            ],
        }
        cls.module_demo = {
            "res.partner": [
                {
                    "id": "employee",
                    "model": "res.partner",
                    "name": "Employee",
                    "file_path": "demo/res_partner.xml",
                    "loaded": True,
                    "data": {"name": "Employee"},
                    "xml": '<record id="employee" model="res.partner">\n        <field name="name">Employee</field>\n    </record>',
                }
            ]
        }

        cls.module_to_dict = cls._order_mod_data(
            {
                "name": cls.module_name,
                "code": cls.module_code_stats,
                "manifest": cls.module_manifest,
                "models": cls.module_models,
                "data": cls.module_data,
                "demo": cls.module_demo,
            }
        )

    @classmethod
    def _order_mod_data(cls, data):
        """Order module data to ease comparison between Python versions."""
        for model, records in data["data"].items():
            data["data"][model] = sorted(records, key=lambda rec: rec["id"])
        for model, records in data["demo"].items():
            data["demo"][model] = sorted(records, key=lambda rec: rec["id"])
        return data

    @classmethod
    def _order_repo_data(cls, data):
        """Order repository data to ease comparison between Python versions."""
        for module_name, mod_data in data.items():
            cls._order_mod_data(mod_data)
        return data

    @classmethod
    def _run_module_parser(cls, **kw):
        return ModuleParser(cls.module_path, **kw)

    @classmethod
    def _run_repo_parser(cls, **kw):
        return RepositoryParser(cls.repo_path, **kw)
