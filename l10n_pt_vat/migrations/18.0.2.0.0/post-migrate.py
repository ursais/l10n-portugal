from collections import defaultdict

from odoo import SUPERUSER_ID, api
from odoo.tools import SQL


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        [table, column],
    )
    return bool(cr.fetchone())


def _load_pt_certification_taxes(env, company):
    Template = env["account.chart.template"].with_company(company)
    if not hasattr(Template, "_get_pt_certification_account_tax"):
        return
    Template._load_data(
        {
            "account.tax": Template._get_pt_certification_account_tax(),
            "account.tax.group": Template._get_pt_certification_account_tax_group(),
        }
    )


def _get_company_tax_by_xmlid_suffix(env, company, suffix):
    rows = env.execute_query(
        SQL(
            """
            SELECT tax.id
              FROM account_tax tax
              JOIN ir_model_data imd
                ON imd.model = 'account.tax'
               AND imd.res_id = tax.id
             WHERE tax.company_id = %s
               AND imd.name LIKE %s
             ORDER BY imd.module = 'l10n_pt' DESC,
                      imd.module = 'l10n_pt_certification' DESC,
                      imd.id
             LIMIT 1
            """,
            company.id,
            f"%_{suffix}",
        )
    )
    return rows[0][0] if rows else False


def _get_or_create_sale_exempt_tax_for_reason(env, company, reason_code, cache):
    key = (company.id, reason_code)
    if key in cache:
        return cache[key]

    Tax = env["account.tax"].with_company(company)
    existing = Tax.search(
        [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "sale"),
            ("amount", "=", 0),
            ("l10n_pt_tax_exemption_reason", "=", reason_code),
        ],
        limit=1,
    )
    if existing:
        cache[key] = existing.id
        return existing.id

    base_tax_id = _get_company_tax_by_xmlid_suffix(env, company, "iva_pt_sale_isenta")
    if not base_tax_id:
        cache[key] = False
        return False

    base_tax = Tax.browse(base_tax_id)
    new_tax = base_tax.copy(
        {
            "name": f"{base_tax.name} [{reason_code}]",
            "l10n_pt_tax_exemption_reason": reason_code,
        }
    )
    cache[key] = new_tax.id
    return new_tax.id


def _migrate_move_lines_for_reason(env, move_ids, tax_id):
    if not move_ids or not tax_id:
        return

    line_rows = env.execute_query(
        SQL(
            """
            SELECT aml.id
              FROM account_move_line aml
              LEFT JOIN account_move_line_account_tax_rel rel
                ON rel.account_move_line_id = aml.id
             WHERE aml.move_id = ANY(%s)
               AND aml.display_type = 'product'
               AND rel.account_tax_id IS NULL
            """,
            move_ids,
        )
    )
    line_ids = [line_id for (line_id,) in line_rows]
    if not line_ids:
        return

    env.cr.execute(
        """
        INSERT INTO account_move_line_account_tax_rel (
            account_move_line_id, account_tax_id
        )
             SELECT UNNEST(%s), %s
        ON CONFLICT DO NOTHING
        """,
        [line_ids, tax_id],
    )


def _replace_zero_tax_without_reason(env, move_ids, tax_id):
    if not move_ids or not tax_id:
        return

    rows = env.execute_query(
        SQL(
            """
            WITH line_tax AS (
                SELECT
                    aml.id AS line_id,
                    ARRAY_AGG(rel.account_tax_id) AS tax_ids,
                    COUNT(*) AS tax_count,
                    MAX(tax.amount) AS max_amount,
                    MAX(tax.l10n_pt_tax_exemption_reason) AS max_reason
                FROM account_move_line aml
                JOIN account_move_line_account_tax_rel rel
                  ON rel.account_move_line_id = aml.id
                JOIN account_tax tax
                  ON tax.id = rel.account_tax_id
                WHERE aml.move_id = ANY(%s)
                  AND aml.display_type = 'product'
                GROUP BY aml.id
            )
            SELECT line_id, tax_ids[1]
              FROM line_tax
             WHERE tax_count = 1
               AND max_amount = 0
               AND max_reason IS NULL
            """,
            move_ids,
        )
    )

    if not rows:
        return

    line_ids = [line_id for line_id, _old_tax_id in rows]
    old_tax_ids = [old_tax_id for _line_id, old_tax_id in rows]

    env.cr.execute(
        """
        DELETE FROM account_move_line_account_tax_rel
         WHERE account_move_line_id = ANY(%s)
           AND account_tax_id = ANY(%s)
        """,
        [line_ids, old_tax_ids],
    )

    env.cr.execute(
        """
        INSERT INTO account_move_line_account_tax_rel (
            account_move_line_id, account_tax_id
        )
        SELECT UNNEST(%s), %s
        ON CONFLICT DO NOTHING
        """,
        [line_ids, tax_id],
    )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    if not _column_exists(cr, "account_move", "l10npt_vat_exempt_reason"):
        return
    if not _column_exists(cr, "account_tax", "l10n_pt_tax_exemption_reason"):
        return

    cr.execute(
        """
        SELECT r.id, r.code
          FROM account_l10n_pt_vat_exempt_reason r
        """
    )
    reason_by_id = dict(cr.fetchall())

    move_rows = env.execute_query(
        SQL(
            """
            SELECT m.id, m.company_id, m.l10npt_vat_exempt_reason
              FROM account_move m
              JOIN res_company c ON c.id = m.company_id
              LEFT JOIN res_country rc ON rc.id = COALESCE(
                  c.account_fiscal_country_id, c.country_id
              )
             WHERE m.l10npt_vat_exempt_reason IS NOT NULL
               AND rc.code = 'PT'
               AND m.move_type IN (
                   'out_invoice', 'out_refund', 'out_receipt', 'debit_note'
               )
            """
        )
    )

    if not move_rows:
        return

    moves_by_company_reason = defaultdict(list)
    for move_id, company_id, reason_id in move_rows:
        moves_by_company_reason[(company_id, reason_id)].append(move_id)

    tax_cache = {}
    for (company_id, reason_id), move_ids in moves_by_company_reason.items():
        reason_code = reason_by_id.get(reason_id)
        if not reason_code:
            continue

        company = env["res.company"].browse(company_id)
        _load_pt_certification_taxes(env, company)

        tax_id = _get_or_create_sale_exempt_tax_for_reason(
            env, company, reason_code, tax_cache
        )
        if not tax_id:
            continue

        _replace_zero_tax_without_reason(env, move_ids, tax_id)
        _migrate_move_lines_for_reason(env, move_ids, tax_id)
