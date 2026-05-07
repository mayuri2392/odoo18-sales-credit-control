# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CreditTier(models.Model):
    _name = 'credit.tier'
    _description = 'Credit Tier'
    _order = 'sequence, name'

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True, copy=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)

    default_credit_limit = fields.Float(string="Default Credit Limit", required=True, default=0.0)
    note = fields.Text(string="Notes")

    # ✅ Color badge support (Odoo standard color index)
    color = fields.Integer(string="Color", default=0)

    _sql_constraints = [
        ('credit_tier_code_company_uniq', 'unique(code, company_id)', 'Credit Tier Code must be unique per company.'),
    ]

    @api.onchange('name')
    def _onchange_name_set_code(self):
        for rec in self:
            if rec.name and not rec.code:
                rec.code = rec.name.strip().upper().replace(" ", "_")
