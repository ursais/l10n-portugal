# Copyright 2025 APO - Associação Portuguesa Odoo
# License LGPL (GNU Lesser General Public License)
# Autors:
#   Tiago Filipe Rodrigues Santos (tiago.santos@arxi.pt)
#   Dylan da Silva (dylan.silva@arxi.pt)
#

from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(template="pt", model="template_data")
    def _get_pt_template_data(self):
        result = super()._get_pt_template_data()
        result.update(
            {
                "code_digits": "3",
                "property_account_receivable_id": "chart_21111",
                "property_account_payable_id": "chart_22111",
                "property_account_income_categ_id": "chart_7111",
                "property_account_expense_categ_id": "chart_3111",
            }
        )
        return result

    @template(template="pt", model="account.account")
    def _get_pt_account_account(self):
        return self._parse_csv("pt", "account.account", module="l10n_pt_apo_coa")

    @template(template="pt", model="account.group")
    def _get_pt_account_group(self):
        return self._parse_csv("pt", "account.group", module="l10n_pt_apo_coa")

    @template(model="account.journal")
    def _get_account_journal(self, template_code):
        vals = super()._get_account_journal(template_code)
        if template_code == "pt":
            if "cash" in vals:
                vals["cash"]["default_account_id"] = "chart_111"
            if "bank" in vals:
                vals["bank"]["default_account_id"] = "chart_121"
        return vals

    @template(template="pt", model="account.tax.group")
    def _get_pt_account_tax_group(self):
        return self._parse_csv("pt", "account.tax.group", module="l10n_pt_apo_coa")

    @template(template="pt", model="account.fiscal.position")
    def _get_pt_account_fiscal_position(self):
        return self._parse_csv(
            "pt", "account.fiscal.position", module="l10n_pt_apo_coa"
        )

    @template(template="pt", model="account.tax")
    def _get_pt_account_tax(self):
        tax_data = self._parse_csv("pt", "account.tax", module="l10n_pt_apo_coa")
        self._deref_account_tags("pt", tax_data)
        return tax_data

    @template("pt", "res.company")
    def _get_pt_res_company(self):
        """
        Override to set the tax calculation rounding method to 'round_globally'.
        """
        result = super()._get_pt_res_company()
        result[self.env.company.id].update(
            {
                "tax_calculation_rounding_method": "round_globally",
                "bank_account_code_prefix": "121",
                "cash_account_code_prefix": "111",
            }
        )
        return result

    def _get_accounts_data_values(
        self, company, template_data, bank_prefix="", code_digits=0
    ):
        accounts_data = super()._get_accounts_data_values(
            company, template_data, bank_prefix=bank_prefix, code_digits=code_digits
        )
        if company.account_fiscal_country_id.code == "PT":
            accounts_data["account_journal_suspense_account_id"]["taxonomy_ids"] = [
                (
                    6,
                    0,
                    [
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_2_s").id,
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_2_m").id,
                    ],
                )
            ]
            accounts_data["transfer_account_id"]["taxonomy_ids"] = [
                (
                    6,
                    0,
                    [
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_4_s").id,
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_9_m").id,
                    ],
                )
            ]
        return accounts_data

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        res = super()._setup_utility_bank_accounts(
            template_code, company, template_data
        )
        if template_code == "pt":
            payment_debit_account = self.env.ref(
                f"account.{company.id}_account_journal_payment_debit_account_id"
            )
            payment_credit_account = self.env.ref(
                f"account.{company.id}_account_journal_payment_credit_account_id"
            )
            payment_debit_account.taxonomy_ids = [
                (
                    6,
                    0,
                    [
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_2_s").id,
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_2_m").id,
                    ],
                )
            ]
            payment_credit_account.taxonomy_ids = [
                (
                    6,
                    0,
                    [
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_2_s").id,
                        self.env.ref("l10n_pt_apo_coa.pt_taxo_2_m").id,
                    ],
                )
            ]

            # FIXME: error on create a PT company!
            # Delete 2 digits accounts from original pt template
            # external_ids = ["chart_11", "chart_12", "chart_13"]
            # for ext_id in external_ids:
            #     self.env.ref(
            #         f"account.{company.id}_{ext_id}", raise_if_not_found=False
            #     ).write({"deprecated:": True})
        return res
