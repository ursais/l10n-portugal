# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _prepare_invoicexpress_line_vals(self):
        self.ensure_one()
        product = self.product_id
        tax = self.move_id.l10npt_invoicexpress_tax_id or product.taxes_id[:1]
        name = product.default_code or product.display_name or "MISC"

        # description_picking often includes the default code; avoid showing it twice
        description = self.description_picking
        prefix = f"[{product.default_code}] " if product.default_code else ""
        if product.default_code and description.startswith(prefix):
            description = description[len(prefix) :]
        else:
            description = ": ".join([product.name, description])
        include_uom = self.picking_id.picking_type_id.invoicexpress_include_uom
        uom_name = f", {self.product_uom_id.name}" if include_uom else ""
        package = f"({self.result_package_id.name})" if self.result_package_id else ""
        return {
            "name": name,
            "description": " ".join([description, uom_name, package]),
            "unit_price": 0.0,
            "quantity": self.quantity_product_uom,
            "discount": self.move_id.sale_line_id.discount or 0.0,
            "tax": {"name": tax.name} if tax else {},
        }
