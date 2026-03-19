# Copyright 2025 Databay Solutions
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
    "name": "AEAT modelo 200",
    "version": "19.0.1.1.0",
    "development_status": "Alpha",
    "category": "Localization/Accounting",
    "author": "Databay Solutions, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-spain",
    "license": "AGPL-3",
    "depends": ["l10n_es_aeat"],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_es_aeat_mod200_security.xml",
        "data/l10n.es.aeat.mod200.map.line.csv",
        "data/aeat_export_mod200_sub01_data.xml",
        "data/aeat_export_mod200_sub03_data.xml",
        "data/aeat_export_mod200_sub07_data.xml",
        "data/aeat_export_mod200_sub12_data.xml",
        "data/aeat_export_mod200_data.xml",
        "views/mod200_view.xml",
    ],
    "installable": True,
}
