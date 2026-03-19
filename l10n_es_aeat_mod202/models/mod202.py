# Copyright 2025 OCA - Odoo Community Association
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
import math
from calendar import monthrange

from odoo import api, exceptions, fields, models
from odoo.tools import float_compare, float_is_zero

# Tax rate key -> (fraction numerator, fraction denominator) for Art. 40.3
# porcentaje = tipo * 19/20, redondeado por exceso
# Ref: Art. 40.3 LIS + DA 14ª LIS
TIPO_GRAVAMEN_MAP = {
    "00": 0,
    "01": 1,
    "04": 4,
    "10": 10,
    "15": 15,
    "21": 21,
    "22": 22,
    "23": 23,
    "24": 24,
    "25": 25,
    "30": 30,
}

# Minimum payment percentage by CN bracket (DA 14ª LIS)
# For CN >= 10M EUR: 23% of accounting result (general)
# For CN >= 10M EUR with Art. 29.6 first paragraph: 25%
MINIMO_PCT_GENERAL = 23
MINIMO_PCT_ENTIDADES_CREDITO = 25


def _round_up_pct(tipo_gravamen):
    """Calculate payment fraction percentage: tipo * 19/20, rounded up.
    Ref: Art. 40.3 last paragraph LIS.
    """
    return math.ceil(tipo_gravamen * 19 / 20 * 100) / 100


class L10nEsAeatMod202Report(models.Model):
    _description = "AEAT 202 report"
    _inherit = "l10n.es.aeat.report"
    _name = "l10n.es.aeat.mod202.report"
    _aeat_number = "202"
    _period_quarterly = False
    _period_monthly = False
    _period_yearly = False

    # Periods for model 202: 1P (April), 2P (October), 3P (December)
    _PERIOD_DATES = {
        "1P": (1, 3),
        "2P": (1, 9),
        "3P": (1, 11),
        "0A": (1, 12),
    }

    def get_period_type_selection(self):
        return [
            ("1P", "1P - Primer pago (abril)"),
            ("2P", "2P - Segundo pago (octubre)"),
            ("3P", "3P - Tercer pago (diciembre)"),
            ("0A", "0A - Anual"),
        ]

    @api.depends("year", "period_type")
    def _compute_dates(self):
        for report in self:
            if not report.year or not report.period_type:
                continue
            dates = self._PERIOD_DATES.get(report.period_type)
            if dates:
                start_month, end_month = dates
                report.date_start = fields.Date.to_date(
                    f"{report.year}-{start_month}-01"
                )
                report.date_end = fields.Date.to_date(
                    f"{report.year}-{end_month}-"
                    f"{monthrange(report.year, end_month)[1]}"
                )
            else:
                super(L10nEsAeatMod202Report, report)._compute_dates()

    # --- Identification & Additional Data ---

    date_start_period = fields.Date(
        string="Fecha inicio período impositivo",
    )
    cnae_actividad = fields.Char(
        string="CNAE actividad principal",
        size=4,
    )
    aplica_ley_49_2002 = fields.Boolean(
        string="Ley 49/2002 (entidades sin fines lucrativos)",
    )
    aplica_ley_11_2009 = fields.Boolean(
        string="Ley 11/2009 (SOCIMI)",
    )
    aplica_capital_riesgo = fields.Boolean(
        string="Capital-riesgo (régimen fiscal especial)",
    )
    aplica_regimen_naviero = fields.Boolean(
        string="Régimen naviero (tonelaje)",
    )
    aplica_erd = fields.Boolean(
        string="Requisitos ERD (reducida dimensión)",
    )
    cn_superior_6m = fields.Boolean(
        string="Importe neto CN ≥ 6M EUR (12 meses anteriores)",
    )
    cooperativa_protegida = fields.Boolean(
        string="Cooperativa fiscalmente protegida",
    )
    aplica_da_14 = fields.Boolean(
        string="Condiciones DA 14ª LIS",
        help="Marque si concurre alguna de las circunstancias del "
        "apartado 1 de la DA 14ª de la LIS.",
    )
    cn_superior_10m = fields.Boolean(
        string="Importe neto CN ≥ 10M EUR",
    )
    otras_entidades_multitipo = fields.Boolean(
        string="Otras entidades con posibilidad de aplicar más de un tipo",
    )
    contribuyente_navarra = fields.Boolean(
        string="Contribuyente sometido a normativa foral de Navarra",
    )
    tipo_gravamen = fields.Char(
        string="Tipo de gravamen",
        size=15,
        default="25",
        help="Código de tipo de gravamen según la tabla del modelo 202. "
        "Ej: 25 (general), 23 (microempresa), 15 (nueva creación), etc.",
    )
    cn_tramo = fields.Selection(
        selection=[
            ("0", "No consta"),
            ("1", "≥ 10M y < 20M EUR"),
            ("2", "≥ 20M y < 60M EUR"),
            ("3", "≥ 60M EUR"),
        ],
        string="Tramo cifra de negocios",
        default="0",
    )

    # --- Modality selection ---

    liquidacion_modalidad = fields.Selection(
        selection=[
            ("A", "Modalidad A - Art. 40.2 LIS (18% cuota íntegra)"),
            ("B", "Modalidad B - Art. 40.3 LIS (base imponible)"),
        ],
        string="Modalidad de liquidación",
        required=True,
        default="A",
    )

    # --- Modality A: Art. 40.2 LIS ---

    casilla_01_mode = fields.Selection(
        selection=[
            ("manual", "Introducir manualmente"),
            ("auto", "Calcular desde último Modelo 200"),
        ],
        string="Origen casilla [01]",
        default="manual",
    )
    casilla_01 = fields.Monetary(
        string="[01] Base del pago fraccionado",
        help="Modalidad A: 18% de la cuota íntegra del último Impuesto sobre "
        "Sociedades presentado, minorada en deducciones, bonificaciones "
        "y retenciones/ingresos a cuenta.",
    )
    casilla_02 = fields.Monetary(
        string="[02] Resultado declaración anterior",
        help="A cumplimentar exclusivamente en caso de declaración complementaria.",
    )
    casilla_03 = fields.Monetary(
        string="[03] A ingresar",
        compute="_compute_casilla_03",
        store=True,
    )

    # --- Modality B: Art. 40.3 LIS ---

    casilla_04 = fields.Monetary(
        string="[04] Resultado contable después de IS e IC",
        help="Resultado contable del período (3, 9 u 11 primeros meses) "
        "determinado según el Código de Comercio.",
    )
    casilla_05 = fields.Monetary(
        string="[05] Correcciones IS/IC - Aumentos",
        help="Correcciones al resultado contable por Impuesto sobre Sociedades "
        "e Impuesto Complementario - Aumentos.",
    )
    casilla_06 = fields.Monetary(
        string="[06] Correcciones IS/IC - Disminuciones",
        help="Correcciones al resultado contable por Impuesto sobre Sociedades "
        "e Impuesto Complementario - Disminuciones.",
    )
    casilla_07 = fields.Monetary(
        string="[07] Correcciones IS/IC complementario",
        help="Correcciones al resultado contable por Impuesto Complementario.",
    )
    casilla_37 = fields.Monetary(
        string="[37] 30% gastos amortización - Disminuciones",
    )
    casilla_08 = fields.Monetary(
        string="[08] Resto correcciones - Aumentos",
        help="Resto de correcciones al resultado contable (excepto IS/IC "
        "y 30% gastos amortización) - Aumentos.",
    )
    casilla_09 = fields.Monetary(
        string="[09] Resto correcciones - Disminuciones",
        help="Resto de correcciones al resultado contable (excepto IS/IC "
        "y 30% gastos amortización) - Disminuciones.",
    )
    casilla_38 = fields.Monetary(
        string="[38] Total correcciones - Aumentos",
        compute="_compute_total_correcciones",
        store=True,
    )
    casilla_39 = fields.Monetary(
        string="[39] Total correcciones - Disminuciones",
        compute="_compute_total_correcciones",
        store=True,
    )
    casilla_13 = fields.Monetary(
        string="[13] Base imponible previa",
        compute="_compute_casilla_13",
        store=True,
    )
    casilla_40 = fields.Monetary(
        string="[40] Remanente reserva de capitalización",
        help="Remanente reserva de capitalización no aplicada en períodos "
        "anteriores que se aplica en este período.",
    )
    casilla_14 = fields.Monetary(
        string="[14] Compensación BINs",
        help="Compensación de bases imponibles negativas de ejercicios anteriores.",
    )
    casilla_15 = fields.Monetary(
        string="[15] Reserva de nivelación - Disminución",
        help="Reserva de nivelación art. 105 LIS (solo ERD) - Disminución.",
    )
    casilla_16 = fields.Monetary(
        string="[16] Reserva de nivelación - Adición",
        help="Reserva de nivelación art. 105 LIS (solo ERD) - Adición por "
        "integración obligatoria.",
    )

    # --- B1: Single percentage ---

    casilla_17_base = fields.Monetary(
        string="[B1] Base pago fraccionado",
        compute="_compute_b1",
        store=True,
        help="B1 - Caso general (porcentaje único): base del pago fraccionado.",
    )
    casilla_17_pct = fields.Float(
        string="[B1] Porcentaje",
        digits=(5, 2),
        help="B1 - Porcentaje aplicable (tipo * 19/20 redondeado por exceso).",
    )
    casilla_18 = fields.Monetary(
        string="[B1] Dotaciones art. 11.12 LIS",
    )
    casilla_19_comp = fields.Monetary(
        string="[B1] Compensación cuotas negativas cooperativas",
    )
    casilla_41 = fields.Monetary(
        string="[B1] Reserva nivelación convertida en minoración",
    )
    casilla_42 = fields.Monetary(
        string="[B1] Reserva nivelación convertida en adición",
    )
    casilla_20 = fields.Monetary(
        string="[20] Resultado previo",
        compute="_compute_casilla_20",
        store=True,
    )

    # --- B2: Multiple percentages (up to 4 tranches) ---

    b2_tramo1_base = fields.Monetary(string="[B2] Tramo 1 - Base")
    b2_tramo1_pct = fields.Float(
        string="[B2] Tramo 1 - Porcentaje", digits=(5, 2)
    )
    b2_tramo1_resultado = fields.Monetary(
        string="[B2] Tramo 1 - Resultado parcial",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo1_acumulado = fields.Monetary(
        string="[B2] Tramo 1 - Resultado acumulado",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo2_base = fields.Monetary(string="[B2] Tramo 2 - Base")
    b2_tramo2_pct = fields.Float(
        string="[B2] Tramo 2 - Porcentaje", digits=(5, 2)
    )
    b2_tramo2_resultado = fields.Monetary(
        string="[B2] Tramo 2 - Resultado parcial",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo2_acumulado = fields.Monetary(
        string="[B2] Tramo 2 - Resultado acumulado",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo3_base = fields.Monetary(string="[B2] Tramo 3 - Base")
    b2_tramo3_pct = fields.Float(
        string="[B2] Tramo 3 - Porcentaje", digits=(5, 2)
    )
    b2_tramo3_resultado = fields.Monetary(
        string="[B2] Tramo 3 - Resultado parcial",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo3_acumulado = fields.Monetary(
        string="[B2] Tramo 3 - Resultado acumulado",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo4_base = fields.Monetary(string="[B2] Tramo 4 - Base")
    b2_tramo4_pct = fields.Float(
        string="[B2] Tramo 4 - Porcentaje", digits=(5, 2)
    )
    b2_tramo4_resultado = fields.Monetary(
        string="[B2] Tramo 4 - Resultado parcial",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_tramo4_acumulado = fields.Monetary(
        string="[B2] Tramo 4 - Resultado acumulado",
        compute="_compute_b2_tramos",
        store=True,
    )
    b2_dotaciones = fields.Monetary(
        string="[B2] Dotaciones art. 11.12 LIS",
    )
    b2_compensacion = fields.Monetary(
        string="[B2] Compensación cuotas negativas cooperativas",
    )
    b2_nivelacion_min = fields.Monetary(
        string="[B2] Reserva nivelación - minoración",
    )
    b2_nivelacion_add = fields.Monetary(
        string="[B2] Reserva nivelación - adición",
    )
    b2_resultado_previo = fields.Monetary(
        string="[B2] Resultado previo",
        compute="_compute_b2_resultado_previo",
        store=True,
    )

    # --- Common B fields ---

    use_b2 = fields.Boolean(
        string="Casos específicos (más de un porcentaje)",
        help="Marque si la entidad aplica más de un tipo de gravamen.",
    )
    casilla_27 = fields.Monetary(
        string="[27] Bonificaciones",
        help="Bonificaciones correspondientes al período computado.",
    )
    casilla_28 = fields.Monetary(
        string="[28] Retenciones e ingresos a cuenta",
        help="Retenciones e ingresos a cuenta practicados sobre los ingresos "
        "del período.",
    )
    casilla_29_pct = fields.Float(
        string="[29] Volumen operaciones Territorio Común (%)",
        digits=(5, 2),
        default=100.00,
        help="Porcentaje del volumen de operaciones en Territorio Común.",
    )
    casilla_30 = fields.Monetary(
        string="[30] Pagos fraccionados períodos anteriores",
        help="Pagos fraccionados de períodos anteriores en Territorio Común.",
    )
    casilla_31 = fields.Monetary(
        string="[31] Resultado declaración anterior",
        help="Resultado de la declaración anterior (exclusivamente "
        "declaración complementaria).",
    )
    casilla_32 = fields.Monetary(
        string="[32] Resultado",
        compute="_compute_casilla_32",
        store=True,
    )
    casilla_33 = fields.Monetary(
        string="[33] Mínimo a ingresar",
        help="Mínimo a ingresar (solo para empresas con CN ≥ 10M EUR). "
        "DA 14ª LIS.",
    )
    casilla_34 = fields.Monetary(
        string="[34] Cantidad a ingresar",
        compute="_compute_casilla_34",
        store=True,
        help="Cantidad a ingresar: mayor de [32] y [33].",
    )

    # --- Additional information ---

    comunicar_datos_adicionales = fields.Boolean(
        string="Comunicar datos adicionales",
        help="Marque si comunica datos adicionales a la declaración "
        "(obligatorio para CN ≥ 10M EUR).",
    )
    nrs = fields.Char(
        string="Número de Referencia de Sociedades (NRS)",
        size=22,
    )
    info_quita_espera = fields.Monetary(
        string="Importe excluido por operaciones de quita o espera",
    )
    info_quita_espera_bi = fields.Monetary(
        string="Parte integrada en BI por operaciones de quita o espera",
    )
    info_quita_espera_cuota = fields.Monetary(
        string="Parte integrada en BI a nivel cuota por quita o espera",
    )
    info_reversion_deterioros = fields.Monetary(
        string="Rentas de reversión de deterioros",
    )
    info_ric = fields.Monetary(
        string="Reserva para inversiones en Canarias (RIC)",
    )
    info_bonif_art26 = fields.Monetary(
        string="Bonificación art. 26 Ley 19/1994",
    )
    info_zec = fields.Monetary(
        string="Régimen fiscal ZEC (importe no computable)",
    )
    info_ceuta_melilla = fields.Monetary(
        string="Minoración rentas Ceuta/Melilla",
    )
    info_aumento_capital = fields.Monetary(
        string="Importe excluido por aumento de capital",
    )
    info_renta_exenta_49_2002 = fields.Monetary(
        string="Renta exenta entidades Ley 49/2002",
    )
    info_bonif_art34 = fields.Monetary(
        string="Bonificación art. 34 LIS",
    )

    # --- Result type ---

    tipo_declaracion = fields.Selection(
        selection=[
            ("I", "A ingresar"),
            ("N", "Negativa"),
        ],
        string="Tipo de declaración",
        compute="_compute_tipo_declaracion",
        store=True,
    )

    # === COMPUTED FIELDS ===

    @api.depends("casilla_01", "casilla_02", "liquidacion_modalidad")
    def _compute_casilla_03(self):
        for report in self:
            if report.liquidacion_modalidad == "A":
                report.casilla_03 = report.casilla_01 - report.casilla_02
            else:
                report.casilla_03 = 0

    @api.depends("casilla_05", "casilla_06", "casilla_07", "casilla_08",
                 "casilla_09", "casilla_37")
    def _compute_total_correcciones(self):
        for report in self:
            report.casilla_38 = report.casilla_05 + report.casilla_08
            report.casilla_39 = (
                report.casilla_06 + report.casilla_07
                + report.casilla_37 + report.casilla_09
            )

    @api.depends("casilla_04", "casilla_38", "casilla_39")
    def _compute_casilla_13(self):
        for report in self:
            report.casilla_13 = (
                report.casilla_04 + report.casilla_38 - report.casilla_39
            )

    @api.depends("casilla_13", "casilla_40", "casilla_14",
                 "casilla_15", "casilla_16")
    def _compute_b1(self):
        for report in self:
            report.casilla_17_base = max(
                0,
                report.casilla_13
                - report.casilla_40
                - report.casilla_14
                - report.casilla_15
                + report.casilla_16,
            )

    @api.depends("casilla_17_base", "casilla_17_pct", "casilla_18",
                 "casilla_19_comp", "casilla_41", "casilla_42")
    def _compute_casilla_20(self):
        for report in self:
            if report.use_b2:
                report.casilla_20 = 0
            else:
                cuota = report.casilla_17_base * report.casilla_17_pct / 100
                report.casilla_20 = (
                    cuota - report.casilla_18 - report.casilla_19_comp
                    - report.casilla_41 + report.casilla_42
                )

    @api.depends(
        "b2_tramo1_base", "b2_tramo1_pct",
        "b2_tramo2_base", "b2_tramo2_pct",
        "b2_tramo3_base", "b2_tramo3_pct",
        "b2_tramo4_base", "b2_tramo4_pct",
    )
    def _compute_b2_tramos(self):
        for report in self:
            acum = 0
            for i in range(1, 5):
                base = getattr(report, f"b2_tramo{i}_base")
                pct = getattr(report, f"b2_tramo{i}_pct")
                resultado = base * pct / 100
                acum += resultado
                setattr(report, f"b2_tramo{i}_resultado", resultado)
                setattr(report, f"b2_tramo{i}_acumulado", acum)

    @api.depends(
        "b2_tramo4_acumulado", "b2_dotaciones",
        "b2_compensacion", "b2_nivelacion_min", "b2_nivelacion_add",
    )
    def _compute_b2_resultado_previo(self):
        for report in self:
            report.b2_resultado_previo = (
                report.b2_tramo4_acumulado
                - report.b2_dotaciones
                - report.b2_compensacion
                - report.b2_nivelacion_min
                + report.b2_nivelacion_add
            )

    @api.depends(
        "liquidacion_modalidad", "use_b2",
        "casilla_20", "b2_resultado_previo",
        "casilla_27", "casilla_28", "casilla_29_pct",
        "casilla_30", "casilla_31",
    )
    def _compute_casilla_32(self):
        for report in self:
            if report.liquidacion_modalidad != "B":
                report.casilla_32 = 0
                continue
            resultado_previo = (
                report.b2_resultado_previo if report.use_b2
                else report.casilla_20
            )
            subtotal = resultado_previo - report.casilla_27 - report.casilla_28
            con_territorio = subtotal * report.casilla_29_pct / 100
            report.casilla_32 = (
                con_territorio - report.casilla_30 - report.casilla_31
            )

    @api.depends("casilla_32", "casilla_33", "liquidacion_modalidad")
    def _compute_casilla_34(self):
        for report in self:
            if report.liquidacion_modalidad != "B":
                report.casilla_34 = 0
                continue
            if report.cn_tramo in ("1", "2", "3") and report.casilla_33 > 0:
                report.casilla_34 = max(report.casilla_32, report.casilla_33)
            else:
                report.casilla_34 = report.casilla_32

    @api.depends("liquidacion_modalidad", "casilla_03", "casilla_34")
    def _compute_tipo_declaracion(self):
        for report in self:
            if report.liquidacion_modalidad == "A":
                amount = report.casilla_03
            else:
                amount = report.casilla_34
            rounding = report.company_id.currency_id.rounding
            if float_is_zero(amount, precision_rounding=rounding):
                report.tipo_declaracion = "N"
            elif float_compare(amount, 0, precision_rounding=rounding) > 0:
                report.tipo_declaracion = "I"
            else:
                report.tipo_declaracion = "N"

    # === BUSINESS METHODS ===

    def calculate(self):
        for report in self:
            if (
                report.liquidacion_modalidad == "A"
                and report.casilla_01_mode == "auto"
            ):
                report._calculate_casilla_01_from_mod200()
            if report.liquidacion_modalidad == "B":
                report._calculate_b_percentage()
        return True

    def _calculate_casilla_01_from_mod200(self):
        """Fetch casilla [01] from the last confirmed Model 200 report."""
        self.ensure_one()
        mod200_model = self.env.get("l10n.es.aeat.mod200.report")
        if mod200_model is None:
            raise exceptions.UserError(
                self.env._(
                    "El módulo del Modelo 200 no está instalado. "
                    "Introduzca la casilla [01] manualmente."
                )
            )
        last_mod200 = mod200_model.search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "done"),
            ],
            order="year desc",
            limit=1,
        )
        if not last_mod200:
            raise exceptions.UserError(
                self.env._(
                    "No se encontró ninguna declaración del Modelo 200 confirmada "
                    "para esta empresa. Introduzca la casilla [01] manualmente."
                )
            )
        self.casilla_01 = last_mod200._get_pago_fraccionado_base()

    def _calculate_b_percentage(self):
        """Auto-calculate the B1 percentage from the tipo_gravamen field."""
        self.ensure_one()
        tipo = self.tipo_gravamen or "25"
        parts = tipo.split("/")
        if len(parts) == 1:
            rate = TIPO_GRAVAMEN_MAP.get(parts[0], 25)
            self.casilla_17_pct = _round_up_pct(rate)
        else:
            for i, part in enumerate(parts):
                rate = TIPO_GRAVAMEN_MAP.get(part, 25)
                pct = _round_up_pct(rate)
                if i < 4:
                    setattr(self, f"b2_tramo{i + 1}_pct", pct)
            if len(parts) > 1:
                self.use_b2 = True

    def button_confirm(self):
        for report in self:
            if report.liquidacion_modalidad == "A":
                if float_compare(
                    report.casilla_03, 0,
                    precision_rounding=report.company_id.currency_id.rounding,
                ) < 0:
                    raise exceptions.ValidationError(
                        self.env._(
                            "Modalidad A: El resultado [03] no puede ser negativo."
                        )
                    )
            if (
                report.statement_type == "C"
                and report.liquidacion_modalidad == "A"
                and not report.casilla_02
            ):
                raise exceptions.ValidationError(
                    self.env._(
                        "En declaración complementaria debe introducir un importe "
                        "en la casilla [02]."
                    )
                )
            if (
                report.statement_type == "C"
                and report.liquidacion_modalidad == "B"
                and not report.casilla_31
            ):
                raise exceptions.ValidationError(
                    self.env._(
                        "En declaración complementaria debe introducir un importe "
                        "en la casilla [31]."
                    )
                )
        return super().button_confirm()
