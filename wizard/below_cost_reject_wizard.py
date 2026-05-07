# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BelowCostRejectWizard(models.TransientModel):
    _name = "below.cost.reject.wizard"
    _description = "Below Cost Reject Wizard"

    sale_order_id = fields.Many2one("sale.order", required=True, readonly=True)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    reject_reason_id = fields.Many2one(
        "approval.reason",
        string="Rejection Reason",
        required=True,
        domain="[('active','=',True),"
               "('reason_type','=','below_cost_reject'),"
               "'|',('company_id','=',False),('company_id','=',company_id)]",
    )

    reject_note = fields.Text(string="Other Details")

    @api.onchange("reject_reason_id")
    def _onchange_reject_reason_id(self):
        if self.reject_reason_id and not self.reject_reason_id.requires_note:
            self.reject_note = False

    def _build_reject_text(self):

        if not self.reject_reason_id:
            raise UserError(_("Please select a rejection reason."))

        note = (self.reject_note or "").strip()

        if self.reject_reason_id.requires_note and not note:
            raise UserError(_("Please enter details for the selected rejection reason."))

        return ("%s: %s" % (self.reject_reason_id.name, note)) if note else self.reject_reason_id.name

    def action_submit(self):

        self.ensure_one()

        user = self.env.user

        is_mgr = user.has_group("sales_team.group_sale_manager")

        if not (is_mgr or user.has_group("base.group_system")):
            raise UserError(_("Only Sales Managers or Admin can reject below-cost approval."))

        so = self.sale_order_id.sudo()

        final_reason = self._build_reject_text()

        so.write({
            "below_cost_approval_state": "rejected",
            "below_cost_reject_reason": final_reason,
            "below_cost_approved": False,
        })

        # close manager activities
        so._below_cost_close_manager_activity()

        requester = so.below_cost_requested_by or so.user_id or so.create_uid

        if requester and requester.partner_id:
            so.message_notify(
                partner_ids=[requester.partner_id.id],
                subject=_("Below-cost approval rejected"),
                body=_(
                    "Below-cost approval REJECTED.\n"
                    "Sales Order: %(so)s\n"
                    "Rejected by: %(by)s\n"
                    "Reason: %(reason)s"
                ) % {
                    "so": so.name,
                    "by": user.name,
                    "reason": final_reason or "-",
                },
                subtype_xmlid="mail.mt_comment",
            )

        # audit log
        so.message_post(
            body=_(
                "Below-cost approval rejected by %(user)s.\n"
                "Reason: %(reason)s"
            ) % {
                "user": user.name,
                "reason": final_reason or "-",
            },
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.act_window_close"}