# odoo18-sales-credit-control

An Odoo 18 module that enforces credit limits and below-cost pricing governance on Sales Orders — with role-based approval workflows, automated notifications, and a full audit trail.

Built on Odoo 18 Community. Tested with the Sales, Accounting, and Inventory apps.

---

## What It Does

### Credit Control
- Assigns customers to credit tiers (Gold, Silver, Bronze, New Customer), each with a default credit limit
- New customers go through an initial credit setup — the salesperson sets the tier and requests a limit, which Accounting approves before any Sales Order can be confirmed
- Blocks Sales Order confirmation when a customer's total exposure exceeds their approved limit
- Gives the salesperson a one-click **Request Credit Increase** flow — the request goes to the Accounting team for approval
- Notifies the salesperson when the request is approved or rejected
- Tracks the full approval history on the customer record and the Sales Order

### Below-Cost Governance
- Detects when any Sales Order line is priced below the product's current cost (post landed costs)
- Blocks confirmation and prompts the salesperson to request approval from a Pricing Manager
- The Pricing Manager sees **Approve Below Cost** / **Reject Below Cost** buttons directly on the SO
- Rejection requires a reason, keeping the audit trail clean

---

## Screenshots

### Credit Setup Tab — New Customer Onboarding
![Credit setup tab](static/src/img/screenshots/00_credit_setup_tab.png)

### Initial Credit Request — Accounting Team Review
![Credit approval requested](static/src/img/screenshots/00b_credit_approval_requested.png)

### Credit Limit Exceeded — SO Blocked
![Credit blocked](static/src/img/screenshots/01_credit_blocked.png)

### Request Credit Increase Wizard
![Credit request wizard](static/src/img/screenshots/02_credit_request_wizard.png)

### Credit Approval Pending
![Credit pending](static/src/img/screenshots/03_credit_pending.png)

### Accountant Inbox — Approval Request
![Accountant inbox](static/src/img/screenshots/04_accountant_inbox.png)

### Sales User Notified — Credit Approved
![Sales user notified](static/src/img/screenshots/05_sales_user_notified.png)

### Below-Cost Warning Banner
![Below cost warning](static/src/img/screenshots/06_below_cost_warning.png)

### Below-Cost Blocked — Invalid Operation
![Below cost blocked](static/src/img/screenshots/07_below_cost_blocked.png)

### Below-Cost Approved — Sales User Notified
![Below cost approved](static/src/img/screenshots/08_below_cost_approved.png)

---

## Security Groups

| Group | Technical Name | Who Gets It |
|---|---|---|
| Credit Setup Requestor | `group_credit_setup_requestor` | Salesperson — can request credit limits and increases |
| Credit Config Manager | `group_credit_config_manager` | Accounting team — approves/rejects credit requests |
| Pricing Config Manager | `group_pricing_config_manager` | Pricing/Sales Manager — approves/rejects below-cost orders |

---

## Credit Tiers

Tiers are configured under **Invoicing → Configuration → Credit Control → Credit Tiers**.

| Tier | Suggested Default Limit |
|---|---|
| Gold | 500,000 |
| Silver | 200,000 |
| Bronze | 75,000 |
| New Customer | 15,000 |

Each customer is assigned a tier on the **Credit Setup** tab. The salesperson requests the initial credit limit, which the Accounting team approves on the **Credit Approval** tab.

---

## Installation

**Prerequisites:** The **Sales** app must be installed before this module. Accounting and Inventory are also required (listed in depends).

1. Clone the repo into your addons folder:
```bash
   git clone https://github.com/mayuri2392/odoo18-sales-credit-control.git \
     ~/Projects/odoo18/custom_addons/sales_credit_control
```
2. Restart Odoo
3. Go to **Settings → Apps**, search for `Sales Credit Control`, and install it
4. Configure credit tiers under **Invoicing → Configuration → Credit Control → Credit Tiers**
5. Add credit reasons under **Invoicing → Configuration → Credit Control → Credit Reasons**
6. Add below-cost rejection reasons under **Sales → Configuration → Below-Cost Reasons**
7. Enable enforcement settings under **Sales → Configuration → Settings → Credit Control**

> Note: Credit Tiers and Credit Reasons appear under the **Invoicing** menu, not Sales. This is intentional — credit governance sits with the Accounting team.

---

## Workflow Overview

### Initial Customer Credit Setup
1. Salesperson opens a new customer → **Credit Setup** tab → selects Credit Tier → clicks **Request Credit Limit**
2. Accounting team receives inbox notification → opens **Credit Approval** tab → clicks **Approve**
3. Salesperson is notified. Customer is now ready for Sales Orders.

### Credit Blocking Flow
1. Salesperson creates a Sales Order that exceeds the customer's approved limit
2. SO shows a warning banner with the exact overage amount
3. Clicking **Confirm** raises an error: "Credit limit exceeded. This Sales Order cannot be confirmed."
4. Salesperson clicks **Request Credit Increase** → fills in the requested limit and reason → submits
5. Accounting team receives inbox notification → approves or rejects
6. Salesperson is notified. If approved, the SO can now be confirmed.

### Below-Cost Flow
1. Salesperson prices a product below its current cost (post landed costs)
2. SO shows a warning banner: "This order is priced below cost. Cost: X SAR | Sales Price: Y SAR"
3. Clicking **Confirm** raises an error: "You are selling below cost."
4. Salesperson clicks **Request Below Cost Approval** → submits
5. Pricing Manager sees **Approve Below Cost** / **Reject Below Cost** on the SO
6. Salesperson is notified. If approved, the SO can now be confirmed.

---

## Configuration Settings

Under **Sales → Configuration → Settings → Credit Control**:

| Setting | Effect |
|---|---|
| Enforce Credit Blocking | Blocks SO confirmation when credit limit is exceeded |
| Enforce Below Cost Approval | Blocks SO confirmation when any line is priced below cost |

Both settings are off by default. Enable them per company.

---

## Technical Notes

- `'application': False` — this is a functional module, not a standalone app. The Sales app must be installed first.
- Admin users bypass group checks by design (Odoo standard behaviour). Use role-specific users to demo the approval flows.
- The `reason_type_credit` proxy field on `approval.reason` restricts the Credit Reasons form to credit-only options, keeping the UI clean for Accounting users. Below-Cost Reasons are managed separately under Sales → Configuration.
- Compatible with Odoo 18 Community. No Docker required for local development.

---

## Author

**Mayuri Patil**
Odoo Functional + Technical Consultant
[LinkedIn](https://linkedin.com/in/mayuri-patil-2392) · [GitHub](https://github.com/mayuri2392)