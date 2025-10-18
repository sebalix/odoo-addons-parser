# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    custom_field = fields.Char(required=True, default="Test")
    computed_field = fields.Char(
        compute="_compute_computed_field",
        readonly=False,
        store=True,
    )

    @api.depends("custom_field")
    def _compute_computed_field(self):
        for rec in self:
            rec.computed_field = rec.customer_field

    def action_custom(self, data, **kwargs):
        pass


# Test corner case: declare the class twice in same Python file
class ResPartner(models.Model):  # noqa: F811
    _inherit = "res.partner"

    new_custom_field = fields.Char()

    _test_attr = {}
    _test_attr["test"] = True
