# Copyright 2025 OCA - Odoo Community Association
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
{
    "name": "AEAT modelo 202",
    "summary": "Pago fraccionado a cuenta del Impuesto sobre Sociedades",
    "version": "19.0.1.0.0",
    "development_status": "Beta",
    "category": "Localization/Accounting",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-spain",
    "license": "AGPL-3",
    "depends": ["l10n_es_aeat"],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_es_aeat_mod202_security.xml",
        "data/aeat_export_mod202_sub01_data.xml",
        "data/aeat_export_mod202_sub02_data.xml",
        "data/aeat_export_mod202_data.xml",
        "views/mod202_view.xml",
    ],
    "installable": True,
}
