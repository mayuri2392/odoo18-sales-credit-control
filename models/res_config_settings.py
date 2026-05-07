# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enforce_credit_block = fields.Boolean(
        related="company_id.enforce_credit_block",
        readonly=False,
        string="Enforce Credit Blocking",
    )

    enforce_below_cost_approval = fields.Boolean(
        related="company_id.enforce_below_cost_approval",
        readonly=False,
        string="Enforce Below Cost Approval",
    )