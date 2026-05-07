# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # =========================================================
    # CREDIT TIER
    # =========================================================
    credit_tier_id = fields.Many2one(
        "credit.tier",
        string="Credit Tier",
        tracking=True,
        help="Tier/category that defines default credit policy (Gold/Silver/etc).",
    )

    tier_default_credit_limit = fields.Float(
        string="Tier Default Credit Limit",
        compute="_compute_tier_default_credit_limit",
        store=False,
        readonly=True,
    )

    @api.depends("credit_tier_id", "credit_tier_id.default_credit_limit")
    def _compute_tier_default_credit_limit(self):
        for partner in self:
            partner.tier_default_credit_limit = (
                partner.credit_tier_id.default_credit_limit if partner.credit_tier_id else 0.0
            )

    # =========================================================
    # UI DISPLAY: Tag-style badge
    # =========================================================
    credit_tier_tag_ids = fields.Many2many(
        comodel_name="credit.tier",
        string="Credit Tier Tag",
        compute="_compute_credit_tier_tag_ids",
        store=False,
        readonly=True,
    )

    @api.depends("credit_tier_id")
    def _compute_credit_tier_tag_ids(self):
        empty = self.env["credit.tier"]
        for partner in self:
            partner.credit_tier_tag_ids = partner.credit_tier_id or empty

    # =========================================================
    # CREDIT REQUEST FLOW
    # =========================================================
    credit_request_state = fields.Selection(
        [
            ("none", "No Request"),
            ("requested", "Requested"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Credit Request State",
        default="none",
        tracking=True,
        copy=False,
    )

    credit_limit_requested = fields.Float(string="Requested Credit Limit", copy=False)
    credit_limit_approved = fields.Float(string="Approved Credit Limit", copy=False)
    credit_request_reason = fields.Text(string="Reason for Credit Request", copy=False)

    credit_reject_reason = fields.Text(string="Reject Reason", readonly=True, copy=False)
    credit_requested_by = fields.Many2one("res.users", string="Requested By", readonly=True, copy=False)
    credit_approved_by = fields.Many2one("res.users", string="Approved By", readonly=True, copy=False)
    credit_approved_on = fields.Datetime(string="Approved On", readonly=True, copy=False)

    credit_request_sale_order_id = fields.Many2one(
        "sale.order",
        string="Related Sales Order (Flow-2)",
        readonly=True,
        copy=False,
    )

    company_currency_id = fields.Many2one(
        "res.currency",
        string="Company Currency",
        compute="_compute_company_currency_id",
        readonly=True,
    )

    current_exposure = fields.Monetary(
        string="Current Exposure",
        currency_field="company_currency_id",
        compute="_compute_current_exposure",
        readonly=True,
    )

    @api.depends("company_id")
    def _compute_company_currency_id(self):
        for partner in self:
            partner.company_currency_id = partner.company_id.currency_id or self.env.company.currency_id

    @api.depends("credit", "credit_to_invoice", "company_id")
    def _compute_current_exposure(self):
        for partner in self:
            credit_to_invoice = getattr(partner, "credit_to_invoice", 0.0) or 0.0
            partner.current_exposure = (partner.credit or 0.0) + credit_to_invoice

    credit_setup_done = fields.Boolean(
        string="Initial Credit Setup Completed",
        default=False,
        copy=False,
    )

    is_system_admin_user = fields.Boolean(
        compute="_compute_is_system_admin_user",
        store=False,
    )

    def _compute_is_system_admin_user(self):
        is_admin = self.env.user.has_group("base.group_system")
        for rec in self:
            rec.is_system_admin_user = is_admin

    # =========================================================
    # ROLE HELPERS
    # =========================================================
    def _is_credit_setup_requestor_user(self):
        """Only explicitly assigned requestors can submit Flow-1.
        This preserves your design choice of keeping Admin hidden/out unless
        you intentionally assign the custom group.
        """
        return self.env.user.has_group("sales_credit_control.group_credit_setup_requestor")

    def _is_credit_approver_user(self):
        return (
            self.env.user.has_group("account.group_account_manager")
            or self.env.user.has_group("base.group_system")
        )

    # =========================================================
    # SAFETY: If someone sets credit_limit directly, align flags
    # =========================================================
    def write(self, vals):
        old_limits = {}
        if "credit_limit" in vals:
            for partner in self:
                old_limits[partner.id] = partner.credit_limit or 0.0

        res = super().write(vals)

        if self.env.context.get("skip_credit_reconcile"):
            return res

        if "credit_limit" in vals:
            for partner in self.sudo():
                old = old_limits.get(partner.id, 0.0)
                new = partner.credit_limit or 0.0

                if old != new:
                    partner.message_post(
                        body=_(
                            "Partner credit limit changed from %(old)s to %(new)s by %(user)s."
                        ) % {
                            "old": old,
                            "new": new,
                            "user": self.env.user.name,
                        },
                        subtype_xmlid="mail.mt_note",
                    )

                if new > 0 and not partner.credit_setup_done:
                    partner.with_context(skip_credit_reconcile=True).write({
                        "credit_setup_done": True,
                        "credit_request_state": "approved",
                    })

        return res

    # =========================================================
    # FLOW-1: OPEN REQUEST WIZARD
    # =========================================================
    def action_open_credit_request_wizard(self):
        self.ensure_one()
        partner = self.commercial_partner_id

        if not self._is_credit_setup_requestor_user():
            raise UserError(_("You are not allowed to request initial credit setup."))

        if partner.credit_setup_done:
            raise UserError(_(
                "Initial credit setup is already approved. "
                "Further increases must be requested from a Sales Order."
            ))

        if partner.credit_request_state == "requested":
            raise UserError(_("A credit request is already pending approval."))

        if not partner.credit_tier_id:
            raise UserError(_("Please select a Credit Tier first."))

        default_limit = partner.credit_tier_id.default_credit_limit or 0.0

        return {
            "type": "ir.actions.act_window",
            "name": _("Request Credit Limit"),
            "res_model": "credit.limit.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": partner.id,
                "default_requested_limit": default_limit,
                "from_sale_order": False,
                "allowed_reason_types": ["credit_initial"],
            },
        }

    # =========================================================
    # HELPERS: NOTIFICATION TARGET
    # =========================================================
    def _credit_notify_partner_ids(self, commercial_partner, so=None):
        """Notify only the actual requester."""
        requester_user = False

        if so and getattr(so, "credit_increase_requested_by", False):
            requester_user = so.credit_increase_requested_by
        else:
            requester_user = commercial_partner.credit_requested_by

        if requester_user and requester_user.partner_id:
            return [requester_user.partner_id.id]
        return []

    # =========================================================
    # ACCOUNTING ACTIONS
    # =========================================================
    def action_approve_credit(self):
        self.ensure_one()

        if not self._is_credit_approver_user():
            raise UserError(_("Only Accounting Managers can approve credit requests."))

        if self.credit_request_state != "requested":
            raise UserError(_("Only requested credit records can be approved."))

        approved_limit = self.credit_limit_approved or self.credit_limit_requested
        if not approved_limit or approved_limit <= 0:
            raise UserError(_("Approved credit limit must be greater than 0."))

        so = self.credit_request_sale_order_id.sudo()
        company = so.company_id if so else (self.company_id or self.env.company)
        commercial_partner = self.commercial_partner_id.with_company(company).sudo()

        notify_partner_ids = self._credit_notify_partner_ids(commercial_partner, so=so)

        commercial_partner.write({
            "credit_limit": approved_limit,
            "credit_setup_done": True,
            "credit_request_state": "approved",
            "credit_approved_by": self.env.user.id,
            "credit_approved_on": fields.Datetime.now(),
            "credit_reject_reason": False,
            "credit_limit_approved": approved_limit,
        })

        if so:
            so.with_context(skip_credit_sync=True).sudo().write({
                "credit_increase_state": "approved",
                "credit_increase_reject_reason": False,
                "credit_increase_approved": True,
            })

            so.message_post(
                body=_(
                    "Credit limit increase APPROVED.\n"
                    "Customer: %s\n"
                    "New credit limit: %s"
                ) % (commercial_partner.name, commercial_partner.credit_limit),
                subtype_xmlid="mail.mt_note",
            )

        commercial_partner.activity_ids.action_done()

        if notify_partner_ids:
            msg = _(
                "Credit limit request APPROVED.\n"
                "Customer: %(customer)s\n"
                "%(so_line)s"
                "New credit limit: %(limit)s"
            ) % {
                "customer": commercial_partner.name,
                "so_line": (("Sales Order: %s\n" % so.name) if so else ""),
                "limit": commercial_partner.credit_limit,
            }

            commercial_partner.message_notify(
                partner_ids=notify_partner_ids,
                body=msg,
                subject=_("Credit limit request approved"),
                subtype_xmlid="mail.mt_comment",
            )

        commercial_partner.message_post(
            body=_(
                "Credit request approved by %(user)s.\n"
                "New credit limit: %(limit)s"
            ) % {
                     "user": self.env.user.name,
                     "limit": commercial_partner.credit_limit,
                 },
            subtype_xmlid="mail.mt_note",
        )

        commercial_partner.write({
            "credit_request_sale_order_id": False,
        })

        return True

    def action_open_reject_wizard(self):
        self.ensure_one()

        if not self._is_credit_approver_user():
            raise UserError(_("Only Accounting Managers can reject credit requests."))

        if self.credit_request_state != "requested":
            raise UserError(_("Only requested credit records can be rejected."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Credit Limit Request"),
            "res_model": "credit.limit.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "allowed_reason_types": ["credit_reject"],
            },
        }

    def action_reject_credit(self):
        for partner in self:
            if not partner._is_credit_approver_user():
                raise UserError(_("Only Accounting Managers can reject credit requests."))

            if partner.credit_request_state != "requested":
                raise UserError(_("Only requested credit records can be rejected."))

            if not partner.credit_reject_reason:
                raise UserError(_("Rejection reason is mandatory."))

            so = partner.credit_request_sale_order_id.sudo()
            company = so.company_id if so else (partner.company_id or self.env.company)
            commercial_partner = partner.commercial_partner_id.with_company(company).sudo()

            notify_partner_ids = partner._credit_notify_partner_ids(commercial_partner, so=so)

            commercial_partner.write({
                "credit_request_state": "rejected",
                "credit_approved_by": self.env.user.id,
                "credit_approved_on": fields.Datetime.now(),
                "credit_reject_reason": partner.credit_reject_reason,
                "credit_limit_approved": 0.0,
            })

            if so:
                so.with_context(skip_credit_sync=True).sudo().write({
                    "credit_increase_state": "rejected",
                    "credit_increase_reject_reason": partner.credit_reject_reason,
                    "credit_increase_approved": False,
                })

                so.message_post(
                    body=_(
                        "Credit limit increase REJECTED.\n"
                        "Customer: %s\n"
                        "Reason: %s"
                    ) % (commercial_partner.name, partner.credit_reject_reason or "-"),
                    subtype_xmlid="mail.mt_note",
                )

            commercial_partner.activity_ids.action_done()

            if notify_partner_ids:
                msg = _(
                    "Credit limit request REJECTED.\n"
                    "Customer: %(customer)s\n"
                    "%(so_line)s"
                    "Reason: %(reason)s"
                ) % {
                    "customer": commercial_partner.name,
                    "so_line": (("Sales Order: %s\n" % so.name) if so else ""),
                    "reason": partner.credit_reject_reason or "-",
                }

                commercial_partner.message_notify(
                    partner_ids=notify_partner_ids,
                    body=msg,
                    subject=_("Credit limit request rejected"),
                    subtype_xmlid="mail.mt_comment",
                )

            commercial_partner.message_post(
                body=_(
                    "Credit request rejected by %(user)s.\n"
                    "Reason: %(reason)s"
                ) % {
                         "user": self.env.user.name,
                         "reason": partner.credit_reject_reason or "-",
                     },
                subtype_xmlid="mail.mt_note",
            )

            commercial_partner.write({
                "credit_request_sale_order_id": False,
            })

        return True