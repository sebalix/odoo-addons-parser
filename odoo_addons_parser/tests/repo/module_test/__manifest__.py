# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Test",
    "version": "1.0.0",
    "category": "Test Module",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://example.com/odoo-addons-parser",
    "license": "AGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "data/res_partner.xml",
        "views/res_partner.xml",
        "views/assets.xml",
        "reports/reports.xml",
        "reports/templates.xml",
    ],
    "demo": ["demo/res_partner.xml"],
    "installable": True,
}
