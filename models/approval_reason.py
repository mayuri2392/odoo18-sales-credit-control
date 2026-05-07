# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ApprovalReason(models.Model):
    _name = "approval.reason"
    _description = "Approval Reason"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    company_id = fields.Many2one("res.company", string="Company", help="Blank = all companies")

    reason_type = fields.Selection([
        ("credit_initial", "Credit: Initial Setup"),
        ("credit_increase", "Credit: Limit Increase"),
        ("credit_reject", "Credit: Rejection"),
        ("below_cost_reject", "Below Cost: Rejection"),
    ], required=True, index=True)

    # Proxy field — shows only credit options in the Credit Reasons form
    reason_type_credit = fields.Selection([
        ("credit_initial", "Credit: Initial Setup"),
        ("credit_increase", "Credit: Limit Increase"),
        ("credit_reject", "Credit: Rejection"),
    ], string="Reason Type", compute="_compute_reason_type_credit",
       inverse="_inverse_reason_type_credit", store=False)

    @api.depends("reason_type")
    def _compute_reason_type_credit(self):
        for rec in self:
            rec.reason_type_credit = rec.reason_type if rec.reason_type != "below_cost_reject" else False

    def _inverse_reason_type_credit(self):
        for rec in self:
            if rec.reason_type_credit:
                rec.reason_type = rec.reason_type_credit

    requires_note = fields.Boolean(
        string="Requires Details",
        help="If enabled, user must fill note/details."
    )

    _sql_constraints = [
        ("uniq_reason", "unique(name, company_id, reason_type)", "Reason already exists for this company and type.")
    ]