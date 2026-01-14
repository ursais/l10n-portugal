# Copyright (C) 2021 Open SOurce Integrators (<http://www.opensourceintegrators.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_pt_fiscal_zone = fields.Selection(
        [
            ("PT-ALL", "All Regions"),
            ("PT", "Mainland Portugal"),
            ("PT-MA", "Madeira"),
            ("PT-AC", "Azores"),
        ],
        string="Fiscal Zone",
        compute="_compute_l10n_pt_fiscal_zone",
        inverse="_inverse_l10n_pt_fiscal_zone",
        store=True,
    )

    def _compute_l10n_pt_fiscal_zone(self):
        for tax in self:
            tax.l10n_pt_fiscal_zone = tax.tax_group_id.l10n_pt_tax_region

    def _inverse_l10n_pt_fiscal_zone(self):
        for tax in self.filtered("tax_group_id"):
            tax.tax_group_id.l10n_pt_tax_region = tax.l10n_pt_fiscal_zone
