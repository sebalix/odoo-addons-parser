# Copyright 2025 Sebastien Alix <https://github.com/sebalix>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


# Test corner case: inherit declared as a list + ref to cls variable
class ResUsers(models.Model):
    _name = "res.users"
    _inherit = [_name, "test"]
