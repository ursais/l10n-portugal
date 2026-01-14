# Copyright 2025 APO - Associação Portuguesa Odoo
# License LGPL (GNU Lesser General Public License)
# Authors:
#   João Vitor Batista Pinheiro (joao.vitor.pinheiro@qubiq.info)
#   Tiago Filipe Rodrigues Santos (tiago.santos@arxi.pt)
#   Dylan da Silva (dylan.silva@arxi.pt)
#

{
    "name": "APO - Portugal Chart of Accounts",
    "summary": "Portugal Chart of Accounts Localization",
    "version": "18.0.1.0.0",
    "countries": ["pt"],  # Required to import translations in data files ex: name@pt
    "license": "LGPL-3",
    "author": "Associação Portuguesa de Odoo (APO), Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-portugal",
    "category": "Accounting/Localizations",
    "depends": ["l10n_pt_certification"],
    "data": [
        "data/template/account.account-pt.csv",
        "data/template/account.group-pt.csv",
        "data/template/account.tax-pt.csv",
        "data/template/account.tax.group-pt.csv",
        "data/template/account.fiscal.position-pt.csv",
        "views/l10n_pt_account_account_views.xml",
        "views/l10n_pt_account_tax_views.xml",
        "views/l10n_pt_account_tax_group_views.xml",
    ],
    "installable": True,
}
