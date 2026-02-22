# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


def get_account_id(provider_sudo):
    return provider_sudo.easypay_account_id


def get_api_key(provider_sudo):
    return provider_sudo.easypay_api_key


def include_customer_data(tx_sudo):
    return {
        "name": tx_sudo.partner_name or "",
        "email": tx_sudo.partner_email or "",
        "phone": tx_sudo.partner_phone or "",
        "key": str(tx_sudo.partner_id.id),
    }


def include_shipping_address(tx_sudo):
    if hasattr(tx_sudo, "sale_order_ids") and tx_sudo.sale_order_ids:
        return format_shipping_address(tx_sudo.sale_order_ids[0].partner_shipping_id)
    elif hasattr(tx_sudo, "invoice_ids") and tx_sudo.invoice_ids:
        return format_shipping_address(tx_sudo.invoice_ids[0].partner_shipping_id)
    return {}


def format_shipping_address(shipping_partner):
    return {
        "name": shipping_partner.name or shipping_partner.parent_id.name,
        "address": {
            "street": shipping_partner.street or "",
            "city": shipping_partner.city or "",
            "postal_code": shipping_partner.zip or "",
            "country": shipping_partner.country_id.code or "",
        },
    }
