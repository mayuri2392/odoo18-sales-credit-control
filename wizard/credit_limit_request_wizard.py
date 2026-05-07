# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreditLimitRequestWizard(models.TransientModel):
    _name = "credit.limit.request.wizard"
    _description = "Credit Limit Request Wizard"

    partner_id = fields.Many2one("res.partner", required=True, check_company=True)
    sale_order_id = fields.Many2one("sale.order", readonly=True)

    requested_limit = fields.Float(string="Requested Credit Limit", required=True)

    title = fields.Char(compute="_compute_title", store=False)

    reason_id = fields.Many2one(
        "approval.reason",
        string="Reason",
        required=True,
        domain="[('active','=',True), ('reason_type','in', context.get('allowed_reason_types', [])), '|', ('company_id','=',False), ('company_id','=',company_id)]",
    )

    reason_note = fields.Text(string="Other Details")

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    # -------------------------------------------------------
    # TITLE
    # -------------------------------------------------------

    @api.depends_context("from_sale_order", "force_initial")
    def _compute_title(self):
        from_so = bool(self.env.context.get("from_sale_order"))
        force_initial = bool(self.env.context.get("force_initial"))

        for w in self:
            if from_so and force_initial:
                w.title = _("Request Initial Credit Setup")
            elif from_so:
                w.title = _("Request Credit Limit Increase")
            else:
                w.title = _("Request Credit Limit")

    # -------------------------------------------------------
    # REASON DOMAIN
    # -------------------------------------------------------

    def _reason_domain(self):

        from_so = bool(self.env.context.get("from_sale_order"))
        force_initial = bool(self.env.context.get("force_initial"))

        if from_so and not force_initial:
            allowed_types = ["credit_increase"]
        else:
            allowed_types = ["credit_initial"]

        return [
            ("active", "=", True),
            ("reason_type", "in", allowed_types),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.env.company.id),
        ]

    @api.onchange("partner_id", "sale_order_id")
    def _onchange_reason_domain(self):
        return {"domain": {"reason_id": self._reason_domain()}}

    @api.onchange("reason_id")
    def _onchange_reason_id(self):
        if self.reason_id and not self.reason_id.requires_note:
            self.reason_note = False

    @api.onchange("partner_id")
    def _onchange_partner_id_fill_default(self):
        if self.partner_id:
            partner = self.partner_id.commercial_partner_id
            tier_limit = partner.credit_tier_id.default_credit_limit if partner.credit_tier_id else 0.0

            if tier_limit and (not self.requested_limit or self.requested_limit <= 0):
                self.requested_limit = tier_limit

    # -------------------------------------------------------
    # APPROVER PICK
    # -------------------------------------------------------

    def _pick_credit_approver_user(self):

        if self.sale_order_id and self.sale_order_id.company_id:
            target_company = self.sale_order_id.company_id
        elif self.partner_id and self.partner_id.company_id:
            target_company = self.partner_id.company_id
        else:
            target_company = self.env.company

        admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
        acc_mgr_group = self.env.ref("account.group_account_manager", raise_if_not_found=False)

        candidates = self.env["res.users"].sudo().browse()

        if acc_mgr_group:
            candidates = acc_mgr_group.users.sudo().filtered(lambda u: u.active)

        if not candidates:
            return admin_user

        if target_company:
            same_company = candidates.filtered(lambda u: target_company in u.company_ids)
            candidates = same_company or candidates

        non_system = candidates.filtered(lambda u: not u.has_group("base.group_system"))

        if non_system:
            return non_system.sorted("id")[0]

        return candidates.sorted("id")[0] or admin_user

    # -------------------------------------------------------
    # BUILD REASON
    # -------------------------------------------------------

    def _build_reason_text(self):

        if not self.reason_id:
            raise UserError(_("Please select a reason."))

        note = (self.reason_note or "").strip()

        if self.reason_id.requires_note and not note:
            raise UserError(_("Please enter details for the selected reason."))

        return ("%s: %s" % (self.reason_id.name, note)) if note else self.reason_id.name

    # -------------------------------------------------------
    # SUBMIT REQUEST
    # -------------------------------------------------------

    def action_submit(self):

        self.ensure_one()

        partner = self.partner_id.commercial_partner_id.sudo()

        from_sale_order = bool(self.env.context.get("from_sale_order"))
        force_initial = bool(self.env.context.get("force_initial"))

        if partner.credit_request_state == "requested":
            raise UserError(_("A credit limit request is already pending approval."))

        if not from_sale_order and partner.credit_setup_done:
            raise UserError(
                _("Initial credit setup is already approved. Further increases must be requested from a Sales Order.")
            )

        final_reason = self._build_reason_text()

        # -------------------------------------------------------
        # WRITE REQUEST
        # -------------------------------------------------------

        partner.write({
            "credit_limit_requested": self.requested_limit,
            "credit_request_reason": final_reason,
            "credit_request_state": "requested",
            "credit_requested_by": self.env.user.id,
            "credit_reject_reason": False,
            "credit_limit_approved": 0.0,
            "credit_request_sale_order_id": self.sale_order_id.id if (from_sale_order and self.sale_order_id) else False,
        })

        # -------------------------------------------------------
        # SALES ORDER STATE UPDATE (FLOW 2)
        # -------------------------------------------------------

        if from_sale_order and self.sale_order_id and not force_initial:
            self.sale_order_id.sudo().write({
                "credit_increase_state": "requested",
                "credit_increase_reject_reason": False,
                "credit_increase_requested_by": self.env.user.id,
                "credit_increase_requested_on": fields.Datetime.now(),
            })

        # -------------------------------------------------------
        # AUDIT TRAIL - CUSTOMER
        # -------------------------------------------------------

        partner.message_post(
            body=_(
                "Credit request submitted by %(user)s.\n"
                "Requested credit limit: %(limit)s\n"
                "Reason: %(reason)s"
            ) % {
                "user": self.env.user.name,
                "limit": self.requested_limit,
                "reason": final_reason or "-",
            },
            subtype_xmlid="mail.mt_note",
        )

        # -------------------------------------------------------
        # AUDIT TRAIL - SALES ORDER (FLOW 2)
        # -------------------------------------------------------

        if self.sale_order_id:
            self.sale_order_id.message_post(
                body=_(
                    "Credit increase request submitted.\n"
                    "Requested credit limit: %(limit)s\n"
                    "Requested by: %(user)s"
                ) % {
                    "limit": self.requested_limit,
                    "user": self.env.user.name,
                },
                subtype_xmlid="mail.mt_note",
            )

        # -------------------------------------------------------
        # CREATE APPROVAL ACTIVITY
        # -------------------------------------------------------

        approver = self._pick_credit_approver_user()

        if not approver:
            return {"type": "ir.actions.act_window_close"}

        Activity = self.env["mail.activity"].sudo()
        todo_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)

        if not todo_type:
            return {"type": "ir.actions.act_window_close"}

        note = _(
            "Customer: %(customer)s\n"
            "Requested Limit: %(limit).2f\n"
            "Requested By: %(by)s\n"
            "Reason: %(reason)s"
        ) % {
            "customer": partner.name,
            "limit": self.requested_limit,
            "by": self.env.user.name,
            "reason": final_reason or "-",
        }

        model_id = self.env["ir.model"]._get_id("res.partner")

        existing = Activity.search([
            ("res_model_id", "=", model_id),
            ("res_id", "=", partner.id),
            ("activity_type_id", "=", todo_type.id),
            ("state", "=", "planned"),
        ], limit=1)

        if existing:
            existing.write({
                "user_id": approver.id,
                "summary": _("Credit Limit Approval Required"),
                "note": note,
            })
        else:
            Activity.create({
                "activity_type_id": todo_type.id,
                "res_model_id": model_id,
                "res_id": partner.id,
                "user_id": approver.id,
                "summary": _("Credit Limit Approval Required"),
                "note": note,
            })

        return {"type": "ir.actions.act_window_close"}