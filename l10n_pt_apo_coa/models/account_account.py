# Copyright 2025 APO - Associação Portuguesa Odoo
# License LGPL (GNU Lesser General Public License)
# Autors:
#   Tiago Filipe Rodrigues Santos (tiago.santos@arxi.pt)
#

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Account(models.Model):
    _inherit = "account.account"

    taxonomy_ids = fields.Many2many(
        "l10n_pt.taxonomy",
        "account_taxonomy_rel",
        "account_id",
        "taxonomy_id",
        string="Taxonomies",
    )

    possible_taxonomy_ids = fields.Many2many(
        "l10n_pt.taxonomy", compute="_compute_possible_taxonomy_ids", store=True
    )

    @api.depends("code")
    def _compute_possible_taxonomy_ids(self):
        for rec in self.filtered(
            lambda a: a.company_ids in self.env.company
            and self.env.company.country_code == "PT"
        ):
            if rec.code:
                rec.possible_taxonomy_ids = self.env["l10n_pt.taxonomy"].search(
                    [
                        ("from_account_code", "<=", rec.code),
                        ("to_account_code", ">=", rec.code),
                    ]
                )
            else:
                rec.possible_taxonomy_ids = False

    @api.constrains("group_id", "code", "deprecated")
    def _check_code_prefix_start(self):
        for account in self.filtered(lambda account: not account.deprecated):
            prefix = account.group_id and account.group_id.code_prefix_start
            if account.code == prefix:
                raise ValidationError(
                    _(
                        "The account code (%s) cannot be the same "
                        "as the group code prefix start.",
                        account.code,
                    )
                )
