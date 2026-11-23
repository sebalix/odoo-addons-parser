# Copyright 2026 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


# Test corner case: an extension of a data model is declared before its
# original declaration in the same module. The original declaration must
# drive the data model metadata (type, inherit, class name...).
class TestModelInherit(models.Model):
    _inherit = "test.model"

    extended_field = fields.Char()


class TestModel(models.CachedModel):
    _name = "test.model"
    _inherit = [_name, "test.mixin"]
    _inherits = {"res.partner": "partner_id"}

    original_field = fields.Char()


# Test corner case: current module implements a new data model, then another
# declaration redefines it with a self-inheritance. The self-reference must
# be dropped from the module record.
class TestOwnedModel(models.Model):
    _name = "test.owned.model"


class TestOwnedModelInherit(models.Model):
    _name = "test.owned.model"
    _inherit = [_name, "other.mixin"]

    other_field = fields.Char()
