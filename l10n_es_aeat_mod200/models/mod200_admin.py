# Copyright 2025 Databay Solutions
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class L10nEsAeatMod200Admin(models.Model):
    _name = "l10n.es.aeat.mod200.admin"
    _description = "Modelo 200 - Administrador / Representante"

    report_id = fields.Many2one(
        comodel_name="l10n.es.aeat.mod200.report",
        string="Declaración",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vat = fields.Char(
        string="NIF/NIE",
        size=9,
        required=True,
    )
    name = fields.Char(
        string="Apellidos y nombre / Razón social",
        required=True,
    )
    person_type = fields.Selection(
        selection=[
            ("F", "Persona física"),
            ("J", "Persona jurídica"),
        ],
        string="Tipo de persona",
        required=True,
        default="F",
    )
    position_type = fields.Selection(
        selection=[
            ("01", "Presidente"),
            ("02", "Vicepresidente"),
            ("03", "Consejero"),
            ("04", "Secretario"),
            ("05", "Administrador"),
            ("06", "Administrador solidario"),
            ("07", "Administrador mancomunado"),
            ("08", "Administrador único"),
            ("09", "Director general"),
            ("10", "Apoderado"),
            ("11", "Liquidador"),
            ("12", "Representante"),
            ("99", "Otro"),
        ],
        string="Cargo",
        required=True,
        default="05",
    )
    appointment_date = fields.Date(
        string="Fecha de nombramiento",
    )
    is_representative = fields.Boolean(
        string="Es representante legal",
    )
