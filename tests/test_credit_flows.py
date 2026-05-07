# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCreditFlows(TransactionCase):

    def setUp(self):
        super().setUp()

        self.company = self.env.company

        self.partner = self.env["res.partner"].create({
            "name": "Test Customer",
            "company_id": self.company.id,
        })

        self.partner.write({
            "credit_setup_done": False,
            "credit_request_state": "none",
            "credit_limit": 0.0,
        })

        self.sale_order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "company_id": self.company.id,
        })

    def test_flow1_credit_setup_missing_blocks_confirm(self):
        with self.assertRaises(UserError):
            self.sale_order.action_confirm()

    def test_company_setting_can_disable_credit_block(self):
        self.company.enforce_credit_block = False
        self.sale_order.action_confirm()

    def test_company_setting_can_disable_below_cost_block_flag(self):
        self.company.enforce_below_cost_approval = False
        self.assertFalse(self.company.enforce_below_cost_approval)