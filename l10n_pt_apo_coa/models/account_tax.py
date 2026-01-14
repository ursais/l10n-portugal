from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

L10N_PT_TAX_REGIONS_SELECTION = [
    ("PT", "Mainland Portugal"),
    ("PT-MA", "Madeira"),
    ("PT-AC", "Azores"),
]

L10N_PT_TAX_CATEGORIES_SELECTION = [
    ("NOR", "Normal"),
    ("INT", "Intermediate"),
    ("RED", "Reduced"),
    ("ISE", "Exempt"),
]


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_pt_fiscal_zone = fields.Selection(
        string="Fiscal Zone", related="tax_group_id.l10n_pt_fiscal_zone", store=True
    )

    l10n_pt_tax_code = fields.Selection(
        string="Tax code",
        related="tax_group_id.l10n_pt_tax_code",
        store=True,
    )

    l10n_pt_tax_type = fields.Selection(
        selection=[
            ("IVA", "Value Added Tax"),
            ("IS", "Stamp Duty"),
            ("NS", "Not Subject"),
            ("IRS", "Personal income tax"),
            ("IRC", "Corporate income tax"),
        ],
        string="Tax type",
    )

    l10n_pt_stamp_duty_code = fields.Char(string="Stamp Duty Code")

    l10n_pt_vat_exempt_reason = fields.Many2one(
        "l10n_pt.vat.exempt.reason", string="VAT Exemption Reason"
    )

    # @api.constrains("amount", "type_tax_use")
    # def _check_exempt_tax(self):
    #     for tax in self:
    #         if (
    #             tax.amount == 0.0
    #             and tax.type_tax_use != "purchase"
    #             and tax.country_code == "PT"
    #             and not tax.l10n_pt_tax_exemption_reason
    #         ):
    #             raise ValidationError(
    #                 _(
    #                     "Exempt taxes must have a VAT Exemption Reason defined. "
    #                     "Please set the reason in the tax configuration."
    #                 )
    #             )

    @api.constrains("l10n_pt_tax_exemption_reason")
    def _validate_l10n_pt_tax_exemption_reason(self):
        """
        According to Portugal's tax authority: "The proram should ensure the
        enforceability for the user
        to present a reason for not assessing tax, if it is the case."
        """
        for tax in self:
            if tax.filtered(
                lambda t: t.type_tax_use != "purchase"
                and t.l10n_pt_tax_type == "IVA"
                and t.country_code == "PT"
                and t.amount == 0
                and not t.l10n_pt_vat_exempt_reason
            ):
                raise ValidationError(
                    _("Exempt taxes require an exemption reason: %s", tax.name)
                )


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_pt_fiscal_zone = fields.Selection(
        string="Fiscal Zone",
        selection=L10N_PT_TAX_REGIONS_SELECTION,
    )

    l10n_pt_tax_code = fields.Selection(
        string="Tax code",
        selection=[
            ("NOR", "Normal"),
            ("INT", "Intermediate"),
            ("RED", "Reduced"),
            ("ISE", "Exempt"),
            ("OUT", "Other"),
            ("NS", "Not subject"),
            ("NA", "Not applicable"),
        ],
    )
