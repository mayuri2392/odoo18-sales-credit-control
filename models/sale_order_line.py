# -*- coding: utf-8 -*-

from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _sync_parent_below_cost_after_line_change(self):
        orders = self.mapped("order_id").filtered(lambda o: o and o.state in ("draft", "sent"))
        for order in orders:
            order._sync_below_cost_state_after_change()
            order._compute_below_cost_warning()

    def write(self, vals):
        res = super().write(vals)
        tracked = {
            "product_id",
            "price_unit",
            "discount",
            "product_uom_qty",
            "product_uom",
            "sequence",
        }
        if tracked.intersection(vals.keys()):
            self._sync_parent_below_cost_after_line_change()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_parent_below_cost_after_line_change()
        return lines

    def unlink(self):
        orders = self.mapped("order_id").filtered(lambda o: o and o.state in ("draft", "sent"))
        res = super().unlink()
        for order in orders:
            order._sync_below_cost_state_after_change()
            order._compute_below_cost_warning()
        return res