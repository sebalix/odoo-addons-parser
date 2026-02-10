# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.fields import Boolean

from odoo.addons import x


class ResPartner(models.Model):
    _inherit = "res.partner"

    custom_field = fields.Char(required=True, default="Test")
    computed_field = fields.Char(
        compute="_compute_computed_field",
        readonly=False,
        store=True,
    )
    good_customer = Boolean(default=lambda self: self._default_good_customer())
    special_field = x.fields.Special()
    foo_id = fields.Many2one(
        # Relation as keyword parameter
        comodel_name="foo.model",
        ondelete="restrict",
        string="Foo",
    )
    bar_ids = fields.One2many(
        # Relation as positional parameter
        "bar.model",
        "partner_id",
        string="Bars",
    )
    new_bar_ids = fields.One2many(
        comodel_name="bar.model",
        inverse_name="partner_id",
        string="New Bars",
    )

    @api.depends("custom_field")
    def _compute_computed_field(self):
        for rec in self:
            rec.computed_field = rec.customer_field

    def action_custom(self, data, **kwargs):
        # Use of 'match/case' syntax, available from Python 3.10+
        match data:
            case 0:
                print("Win")
            case 1:
                print("Lost")


# Test corner case: declare the class twice in same Python file
class ResPartner(models.Model):  # noqa: F811
    _inherit = "res.partner"

    new_custom_field = fields.Char()

    _test_attr = {}
    _test_attr["test"] = True
