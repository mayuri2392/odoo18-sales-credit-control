# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.fields import Date


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # =========================================================
    # CREDIT FLOW
    # =========================================================
    credit_status = fields.Char(
        string="Credit Status",
        compute="_compute_credit_metrics",
        store=False,
        readonly=True,
    )
    credit_setup_missing = fields.Boolean(
        string="Credit Setup Missing",
        compute="_compute_credit_metrics",
        store=False,
        readonly=True,
    )
    credit_exceeded = fields.Boolean(
        string="Credit Exceeded",
        compute="_compute_credit_metrics",
        store=False,
        readonly=True,
    )

    credit_request_state = fields.Selection(
        related="partner_id.credit_request_state",
        store=False,
        readonly=True,
    )
    credit_reject_reason = fields.Text(
        related="partner_id.credit_reject_reason",
        store=False,
        readonly=True,
    )

    partner_credit_pending = fields.Boolean(
        string="Customer Credit Pending",
        compute="_compute_partner_credit_pending",
        store=False,
        readonly=True,
    )

    partner_credit_setup_done = fields.Boolean(
        string="Credit Setup Done (Compat)",
        compute="_compute_partner_credit_setup_done",
        store=False,
        readonly=True,
    )

    credit_increase_requested_by = fields.Many2one(
        "res.users",
        string="Credit Increase Requested By",
        readonly=True,
        copy=False,
    )
    credit_increase_requested_on = fields.Datetime(
        string="Credit Increase Requested On",
        readonly=True,
        copy=False,
    )

    credit_increase_state = fields.Selection(
        [
            ("none", "No Request"),
            ("requested", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Credit Increase Status",
        default="none",
        readonly=True,
        copy=False,
    )
    credit_increase_reject_reason = fields.Text(
        string="Credit Increase Rejection Reason",
        readonly=True,
        copy=False,
    )
    credit_increase_approved = fields.Boolean(
        string="Credit Increase Approved (This SO)",
        default=False,
        copy=False,
        readonly=True,
    )

    # =========================================================
    # BELOW COST APPROVAL FLOW
    # =========================================================
    below_cost_approval_state = fields.Selection(
        [
            ("none", "No Request"),
            ("requested", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Below Cost Approval Status",
        default="none",
        readonly=True,
        copy=False,
    )

    below_cost_reject_reason = fields.Text(
        string="Below Cost Rejection Reason",
        readonly=True,
        copy=False,
    )

    below_cost_approved = fields.Boolean(
        string="Below Cost Approved (This SO)",
        default=False,
        copy=False,
        readonly=True,
    )

    below_cost_requested_by = fields.Many2one(
        "res.users",
        string="Below Cost Requested By",
        readonly=True,
        copy=False,
    )
    below_cost_requested_on = fields.Datetime(
        string="Below Cost Requested On",
        readonly=True,
        copy=False,
    )

    # IMPORTANT: store=True for reliable button visibility
    below_cost_warning = fields.Boolean(
        string="Below Cost Warning",
        compute="_compute_below_cost_warning",
        store=True,
        readonly=True,
        compute_sudo=True,
    )
    below_cost_warning_message = fields.Char(
        string="Below Cost Warning Message",
        compute="_compute_below_cost_warning",
        store=True,
        readonly=True,
        compute_sudo=True,
    )

    below_cost_approval_snapshot = fields.Char(
        string="Below Cost Approval Snapshot",
        readonly=True,
        copy=False,
    )

    below_cost_approved_by = fields.Many2one(
        "res.users",
        string="Below Cost Approved By",
        readonly=True,
        copy=False,
    )

    below_cost_approved_on = fields.Datetime(
        string="Below Cost Approved On",
        readonly=True,
        copy=False,
    )

    # =========================================================
    # USER FLAGS
    # =========================================================
    below_cost_request_allowed = fields.Boolean(
        string="Below Cost Request Allowed",
        compute="_compute_below_cost_request_allowed",
        store=False,
        readonly=True,
    )

    is_sales_manager_user = fields.Boolean(
        compute="_compute_user_flags",
        store=False,
        readonly=True,
    )
    is_system_admin_user = fields.Boolean(
        compute="_compute_user_flags",
        store=False,
        readonly=True,
    )
    is_sales_user_only = fields.Boolean(
        compute="_compute_user_flags",
        store=False,
        readonly=True,
    )

    # =========================================================
    # USER / ROLE HELPERS
    # =========================================================
    def _user_is_sales_manager(self, user):
        return user.has_group("sales_team.group_sale_manager")

    def _user_is_salesperson(self, user):
        return any([
            user.has_group("sales_team.group_sale_salesman"),
            user.has_group("sales_team.group_sale_salesman_all_leads"),
            user.has_group("sales_team.group_sale_manager"),
        ])

    def _user_is_sales_user(self, user):
        return self._user_is_salesperson(user)

    def _user_is_salesman_only(self, user):
        is_mgr = self._user_is_sales_manager(user)
        is_admin = user.has_group("base.group_system")
        is_salesperson = (
                user.has_group("sales_team.group_sale_salesman")
                or user.has_group("sales_team.group_sale_salesman_all_leads")
        )
        return bool(is_salesperson and not is_mgr and not is_admin)

    def _user_is_admin(self, user):
        return user.has_group("base.group_system")

    def _user_is_accounting_user(self, user):
        return (
                user.has_group("account.group_account_user")
                or user.has_group("account.group_account_manager")
        )

    def _user_is_manager_or_admin(self, user):
        return self._user_is_sales_manager(user) or self._user_is_admin(user)



    @api.depends_context("uid")
    def _compute_user_flags(self):
        user = self.env.user
        for order in self:
            order.is_sales_manager_user = self._user_is_sales_manager(user)
            order.is_system_admin_user = user.has_group("base.group_system")
            order.is_sales_user_only = self._user_is_salesman_only(user)

    @api.depends_context("uid")
    def _compute_below_cost_request_allowed(self):
        user = self.env.user
        is_admin = user.has_group("base.group_system")
        is_salesman_only = self._user_is_salesman_only(user)

        for order in self:
            order.below_cost_request_allowed = bool(is_admin or is_salesman_only)

    @api.depends("credit_setup_missing")
    def _compute_partner_credit_setup_done(self):
        for order in self:
            order.partner_credit_setup_done = not bool(order.credit_setup_missing)

    @api.depends("partner_id.credit_request_state")
    def _compute_partner_credit_pending(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id if order.partner_id else False
            order.partner_credit_pending = bool(partner and partner.credit_request_state == "requested")

    # =========================================================
    # CREDIT LIMIT PARSER
    # =========================================================
    def _partner_credit_limit_amount(self, partner, company=None):
        company = company or self.env.company
        limit = getattr(partner, "credit_limit", 0.0) or 0.0

        if isinstance(limit, (int, float)):
            return float(limit)

        if isinstance(limit, dict):
            cid = str(company.id)
            if cid in limit:
                return float(limit.get(cid) or 0.0)
            try:
                return float(next(iter(limit.values())) or 0.0)
            except Exception:
                return 0.0

        return 0.0

    # =========================================================
    # CREDIT METRICS
    # =========================================================
    @api.depends(
        "partner_id",
        "partner_id.credit_limit",
        "partner_id.credit",
        "partner_id.credit_to_invoice",
        "partner_id.credit_request_state",
        "amount_total",
        "currency_id",
        "company_id",
        "date_order",
        "state",
        "credit_increase_state",
        "credit_increase_approved",
    )
    def _compute_credit_metrics(self):
        for order in self:
            order.credit_status = ""
            order.credit_exceeded = False
            order.credit_setup_missing = False

            if not order.partner_id:
                continue

            partner = order.partner_id.commercial_partner_id.sudo()
            company = order.company_id

            setup_done = bool(getattr(partner, "credit_setup_done", False))
            limit = order._partner_credit_limit_amount(partner, company=company)

            if not setup_done or limit <= 0:
                order.credit_setup_missing = True
                order.credit_status = _("Credit setup not approved")
                continue

            exposure = (partner.credit or 0.0) + (getattr(partner, "credit_to_invoice", 0.0) or 0.0)
            if order.state not in ("cancel",):
                conv_date = order.date_order or order.create_date or Date.today()
                exposure += order.currency_id._convert(
                    order.amount_total,
                    company.currency_id,
                    company,
                    conv_date,
                )

            exceeds = exposure > limit

            # If this SO already got approved increase, do not keep showing it as blocked.
            if exceeds and order.credit_increase_approved and order.credit_increase_state == "approved":
                exceeds = False

            order.credit_exceeded = exceeds

            if order.credit_increase_state == "requested":
                order.credit_status = _("Credit increase approval pending")
            elif order.credit_increase_state == "rejected":
                order.credit_status = _("Credit increase rejected")
            elif exceeds:
                exceeded = exposure - limit
                order.credit_status = _("Exceeds by %s %s") % (
                    f"{exceeded:,.2f}",
                    company.currency_id.name,
                )
            else:
                percent = (exposure / limit) * 100.0 if limit else 0.0
                order.credit_status = _("%s%% used") % f"{percent:.0f}"

    @api.onchange("order_line", "partner_id", "currency_id", "company_id", "date_order")
    def _onchange_force_credit_refresh(self):
        for order in self:
            order._compute_credit_metrics()

    def _sync_credit_increase_state_after_change(self):
        for order in self:
            if order.credit_increase_state == "requested":
                continue

            if order.credit_exceeded and order.credit_increase_state in ("approved", "rejected"):
                order.with_context(skip_credit_sync=True).sudo().write({
                    "credit_increase_state": "none",
                    "credit_increase_reject_reason": False,
                    "credit_increase_approved": False,
                })

            if not order.credit_exceeded and order.credit_increase_reject_reason:
                order.with_context(skip_credit_sync=True).sudo().write({
                    "credit_increase_reject_reason": False
                })

    def write(self, vals):
        res = super().write(vals)

        if not self.env.context.get("skip_credit_sync"):
            credit_trigger_fields = {"partner_id", "state", "currency_id", "company_id", "date_order"}
            if credit_trigger_fields.intersection(vals.keys()):
                self._sync_credit_increase_state_after_change()

        below_cost_trigger_fields = {
            "order_line",
            "currency_id",
            "company_id",
            "date_order",
        }
        if below_cost_trigger_fields.intersection(vals.keys()):
            self._sync_below_cost_state_after_change()

        return res

    # =========================================================
    # FLOW-2: CREDIT INCREASE REQUEST
    # =========================================================
    def action_request_credit(self):
        self.ensure_one()

        user = self.env.user
        is_system_admin = user.has_group("base.group_system")
        is_sales = self._user_is_sales_user(user)
        is_accounting = (
                user.has_group("account.group_account_user")
                or user.has_group("account.group_account_manager")
        )

        if not (is_system_admin or is_sales):
            if is_accounting:
                raise UserError(_("Accounting cannot submit credit requests. Ask Sales."))
            raise UserError(_("You are not allowed to request a credit limit increase."))

        partner = self.partner_id.commercial_partner_id.sudo()
        if not partner:
            raise UserError(_("Please select a customer first."))

        limit = self._partner_credit_limit_amount(partner, company=self.company_id)
        if not getattr(partner, "credit_setup_done", False) or limit <= 0:
            raise UserError(_(
                "Initial credit is not approved.\n\n"
                "Please open the Customer and complete Credit Setup first.\n"
                "After approval, you can request a credit increase from the Sales Order if needed."
            ))

        if not self.credit_exceeded:
            raise UserError(_("This Sales Order does not exceed the approved credit limit."))

        if self.credit_increase_state == "requested":
            raise UserError(_("Credit approval is already pending for this Sales Order."))

        if partner.credit_request_state == "requested":
            raise UserError(_("A credit request is already pending for this customer."))

        company = self.company_id
        conv_date = self.date_order or self.create_date or Date.today()

        exposure = (partner.credit or 0.0) + (getattr(partner, "credit_to_invoice", 0.0) or 0.0)
        if self.state not in ("cancel",):
            exposure += self.currency_id._convert(
                self.amount_total,
                company.currency_id,
                company,
                conv_date,
            )

        suggested_limit = company.currency_id._convert(
            exposure,
            self.currency_id,
            company,
            conv_date,
        )

        current_limit_so_cur = company.currency_id._convert(
            limit,
            self.currency_id,
            company,
            conv_date,
        )
        suggested_limit = max(suggested_limit, current_limit_so_cur)

        # Audit trail on Sales Order
        self.message_post(
            body=_(
                "Credit increase request initiated by %(user)s.\n"
                "Customer: %(customer)s\n"
                "Suggested credit limit: %(limit)s"
            ) % {
                     "user": self.env.user.name,
                     "customer": partner.display_name,
                     "limit": suggested_limit,
                 },
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Request Credit Limit Increase"),
            "res_model": "credit.limit.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "from_sale_order": True,
                "default_partner_id": partner.id,
                "default_sale_order_id": self.id,
                "default_requested_limit": suggested_limit,
                "allowed_reason_types": ["credit_increase"],
            }
        }

    # =========================================================
    # BELOW COST WARNING
    # =========================================================
    @api.depends(
        "order_line.price_unit",
        "order_line.product_id",
        "order_line.display_type",
        "order_line.product_uom_qty",
        "order_line.product_uom",
        "order_line.discount",
        "order_line.sequence",
        "order_line.product_id.standard_price",
        "order_line.product_id.product_tmpl_id.standard_price",
        "currency_id",
        "company_id",
        "date_order",
        "create_date",
        "below_cost_approved",
        "below_cost_approval_state",
        "below_cost_approval_snapshot",
    )
    def _compute_below_cost_warning(self):
        for order in self:
            snapshot_valid = order._is_below_cost_approval_snapshot_valid()
            if snapshot_valid:
                order.below_cost_warning = False
                order.below_cost_warning_message = False
                continue

            order.below_cost_warning = False
            order.below_cost_warning_message = False

            company = order.company_id
            conversion_date = order.date_order or order.create_date or Date.today()

            for line in order.order_line:
                if line.display_type:
                    continue

                product = line.product_id.sudo()
                if not product:
                    continue

                base_cost = product.standard_price or product.product_tmpl_id.standard_price or 0.0
                if base_cost <= 0:
                    continue

                cost = company.currency_id._convert(
                    base_cost,
                    order.currency_id,
                    company,
                    conversion_date,
                )

                if line.price_unit < cost:
                    order.below_cost_warning = True
                    order.below_cost_warning_message = _(
                        "This order is priced below cost. "
                        "Cost: %s %s | Sales Price: %s %s"
                    ) % (
                                                           f"{cost:,.2f}",
                                                           order.currency_id.name,
                                                           f"{line.price_unit:,.2f}",
                                                           order.currency_id.name,
                                                       )
                    break

    # =========================================================
    # RESET APPROVAL ONLY IF ORDER CHANGES AGAIN
    # =========================================================

    def _sync_below_cost_state_after_change(self):
        for order in self:
            current_snapshot = order._get_below_cost_snapshot()
            snapshot_valid = (
                    order.below_cost_approved
                    and order.below_cost_approval_state == "approved"
                    and order.below_cost_approval_snapshot == current_snapshot
            )

            if snapshot_valid:
                continue

            vals = {}
            if order.below_cost_approval_state != "none":
                vals["below_cost_approval_state"] = "none"
            if order.below_cost_reject_reason:
                vals["below_cost_reject_reason"] = False
            if order.below_cost_approved:
                vals["below_cost_approved"] = False
            if order.below_cost_requested_by:
                vals["below_cost_requested_by"] = False
            if order.below_cost_requested_on:
                vals["below_cost_requested_on"] = False
            if order.below_cost_approval_snapshot:
                vals["below_cost_approval_snapshot"] = False
            if order.below_cost_approved_by:
                vals["below_cost_approved_by"] = False
            if order.below_cost_approved_on:
                vals["below_cost_approved_on"] = False

            if vals:
                order.sudo().write(vals)
                order._below_cost_close_manager_activity()

            order._compute_below_cost_warning()

    # =========================================================
    # BELOW COST ACTIVITIES
    # =========================================================
    def _below_cost_activity_type(self):
        return self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)

    def _below_cost_pick_approver_user(self):
        self.ensure_one()
        Users = self.env["res.users"].sudo()

        managers = Users.browse()
        grp = self.env.ref("sales_team.group_sale_manager", raise_if_not_found=False)
        if grp:
            managers |= grp.users

        managers = managers.filtered(lambda u: u.active)

        admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
        if admin_user:
            managers = managers.filtered(lambda u: u.id != admin_user.id)

        if self.company_id:
            same_company = managers.filtered(lambda u: self.company_id in u.company_ids)
            managers = same_company or managers

        non_system = managers.filtered(lambda u: not u.has_group("base.group_system"))
        managers = non_system or managers

        if not managers:
            raise UserError(_(
                "No Sales Manager user found for below-cost approval.\n\n"
                "Please add at least one active user to the Sales Manager group."
            ))

        return managers.sorted(key=lambda u: u.id)[0]

    def _below_cost_manager_activity_domain(self, user):
        self.ensure_one()
        act_type = self._below_cost_activity_type()
        if not act_type:
            return []
        return [
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("user_id", "=", user.id),
            ("activity_type_id", "=", act_type.id),
            ("state", "!=", "done"),
        ]

    def _below_cost_ensure_manager_activity(self, approver):
        self.ensure_one()
        act_type = self._below_cost_activity_type()
        if not act_type:
            return

        Activity = self.env["mail.activity"].sudo()
        existing = Activity.search(self._below_cost_manager_activity_domain(approver), limit=1)
        if existing:
            return

        note = _(
            "Sales Order %(so)s contains lines priced below cost.\n"
            "Please approve or reject on the Sales Order."
        ) % {"so": self.name}

        Activity.create({
            "activity_type_id": act_type.id,
            "summary": _("Below-Cost Approval Needed"),
            "note": note,
            "user_id": approver.id,
            "res_model_id": self.env["ir.model"]._get_id(self._name),
            "res_id": self.id,
        })

    def _below_cost_close_manager_activity(self):
        self.ensure_one()
        act_type = self._below_cost_activity_type()
        if not act_type:
            return
        Activity = self.env["mail.activity"].sudo()
        acts = Activity.search([
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("activity_type_id", "=", act_type.id),
            ("state", "!=", "done"),
        ])
        if acts:
            acts.action_done()

    def _get_below_cost_snapshot(self):
        self.ensure_one()
        parts = []

        for line in self.order_line.sorted(key=lambda l: (l.sequence, l.id)):
            if line.display_type:
                continue

            product_id = line.product_id.id or 0
            qty = line.product_uom_qty or 0.0
            price = line.price_unit or 0.0
            discount = line.discount or 0.0
            uom_id = line.product_uom.id or 0

            parts.append(
                f"{product_id}|{uom_id}|{qty:.6f}|{price:.6f}|{discount:.6f}"
            )

        return "||".join(parts)

    def _is_below_cost_approval_snapshot_valid(self):
        self.ensure_one()
        if not self.below_cost_approved or self.below_cost_approval_state != "approved":
            return False
        return self.below_cost_approval_snapshot == self._get_below_cost_snapshot()

    # =========================================================
    # FLOW-3: BELOW COST REQUEST / APPROVE / REJECT
    # =========================================================
    def action_request_below_cost_approval(self):
        self.ensure_one()

        user = self.env.user
        is_admin = user.has_group("base.group_system")
        is_salesperson = self._user_is_salesperson(user)

        if not (is_admin or is_salesperson):
            raise UserError(_("Only Sales users can request below-cost approval."))

        if self._user_is_sales_manager(user) and not is_admin:
            raise UserError(_("Sales Managers cannot request below-cost approval because they are the approvers."))

        if not self.below_cost_warning:
            raise UserError(_("This Sales Order is not below cost. No approval is required."))

        if self.below_cost_approval_state == "requested":
            raise UserError(_("Below-cost approval is already pending for this Sales Order."))

        if self.below_cost_approval_state == "approved" and self.below_cost_approved:
            raise UserError(_("Below-cost selling is already approved for this Sales Order."))

        self.sudo().write({
            "below_cost_approval_state": "requested",
            "below_cost_reject_reason": False,
            "below_cost_approved": False,
            "below_cost_requested_by": user.id,
            "below_cost_requested_on": fields.Datetime.now(),
            "below_cost_approval_snapshot": False,
            "below_cost_approved_by": False,
            "below_cost_approved_on": False,
        })

        approver = self._below_cost_pick_approver_user()
        self._below_cost_ensure_manager_activity(approver)

        self.message_post(
            body=_(
                "Below-cost approval requested by %(user)s.\n"
                "Approver: %(approver)s"
            ) % {
                     "user": user.name,
                     "approver": approver.name,
                 },
            subtype_xmlid="mail.mt_note",
        )
        return True

    def action_approve_below_cost(self):
        self.ensure_one()

        user = self.env.user
        if not (self._user_is_sales_manager(user) or user.has_group("base.group_system")):
            raise UserError(_("Only Sales Managers or Admin can approve below-cost selling."))

        if not self.below_cost_warning:
            raise UserError(_("This Sales Order is not below cost. No approval is required."))

        if self.below_cost_approval_state == "approved" and self.below_cost_approved:
            raise UserError(_("Below-cost selling is already approved for this Sales Order."))

        self.sudo().write({
            "below_cost_approval_state": "approved",
            "below_cost_reject_reason": False,
            "below_cost_approved": True,
            "below_cost_approval_snapshot": self._get_below_cost_snapshot(),
            "below_cost_approved_by": user.id,
            "below_cost_approved_on": fields.Datetime.now(),
        })

        self._below_cost_close_manager_activity()

        requester = self.below_cost_requested_by
        if requester and requester.partner_id:
            self.message_notify(
                partner_ids=[requester.partner_id.id],
                subject=_("Below-cost approval approved"),
                body=_(
                    "Below-cost approval APPROVED.\n"
                    "Sales Order: %(so)s\n"
                    "Approved by: %(by)s"
                ) % {"so": self.name, "by": user.name},
                subtype_xmlid="mail.mt_comment",
            )

        self.message_post(
            body=_("Below-cost approval approved by %(user)s.") % {
                "user": user.name,
            },
            subtype_xmlid="mail.mt_note",
        )
        return True

    def action_reject_below_cost(self):
        self.ensure_one()

        user = self.env.user
        if not (self._user_is_sales_manager(user) or user.has_group("base.group_system")):
            raise UserError(_("Only Sales Managers or Admin can reject below-cost approval."))

        if not self.below_cost_warning:
            raise UserError(_("This Sales Order is not below cost. No approval is required."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Below-Cost Approval"),
            "res_model": "below.cost.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_id": self.id,
                "reason_type_filter": "below_cost_reject",
            },
        }

    # =========================================================
    # CONFIRM: CREDIT BLOCK + BELOW COST BLOCK
    # =========================================================
    def action_confirm(self):
        for order in self:
            company = order.company_id or self.env.company

            # ---- FLOW 1 + FLOW 2 guards ----
            if company.enforce_credit_block:
                if order.credit_setup_missing:
                    raise UserError(_(
                        "Customer credit setup is not approved.\n\n"
                        "Please complete Customer Credit Setup first before confirming this Sales Order."
                    ))

                if order.credit_exceeded and not (
                        order.credit_increase_state == "approved" and order.credit_increase_approved
                ):
                    raise UserError(_(
                        "Credit limit exceeded.\n\n"
                        "This Sales Order cannot be confirmed.\n\n"
                        "Please request a credit limit increase or ask for advance payment."
                    ))

            # ---- FLOW 3 guard ----
            if company.enforce_below_cost_approval and order.below_cost_warning:
                user = self.env.user
                is_manager_or_admin = self._user_is_sales_manager(user) or user.has_group("base.group_system")

                if not is_manager_or_admin:
                    raise UserError(_(
                        "You are selling below cost.\n\n"
                        "This Sales Order cannot be confirmed until a Sales Manager approves.\n\n"
                        "Please click: Request Below Cost Approval."
                    ))

                if order.below_cost_approval_state != "approved" or not order.below_cost_approved:
                    order.sudo().write({
                        "below_cost_approval_state": "approved",
                        "below_cost_approved": True,
                        "below_cost_reject_reason": False,
                        "below_cost_approval_snapshot": order._get_below_cost_snapshot(),
                        "below_cost_approved_by": user.id,
                        "below_cost_approved_on": fields.Datetime.now(),
                    })
                    order.message_post(
                        body=_(
                            "Below-cost selling approved automatically on Sales Order confirmation by %s.") % user.name,
                        subtype_xmlid="mail.mt_note",
                    )

        return super().action_confirm()
