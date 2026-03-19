# Copyright 2025 Databay Solutions
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class L10nEsAeatMod200MapLine(models.Model):
    _name = "l10n.es.aeat.mod200.map.line"
    _description = "Mapping line between PGC accounts and Model 200 fields"

    field_name = fields.Char(
        required=True,
        help="Name of the target field in l10n.es.aeat.mod200.report",
    )
    account_prefix = fields.Char(
        required=True,
        help="PGC account prefix to match (e.g. '20' matches 200xxxxx, 201xxxxx...)",
    )
    sign = fields.Integer(
        default=1,
        help="Multiplier: 1 or -1. Use -1 for contra-accounts like depreciation.",
    )
    balance_type = fields.Selection(
        selection=[
            ("debit-credit", "Debit - Credit (asset / expense accounts)"),
            ("credit-debit", "Credit - Debit (liability / equity / income accounts)"),
        ],
        required=True,
        default="debit-credit",
        help="How to compute the balance from account.move.line.",
    )
    cumulative = fields.Boolean(
        default=False,
        help="If True, compute cumulative balance up to date_end "
        "(for balance sheet accounts 1-5). "
        "If False, only period movements (for P&L accounts 6-7).",
    )
