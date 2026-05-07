# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    enforce_credit_block = fields.Boolean(
        string="Enforce Credit Blocking",
        default=True,
        help="Block Sales Order confirmation when customer credit setup is missing or credit limit is exceeded without approval.",
    )

    enforce_below_cost_approval = fields.Boolean(
        string="Enforce Below Cost Approval",
        default=True,
        help="Block Sales Order confirmation when the order is below cost and no Sales Manager approval exists.",
    )