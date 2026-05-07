# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditLimitRejectWizard(models.TransientModel):
    _name = "credit.limit.reject.wizard"
    _description = "Credit Limit Reject Wizard"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    # ✅ Same style as request wizard: domain evaluated by webclient using context + company_id
    reason_id = fields.Many2one(
        "approval.reason",
        string="Reason",
        required=True,
        domain="[('active','=',True),"
               " ('reason_type','in', context.get('allowed_reason_types', ['credit_reject'])),"
               " '|', ('company_id','=',False), ('company_id','=',company_id)]",
    )

    reason_note = fields.Text(string="Other Details")

    # -----------------------------
    # Helpers
    # -----------------------------
    def _allowed_reason_types(self):
        allowed = (self.env.context or {}).get("allowed_reason_types")
        if isinstance(allowed, (list, tuple)) and allowed:
            return list(allowed)
        return ["credit_reject"]

    # -----------------------------
    # Onchange
    # -----------------------------
    @api.onchange("reason_id")
    def _onchange_reason_id(self):
        if self.reason_id and not self.reason_id.requires_note:
            self.reason_note = False

    # -----------------------------
    # Validation + formatting
    # -----------------------------
    def _build_reason_text(self):
        self.ensure_one()

        if not self.reason_id:
            raise UserError(_("Please select a reason."))

        # ✅ Server-side safety: enforce allowed types even if client domain is bypassed
        allowed_types = set(self._allowed_reason_types())
        if self.reason_id.reason_type not in allowed_types:
            raise UserError(_("Selected reason is not allowed for this rejection flow."))

        note = (self.reason_note or "").strip()
        if self.reason_id.requires_note and not note:
            raise UserError(_("Please enter details for the selected reason."))

        return ("%s: %s" % (self.reason_id.name, note)) if note else self.reason_id.name

    # -----------------------------
    # Action
    # -----------------------------
    def action_confirm_reject(self):
        self.ensure_one()

        partner = self.partner_id.commercial_partner_id.sudo()

        partner.write({
            "credit_reject_reason": self._build_reason_text(),
        })

        # Call your existing rejection handler
        partner.with_context(skip_reject_wizard=True).action_reject_credit()

        return {"type": "ir.actions.act_window_close"}