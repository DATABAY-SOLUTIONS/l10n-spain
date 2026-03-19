# Copyright 2025 Databay Solutions
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from datetime import timedelta

from odoo import api, exceptions, fields, models
from odoo.tools import float_compare


class L10nEsAeatMod200Report(models.Model):
    _description = "AEAT 200 report"
    _inherit = "l10n.es.aeat.report"
    _name = "l10n.es.aeat.mod200.report"
    _aeat_number = "200"
    _period_quarterly = False
    _period_monthly = False
    _period_yearly = True

    # -------------------------------------------------------------------------
    # Page 1: Identification & declaration characteristics
    # -------------------------------------------------------------------------

    date_start_period = fields.Date(
        string="Fecha inicio período impositivo",
    )
    date_end_period = fields.Date(
        string="Fecha fin período impositivo",
    )
    cnae_actividad = fields.Char(
        string="CNAE actividad principal",
        size=4,
    )

    # --- Declaration type flags ---
    regimen_general = fields.Boolean(
        string="Régimen general",
        default=True,
    )
    regimen_erd = fields.Boolean(
        string="Entidad de reducida dimensión (ERD)",
    )
    gran_empresa = fields.Boolean(
        string="Gran empresa",
    )
    entidad_parcialmente_exenta = fields.Boolean(
        string="Entidad parcialmente exenta",
    )
    entidad_sin_fines_lucrativos = fields.Boolean(
        string="Entidad sin fines lucrativos (Ley 49/2002)",
    )
    cooperativa_protegida = fields.Boolean(
        string="Cooperativa fiscalmente protegida",
    )
    socimi = fields.Boolean(
        string="SOCIMI (Ley 11/2009)",
    )
    regimen_naviero = fields.Boolean(
        string="Régimen naviero (tonelaje)",
    )
    zec = fields.Boolean(
        string="Zona Especial Canaria (ZEC)",
    )

    tipo_cuentas_anuales = fields.Selection(
        selection=[
            ("N", "Normal"),
            ("A", "Abreviado"),
            ("P", "PYMES"),
        ],
        string="Tipo de cuentas anuales",
        default="P",
        help="Determina qué páginas BOE se generan y si ECPN/EFE son obligatorios.",
    )
    cnae_secundario = fields.Char(
        string="CNAE actividad secundaria",
        size=4,
    )
    fecha_constitucion = fields.Date(
        string="Fecha de constitución",
    )
    entidad_inactiva = fields.Boolean(
        string="Entidad inactiva",
    )
    admin_ids = fields.One2many(
        comodel_name="l10n.es.aeat.mod200.admin",
        inverse_name="report_id",
        string="Administradores / Representantes",
    )

    # --- Tax rate ---
    tipo_gravamen = fields.Selection(
        selection=[
            ("25", "25% - General"),
            ("23", "23% - Empresas CN < 1M EUR"),
            ("15", "15% - Entidades nueva creación"),
            ("20", "20% - Cooperativas protegidas"),
            ("10", "10% - Entidades Ley 49/2002"),
            ("1", "1% - SOCIMI / SII"),
            ("0", "0% - Fondos de pensiones"),
            ("30", "30% - Entidades de crédito"),
        ],
        string="Tipo de gravamen",
        default="25",
    )

    # -------------------------------------------------------------------------
    # Page 14: Base imponible & Cuota íntegra (simplified for Fase 1)
    # -------------------------------------------------------------------------

    resultado_contable = fields.Monetary(
        string="[500] Resultado de la cuenta de PyG",
        help="Resultado de la cuenta de pérdidas y ganancias (saldo acreedor "
        "con signo positivo, saldo deudor con signo negativo).",
    )

    # Corrections aggregate
    correcciones_aumentos = fields.Monetary(
        string="[501] Correcciones al resultado contable - Aumentos",
        compute="_compute_correcciones_totales",
        store=True,
    )
    correcciones_disminuciones = fields.Monetary(
        string="[502] Correcciones al resultado contable - Disminuciones",
        compute="_compute_correcciones_totales",
        store=True,
    )

    # Detailed corrections (manual fields)
    corr_amortizaciones_aumento = fields.Monetary(
        string="[503] Amortizaciones - Aumentos"
    )
    corr_amortizaciones_disminucion = fields.Monetary(
        string="[504] Amortizaciones - Disminuciones"
    )
    corr_deterioros_aumento = fields.Monetary(
        string="[505] Pérdidas por deterioro - Aumentos"
    )
    corr_deterioros_disminucion = fields.Monetary(
        string="[506] Pérdidas por deterioro - Disminuciones"
    )
    corr_provisiones_aumento = fields.Monetary(
        string="[507] Provisiones - Aumentos"
    )
    corr_provisiones_disminucion = fields.Monetary(
        string="[508] Provisiones - Disminuciones"
    )
    corr_operaciones_vinculadas_aumento = fields.Monetary(
        string="[510] Operaciones vinculadas - Aumentos"
    )
    corr_operaciones_vinculadas_disminucion = fields.Monetary(
        string="[511] Operaciones vinculadas - Disminuciones"
    )
    corr_subvenciones_aumento = fields.Monetary(
        string="[515] Imputación de subvenciones - Aumentos"
    )
    corr_subvenciones_disminucion = fields.Monetary(
        string="[516] Imputación de subvenciones - Disminuciones"
    )
    corr_gastos_no_deducibles_aumento = fields.Monetary(
        string="[520] Gastos no deducibles - Aumentos",
        help="Multas, sanciones, donativos, atenciones a clientes que excedan "
        "el 1% del INCN, retribuciones fondos propios, etc.",
    )
    corr_libertad_amortizacion_disminucion = fields.Monetary(
        string="[525] Libertad de amortización (ERD) - Disminuciones"
    )
    corr_reserva_capitalizacion_disminucion = fields.Monetary(
        string="[530] Reserva de capitalización - Disminuciones"
    )
    corr_reserva_nivelacion_disminucion = fields.Monetary(
        string="[535] Reserva de nivelación (ERD) - Disminuciones"
    )
    corr_otras_correcciones_aumento = fields.Monetary(
        string="[540] Otras correcciones - Aumentos"
    )
    corr_otras_correcciones_disminucion = fields.Monetary(
        string="[541] Otras correcciones - Disminuciones"
    )
    base_imponible_previa = fields.Monetary(
        string="[550] Base imponible previa",
        compute="_compute_base_imponible_previa",
        store=True,
    )

    compensacion_bins = fields.Monetary(
        string="[547] Compensación BINs",
        help="Compensación de bases imponibles negativas de ejercicios anteriores.",
    )
    base_imponible = fields.Monetary(
        string="[552] Base imponible",
        compute="_compute_base_imponible",
        store=True,
    )

    # --- Cuota ---
    cuota_integra = fields.Monetary(
        string="[562] Cuota íntegra",
        compute="_compute_cuota_integra",
        store=True,
    )
    deducciones_doble_imposicion = fields.Monetary(
        string="[582] Deducciones por doble imposición",
        compute="_compute_deduc_doble_imp",
        store=True,
    )
    bonificaciones = fields.Monetary(
        string="[584] Bonificaciones",
        compute="_compute_bonificaciones",
        store=True,
    )
    cuota_integra_ajustada = fields.Monetary(
        string="[592] Cuota íntegra ajustada positiva",
        compute="_compute_cuota_integra_ajustada",
        store=True,
    )

    # --- Detailed deductions (manual fields) ---
    deduc_doble_imp_internacional = fields.Monetary(
        string="[576] Deducciones por doble imposición internacional"
    )
    deduc_doble_imp_interna = fields.Monetary(
        string="[578] Deducciones por doble imposición interna"
    )
    bonif_rentas_ceuta_melilla = fields.Monetary(
        string="[585] Bonificación Ceuta y Melilla"
    )
    bonif_cooperativas = fields.Monetary(
        string="[586] Bonificación cooperativas protegidas"
    )
    bonif_otras = fields.Monetary(
        string="[588] Otras bonificaciones"
    )
    deduc_idi = fields.Monetary(
        string="[601] Deducciones I+D+i"
    )
    deduc_producciones_cinematograficas = fields.Monetary(
        string="[602] Deducciones producciones cinematográficas"
    )
    deduc_creacion_empleo = fields.Monetary(
        string="[603] Deducciones creación de empleo"
    )
    deduc_creacion_empleo_discapacidad = fields.Monetary(
        string="[604] Deducciones creación empleo discapacidad"
    )
    deduc_donativos = fields.Monetary(
        string="[605] Deducciones por donativos"
    )
    deduc_otras_inversiones = fields.Monetary(
        string="[606] Otras deducciones por inversiones"
    )
    deducciones_inversiones = fields.Monetary(
        string="[600] Deducciones por inversiones",
        compute="_compute_deducciones_inversiones",
        store=True,
    )
    cuota_liquida = fields.Monetary(
        string="[612] Cuota líquida positiva",
        compute="_compute_cuota_liquida",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Page 18: Result
    # -------------------------------------------------------------------------

    retenciones_ingresos_cuenta = fields.Monetary(
        string="[595] Retenciones e ingresos a cuenta",
    )
    pagos_fraccionados = fields.Monetary(
        string="[596] Pagos fraccionados",
        help="Total pagos fraccionados del ejercicio (modelo 202).",
    )
    cuota_diferencial = fields.Monetary(
        string="[621] Cuota diferencial",
        compute="_compute_cuota_diferencial",
        store=True,
    )
    resultado_liquidacion = fields.Monetary(
        string="[625] Resultado de la liquidación",
        compute="_compute_resultado_liquidacion",
        store=True,
    )

    tipo_declaracion = fields.Selection(
        selection=[
            ("I", "A ingresar"),
            ("D", "A devolver"),
            ("N", "Negativa / Cuota cero"),
        ],
        string="Tipo de declaración",
        compute="_compute_tipo_declaracion",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Balance sheet fields (pages 03-06 BOE)
    # -------------------------------------------------------------------------
    # ACTIVO NO CORRIENTE
    activo_inmovilizado_intangible = fields.Monetary(
        string="[0015] Inmovilizado intangible",
    )
    # Detail casillas for Inmovilizado intangible [00102]
    activo_ii_desarrollo = fields.Monetary(string="[00103] Desarrollo")
    activo_ii_concesiones = fields.Monetary(string="[00104] Concesiones")
    activo_ii_patentes = fields.Monetary(string="[00105] Patentes, licencias, marcas")
    activo_ii_fondo_comercio = fields.Monetary(string="[00106] Fondo de comercio")
    activo_ii_aplicaciones_informaticas = fields.Monetary(
        string="[00107] Aplicaciones informáticas"
    )
    activo_ii_investigacion = fields.Monetary(string="[00108] Investigación")
    activo_ii_otro = fields.Monetary(string="[00109] Otro inmovilizado intangible")
    activo_inmovilizado_material = fields.Monetary(
        string="[0020] Inmovilizado material",
    )
    # Detail casillas for Inmovilizado material
    activo_im_terrenos = fields.Monetary(string="[00112] Terrenos y construcciones")
    activo_im_instalaciones = fields.Monetary(
        string="[00113] Instalaciones técnicas y otro inmovilizado material"
    )
    activo_im_inmovilizado_curso = fields.Monetary(
        string="[00114] Inmovilizado en curso y anticipos"
    )
    activo_inversiones_inmobiliarias = fields.Monetary(
        string="[0025] Inversiones inmobiliarias",
    )
    activo_inv_inm_terrenos = fields.Monetary(
        string="[00117] Inversiones inmobiliarias - Terrenos"
    )
    activo_inv_inm_construcciones = fields.Monetary(
        string="[00118] Inversiones inmobiliarias - Construcciones"
    )
    activo_inversiones_empresas_grupo_lp = fields.Monetary(
        string="[0030] Inversiones en empresas del grupo y asociadas a L/P",
    )
    activo_ieg_lp_instrumentos_patrimonio = fields.Monetary(
        string="[00121] Instrumentos de patrimonio (grupo/asoc L/P)"
    )
    activo_ieg_lp_creditos = fields.Monetary(
        string="[00122] Créditos a empresas (grupo/asoc L/P)"
    )
    activo_ieg_lp_valores_deuda = fields.Monetary(
        string="[00123] Valores representativos de deuda (grupo/asoc L/P)"
    )
    activo_ieg_lp_derivados = fields.Monetary(
        string="[00124] Derivados (grupo/asoc L/P)"
    )
    activo_ieg_lp_otros = fields.Monetary(
        string="[00125] Otros activos financieros (grupo/asoc L/P)"
    )
    activo_inversiones_financieras_lp = fields.Monetary(
        string="[0035] Inversiones financieras a largo plazo",
    )
    activo_if_lp_instrumentos_patrimonio = fields.Monetary(
        string="[00128] Instrumentos de patrimonio (IF L/P)"
    )
    activo_if_lp_creditos_terceros = fields.Monetary(
        string="[00129] Créditos a terceros (IF L/P)"
    )
    activo_if_lp_valores_deuda = fields.Monetary(
        string="[00130] Valores representativos de deuda (IF L/P)"
    )
    activo_if_lp_derivados = fields.Monetary(
        string="[00131] Derivados (IF L/P)"
    )
    activo_if_lp_otros = fields.Monetary(
        string="[00132] Otros activos financieros (IF L/P)"
    )
    activo_activos_impuesto_diferido = fields.Monetary(
        string="[0040] Activos por impuesto diferido",
    )
    activo_deudores_comerciales_nc = fields.Monetary(
        string="[0045] Deudores comerciales no corrientes",
    )

    # ACTIVO CORRIENTE
    activo_existencias = fields.Monetary(
        string="[0060] Existencias",
    )
    activo_exist_comerciales = fields.Monetary(
        string="[00139] Comerciales"
    )
    activo_exist_materias_primas = fields.Monetary(
        string="[00140] Materias primas y otros aprovisionamientos"
    )
    activo_exist_productos_curso = fields.Monetary(
        string="[00141] Productos en curso"
    )
    activo_exist_productos_terminados = fields.Monetary(
        string="[00142] Productos terminados"
    )
    activo_exist_subproductos = fields.Monetary(
        string="[00143] Subproductos, residuos y materiales recuperados"
    )
    activo_exist_anticipos = fields.Monetary(
        string="[00144] Anticipos a proveedores"
    )
    activo_deudores_comerciales = fields.Monetary(
        string="[0065] Deudores comerciales y otras cuentas a cobrar",
    )
    activo_dc_clientes_ventas = fields.Monetary(
        string="[00146] Clientes por ventas y prestaciones de servicios"
    )
    activo_dc_clientes_grupo = fields.Monetary(
        string="[00147] Clientes empresas del grupo y asociadas"
    )
    activo_dc_deudores_varios = fields.Monetary(
        string="[00148] Deudores varios"
    )
    activo_dc_personal = fields.Monetary(
        string="[00149] Personal"
    )
    activo_dc_activos_impuesto_corriente = fields.Monetary(
        string="[00150] Activos por impuesto corriente"
    )
    activo_dc_otros_creditos_aapp = fields.Monetary(
        string="[00151] Otros créditos con las Administraciones Públicas"
    )
    activo_dc_accionistas_desembolsos = fields.Monetary(
        string="[00152] Accionistas (socios) por desembolsos exigidos"
    )
    activo_inversiones_empresas_grupo_cp = fields.Monetary(
        string="[0070] Inversiones en empresas del grupo y asociadas a C/P",
    )
    activo_ieg_cp_instrumentos_patrimonio = fields.Monetary(
        string="[00155] Instrumentos de patrimonio (grupo/asoc C/P)"
    )
    activo_ieg_cp_creditos = fields.Monetary(
        string="[00156] Créditos a empresas (grupo/asoc C/P)"
    )
    activo_ieg_cp_valores_deuda = fields.Monetary(
        string="[00157] Valores representativos de deuda (grupo/asoc C/P)"
    )
    activo_ieg_cp_derivados = fields.Monetary(
        string="[00158] Derivados (grupo/asoc C/P)"
    )
    activo_ieg_cp_otros = fields.Monetary(
        string="[00159] Otros activos financieros (grupo/asoc C/P)"
    )
    activo_inversiones_financieras_cp = fields.Monetary(
        string="[0075] Inversiones financieras a corto plazo",
    )
    activo_if_cp_instrumentos_patrimonio = fields.Monetary(
        string="[00162] Instrumentos de patrimonio (IF C/P)"
    )
    activo_if_cp_creditos_terceros = fields.Monetary(
        string="[00163] Créditos a terceros (IF C/P)"
    )
    activo_if_cp_valores_deuda = fields.Monetary(
        string="[00164] Valores representativos de deuda (IF C/P)"
    )
    activo_if_cp_derivados = fields.Monetary(
        string="[00165] Derivados (IF C/P)"
    )
    activo_if_cp_otros = fields.Monetary(
        string="[00166] Otros activos financieros (IF C/P)"
    )
    activo_periodificaciones_cp = fields.Monetary(
        string="[0080] Periodificaciones a corto plazo",
    )
    activo_efectivo = fields.Monetary(
        string="[0085] Efectivo y otros activos líquidos equivalentes",
    )

    # TOTALS
    activo_no_corriente = fields.Monetary(
        string="[0050] Total activo no corriente",
        compute="_compute_activo_no_corriente",
        store=True,
    )
    activo_corriente = fields.Monetary(
        string="[0090] Total activo corriente",
        compute="_compute_activo_corriente",
        store=True,
    )
    total_activo = fields.Monetary(
        string="[0095] Total activo",
        compute="_compute_total_activo",
        store=True,
    )

    # PATRIMONIO NETO
    pn_capital = fields.Monetary(
        string="[0100] Capital / Fondo social",
    )
    pn_prima_emision = fields.Monetary(
        string="[0105] Prima de emisión",
    )
    pn_reservas = fields.Monetary(
        string="[0110] Reservas",
    )
    pn_reservas_legal = fields.Monetary(string="[00183] Reserva legal")
    pn_reservas_estatutarias = fields.Monetary(string="[00184] Reservas estatutarias")
    pn_reservas_voluntarias = fields.Monetary(string="[00185] Reservas voluntarias")
    pn_reservas_otras = fields.Monetary(string="[00186] Otras reservas")
    pn_acciones_propias = fields.Monetary(
        string="[0115] (Acciones y participaciones en patrimonio propias)",
    )
    pn_resultados_ejercicios_anteriores = fields.Monetary(
        string="[0120] Resultados de ejercicios anteriores",
    )
    pn_otras_aportaciones_socios = fields.Monetary(
        string="[0125] Otras aportaciones de socios",
    )
    pn_resultado_ejercicio = fields.Monetary(
        string="[0130] Resultado del ejercicio",
    )
    pn_dividendo_cuenta = fields.Monetary(
        string="[0135] (Dividendo a cuenta)",
    )
    pn_ajustes_cambio_valor = fields.Monetary(
        string="[0140] Ajustes por cambio de valor",
    )
    pn_ajustes_activos_venta = fields.Monetary(
        string="[00200] Activos financieros disponibles para la venta"
    )
    pn_ajustes_cobertura = fields.Monetary(
        string="[00201] Operaciones de cobertura"
    )
    pn_ajustes_otros = fields.Monetary(
        string="[00202] Otros ajustes por cambio de valor"
    )
    pn_subvenciones = fields.Monetary(
        string="[0145] Subvenciones, donaciones y legados recibidos",
    )

    # PASIVO NO CORRIENTE
    pasivo_provisiones_lp = fields.Monetary(
        string="[0160] Provisiones a largo plazo",
    )
    pasivo_prov_lp_obligaciones_prestaciones = fields.Monetary(
        string="[00209] Obligaciones por prestaciones a L/P al personal"
    )
    pasivo_prov_lp_actuaciones_medioambientales = fields.Monetary(
        string="[00210] Provisiones para actuaciones medioambientales"
    )
    pasivo_prov_lp_reestructuraciones = fields.Monetary(
        string="[00211] Provisiones para reestructuraciones"
    )
    pasivo_prov_lp_otras = fields.Monetary(
        string="[00212] Otras provisiones a largo plazo"
    )
    pasivo_deudas_lp = fields.Monetary(
        string="[0165] Deudas a largo plazo",
    )
    pasivo_deudas_lp_obligaciones = fields.Monetary(
        string="[00214] Obligaciones y otros valores negociables (L/P)"
    )
    pasivo_deudas_lp_entidades_credito = fields.Monetary(
        string="[00215] Deudas con entidades de crédito (L/P)"
    )
    pasivo_deudas_lp_arrendamiento = fields.Monetary(
        string="[00216] Acreedores por arrendamiento financiero (L/P)"
    )
    pasivo_deudas_lp_derivados = fields.Monetary(
        string="[00217] Derivados (L/P)"
    )
    pasivo_deudas_lp_otras = fields.Monetary(
        string="[00218] Otras deudas a largo plazo"
    )
    pasivo_deudas_empresas_grupo_lp = fields.Monetary(
        string="[0170] Deudas con empresas del grupo y asociadas a L/P",
    )
    pasivo_pasivos_impuesto_diferido = fields.Monetary(
        string="[0175] Pasivos por impuesto diferido",
    )
    pasivo_periodificaciones_lp = fields.Monetary(
        string="[0180] Periodificaciones a largo plazo",
    )
    pasivo_acreedores_comerciales_nc = fields.Monetary(
        string="[0185] Acreedores comerciales no corrientes",
    )
    pasivo_deuda_carac_especiales_lp = fields.Monetary(
        string="[0190] Deuda con características especiales a L/P",
    )

    # PASIVO CORRIENTE
    pasivo_provisiones_cp = fields.Monetary(
        string="[0200] Provisiones a corto plazo",
    )
    pasivo_deudas_cp = fields.Monetary(
        string="[0205] Deudas a corto plazo",
    )
    pasivo_deudas_cp_obligaciones = fields.Monetary(
        string="[00240] Obligaciones y otros valores negociables (C/P)"
    )
    pasivo_deudas_cp_entidades_credito = fields.Monetary(
        string="[00241] Deudas con entidades de crédito (C/P)"
    )
    pasivo_deudas_cp_arrendamiento = fields.Monetary(
        string="[00242] Acreedores por arrendamiento financiero (C/P)"
    )
    pasivo_deudas_cp_derivados = fields.Monetary(
        string="[00243] Derivados (C/P)"
    )
    pasivo_deudas_cp_otras = fields.Monetary(
        string="[00244] Otras deudas a corto plazo"
    )
    pasivo_deudas_empresas_grupo_cp = fields.Monetary(
        string="[0210] Deudas con empresas del grupo y asociadas a C/P",
    )
    pasivo_acreedores_comerciales = fields.Monetary(
        string="[0215] Acreedores comerciales y otras cuentas a pagar",
    )
    pasivo_ac_proveedores = fields.Monetary(
        string="[00249] Proveedores"
    )
    pasivo_ac_proveedores_grupo = fields.Monetary(
        string="[00250] Proveedores empresas del grupo y asociadas"
    )
    pasivo_ac_acreedores_varios = fields.Monetary(
        string="[00251] Acreedores varios"
    )
    pasivo_ac_personal = fields.Monetary(
        string="[00252] Personal (remuneraciones pendientes de pago)"
    )
    pasivo_ac_pasivos_impuesto_corriente = fields.Monetary(
        string="[00253] Pasivos por impuesto corriente"
    )
    pasivo_ac_otras_deudas_aapp = fields.Monetary(
        string="[00254] Otras deudas con las Administraciones Públicas"
    )
    pasivo_ac_anticipos_clientes = fields.Monetary(
        string="[00255] Anticipos de clientes"
    )
    pasivo_periodificaciones_cp = fields.Monetary(
        string="[0220] Periodificaciones a corto plazo",
    )
    pasivo_deuda_carac_especiales_cp = fields.Monetary(
        string="[0225] Deuda con características especiales a C/P",
    )

    # TOTALS PASIVO
    patrimonio_neto = fields.Monetary(
        string="[0150] Total patrimonio neto",
        compute="_compute_patrimonio_neto",
        store=True,
    )
    pasivo_no_corriente = fields.Monetary(
        string="[0195] Total pasivo no corriente",
        compute="_compute_pasivo_no_corriente",
        store=True,
    )
    pasivo_corriente = fields.Monetary(
        string="[0230] Total pasivo corriente",
        compute="_compute_pasivo_corriente",
        store=True,
    )
    total_patrimonio_neto_pasivo = fields.Monetary(
        string="[0235] Total patrimonio neto y pasivo",
        compute="_compute_total_patrimonio_neto_pasivo",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Profit & Loss fields (pages 3-5)
    # -------------------------------------------------------------------------
    pyg_importe_neto_cifra_negocios = fields.Monetary(
        string="[0255] Importe neto de la cifra de negocios",
    )
    pyg_incn_ventas = fields.Monetary(
        string="[00256] Ventas"
    )
    pyg_incn_prestaciones_servicios = fields.Monetary(
        string="[00257] Prestaciones de servicios"
    )
    pyg_variacion_existencias = fields.Monetary(
        string="[0260] Variación de existencias de PT y PC",
    )
    pyg_trabajos_activo = fields.Monetary(
        string="[0265] Trabajos realizados por la empresa para su activo",
    )
    pyg_aprovisionamientos = fields.Monetary(
        string="[0270] Aprovisionamientos",
    )
    pyg_aprov_consumo_mercaderias = fields.Monetary(
        string="[00270] Consumo de mercaderías"
    )
    pyg_aprov_consumo_materias_primas = fields.Monetary(
        string="[00271] Consumo de materias primas y otras materias consumibles"
    )
    pyg_aprov_trabajos_otras_empresas = fields.Monetary(
        string="[00272] Trabajos realizados por otras empresas"
    )
    pyg_aprov_deterioro = fields.Monetary(
        string="[00273] Deterioro de mercaderías, materias primas y otros"
    )
    pyg_otros_ingresos_explotacion = fields.Monetary(
        string="[0275] Otros ingresos de explotación",
    )
    pyg_oie_ingresos_accesorios = fields.Monetary(
        string="[00276] Ingresos accesorios y otros de gestión corriente"
    )
    pyg_oie_subvenciones_explotacion = fields.Monetary(
        string="[00277] Subvenciones de explotación incorporadas al resultado"
    )
    pyg_gastos_personal = fields.Monetary(
        string="[0280] Gastos de personal",
    )
    pyg_gp_sueldos_salarios = fields.Monetary(
        string="[00281] Sueldos, salarios y asimilados"
    )
    pyg_gp_cargas_sociales = fields.Monetary(
        string="[00282] Cargas sociales"
    )
    pyg_gp_provisiones = fields.Monetary(
        string="[00283] Provisiones"
    )
    pyg_otros_gastos_explotacion = fields.Monetary(
        string="[0285] Otros gastos de explotación",
    )
    pyg_oge_servicios_exteriores = fields.Monetary(
        string="[00286] Servicios exteriores"
    )
    pyg_oge_tributos = fields.Monetary(
        string="[00287] Tributos"
    )
    pyg_oge_perdidas_deterioro_creditos = fields.Monetary(
        string="[00288] Pérdidas, deterioro y variación de provisiones por ops comerciales"
    )
    pyg_oge_otros_gastos_gestion = fields.Monetary(
        string="[00289] Otros gastos de gestión corriente"
    )
    pyg_amortizacion_inmovilizado = fields.Monetary(
        string="[0290] Amortización del inmovilizado",
    )
    pyg_imputacion_subvenciones = fields.Monetary(
        string="[0295] Imputación de subvenciones de inmovilizado no financiero",
    )
    pyg_excesos_provisiones = fields.Monetary(
        string="[0300] Exceso de provisiones",
    )
    pyg_deterioro_enajenacion_inmovilizado = fields.Monetary(
        string="[0305] Deterioro y resultado por enajenaciones del inmovilizado",
    )
    pyg_diferencia_negativa_combinaciones = fields.Monetary(
        string="[0310] Diferencia negativa de combinaciones de negocio",
    )
    pyg_otros_resultados = fields.Monetary(
        string="[0315] Otros resultados",
    )
    pyg_resultado_explotacion = fields.Monetary(
        string="[0320] Resultado de explotación",
        compute="_compute_pyg_resultado_explotacion",
        store=True,
    )

    # Financial result
    pyg_ingresos_financieros = fields.Monetary(
        string="[0325] Ingresos financieros",
    )
    pyg_if_participaciones_patrimonio = fields.Monetary(
        string="[00326] De participaciones en instrumentos de patrimonio"
    )
    pyg_if_valores_negociables = fields.Monetary(
        string="[00327] De valores negociables y otros instrumentos financieros"
    )
    pyg_gastos_financieros = fields.Monetary(
        string="[0330] Gastos financieros",
    )
    pyg_gf_deudas_grupo = fields.Monetary(
        string="[00331] Por deudas con empresas del grupo y asociadas"
    )
    pyg_gf_deudas_terceros = fields.Monetary(
        string="[00332] Por deudas con terceros"
    )
    pyg_gf_provision_ajuste_valor = fields.Monetary(
        string="[00333] Por actualización de provisiones"
    )
    pyg_variacion_valor_razonable = fields.Monetary(
        string="[0335] Variación de valor razonable en instrumentos financieros",
    )
    pyg_diferencias_cambio = fields.Monetary(
        string="[0340] Diferencias de cambio",
    )
    pyg_deterioro_enajenacion_if = fields.Monetary(
        string="[0345] Deterioro y resultado por enajenaciones de IF",
    )
    pyg_otros_ingresos_gastos_financieros = fields.Monetary(
        string="[0348] Otros ingresos y gastos de carácter financiero",
    )
    pyg_resultado_financiero = fields.Monetary(
        string="[0350] Resultado financiero",
        compute="_compute_pyg_resultado_financiero",
        store=True,
    )

    pyg_resultado_antes_impuestos = fields.Monetary(
        string="[0355] Resultado antes de impuestos",
        compute="_compute_pyg_resultado_antes_impuestos",
        store=True,
    )
    pyg_impuesto_beneficios = fields.Monetary(
        string="[0360] Impuesto sobre beneficios",
    )
    pyg_resultado_ejercicio = fields.Monetary(
        string="[0365] Resultado del ejercicio procedente de operaciones continuadas",
        compute="_compute_pyg_resultado_ejercicio",
        store=True,
    )
    pyg_resultado_ops_interrumpidas = fields.Monetary(
        string="[0370] Resultado de operaciones interrumpidas neto de impuestos",
    )
    pyg_resultado_ejercicio_total = fields.Monetary(
        string="[0375] Resultado del ejercicio",
        compute="_compute_pyg_resultado_ejercicio_total",
        store=True,
    )

    # -------------------------------------------------------------------------
    # ECPN (Estado de Cambios en el Patrimonio Neto) - Pages 6-8
    # -------------------------------------------------------------------------
    ecpn_resultado_pyg = fields.Monetary(
        string="[0380] Resultado de la cuenta de PyG (ECPN)",
    )
    ecpn_ingresos_gastos_pn = fields.Monetary(
        string="[0385] Total ingresos y gastos imputados directamente en PN",
    )
    ecpn_transferencias_pyg = fields.Monetary(
        string="[0390] Total transferencias a la cuenta de PyG",
    )
    ecpn_total_ingresos_gastos = fields.Monetary(
        string="[0395] Total de ingresos y gastos reconocidos",
        compute="_compute_ecpn_total",
        store=True,
    )

    ecpn_pn_inicio = fields.Monetary(
        string="[0400] Patrimonio neto a inicio del ejercicio",
    )
    ecpn_ajustes = fields.Monetary(
        string="[0405] Ajustes por cambios de criterio y errores",
    )
    ecpn_pn_inicio_ajustado = fields.Monetary(
        string="[0410] Patrimonio neto a inicio ajustado",
        compute="_compute_ecpn_pn_inicio_ajustado",
        store=True,
    )
    ecpn_variaciones_pn = fields.Monetary(
        string="[0415] Variaciones de patrimonio neto en el ejercicio",
    )
    ecpn_pn_final = fields.Monetary(
        string="[0420] Patrimonio neto al final del ejercicio",
        compute="_compute_ecpn_pn_final",
        store=True,
    )

    # -------------------------------------------------------------------------
    # EFE (Estado de Flujos de Efectivo) - Page 9
    # -------------------------------------------------------------------------
    efe_flujos_explotacion = fields.Monetary(
        string="[0425] Flujos de efectivo de las actividades de explotación",
    )
    efe_flujos_inversion = fields.Monetary(
        string="[0430] Flujos de efectivo de las actividades de inversión",
    )
    efe_flujos_financiacion = fields.Monetary(
        string="[0435] Flujos de efectivo de las actividades de financiación",
    )
    efe_efecto_tipo_cambio = fields.Monetary(
        string="[0440] Efecto de las variaciones de los tipos de cambio",
    )
    efe_aumento_disminucion_efectivo = fields.Monetary(
        string="[0445] Aumento/disminución neta del efectivo",
        compute="_compute_efe_total",
        store=True,
    )
    efe_efectivo_inicio = fields.Monetary(
        string="[0450] Efectivo y equivalentes al inicio del ejercicio",
    )
    efe_efectivo_final = fields.Monetary(
        string="[0455] Efectivo y equivalentes al final del ejercicio",
        compute="_compute_efe_efectivo_final",
        store=True,
    )

    # =====================================================================
    # COMPUTED METHODS - Balance
    # =====================================================================

    @api.depends(
        "activo_inmovilizado_intangible",
        "activo_inmovilizado_material",
        "activo_inversiones_inmobiliarias",
        "activo_inversiones_empresas_grupo_lp",
        "activo_inversiones_financieras_lp",
        "activo_activos_impuesto_diferido",
        "activo_deudores_comerciales_nc",
    )
    def _compute_activo_no_corriente(self):
        for report in self:
            report.activo_no_corriente = (
                report.activo_inmovilizado_intangible
                + report.activo_inmovilizado_material
                + report.activo_inversiones_inmobiliarias
                + report.activo_inversiones_empresas_grupo_lp
                + report.activo_inversiones_financieras_lp
                + report.activo_activos_impuesto_diferido
                + report.activo_deudores_comerciales_nc
            )

    @api.depends(
        "activo_existencias",
        "activo_deudores_comerciales",
        "activo_inversiones_empresas_grupo_cp",
        "activo_inversiones_financieras_cp",
        "activo_periodificaciones_cp",
        "activo_efectivo",
    )
    def _compute_activo_corriente(self):
        for report in self:
            report.activo_corriente = (
                report.activo_existencias
                + report.activo_deudores_comerciales
                + report.activo_inversiones_empresas_grupo_cp
                + report.activo_inversiones_financieras_cp
                + report.activo_periodificaciones_cp
                + report.activo_efectivo
            )

    @api.depends("activo_no_corriente", "activo_corriente")
    def _compute_total_activo(self):
        for report in self:
            report.total_activo = (
                report.activo_no_corriente + report.activo_corriente
            )

    @api.depends(
        "pn_capital",
        "pn_prima_emision",
        "pn_reservas",
        "pn_acciones_propias",
        "pn_resultados_ejercicios_anteriores",
        "pn_otras_aportaciones_socios",
        "pn_resultado_ejercicio",
        "pn_dividendo_cuenta",
        "pn_ajustes_cambio_valor",
        "pn_subvenciones",
    )
    def _compute_patrimonio_neto(self):
        for report in self:
            report.patrimonio_neto = (
                report.pn_capital
                + report.pn_prima_emision
                + report.pn_reservas
                + report.pn_acciones_propias
                + report.pn_resultados_ejercicios_anteriores
                + report.pn_otras_aportaciones_socios
                + report.pn_resultado_ejercicio
                + report.pn_dividendo_cuenta
                + report.pn_ajustes_cambio_valor
                + report.pn_subvenciones
            )

    @api.depends(
        "pasivo_provisiones_lp",
        "pasivo_deudas_lp",
        "pasivo_deudas_empresas_grupo_lp",
        "pasivo_pasivos_impuesto_diferido",
        "pasivo_periodificaciones_lp",
        "pasivo_acreedores_comerciales_nc",
        "pasivo_deuda_carac_especiales_lp",
    )
    def _compute_pasivo_no_corriente(self):
        for report in self:
            report.pasivo_no_corriente = (
                report.pasivo_provisiones_lp
                + report.pasivo_deudas_lp
                + report.pasivo_deudas_empresas_grupo_lp
                + report.pasivo_pasivos_impuesto_diferido
                + report.pasivo_periodificaciones_lp
                + report.pasivo_acreedores_comerciales_nc
                + report.pasivo_deuda_carac_especiales_lp
            )

    @api.depends(
        "pasivo_provisiones_cp",
        "pasivo_deudas_cp",
        "pasivo_deudas_empresas_grupo_cp",
        "pasivo_acreedores_comerciales",
        "pasivo_periodificaciones_cp",
        "pasivo_deuda_carac_especiales_cp",
    )
    def _compute_pasivo_corriente(self):
        for report in self:
            report.pasivo_corriente = (
                report.pasivo_provisiones_cp
                + report.pasivo_deudas_cp
                + report.pasivo_deudas_empresas_grupo_cp
                + report.pasivo_acreedores_comerciales
                + report.pasivo_periodificaciones_cp
                + report.pasivo_deuda_carac_especiales_cp
            )

    @api.depends("patrimonio_neto", "pasivo_no_corriente", "pasivo_corriente")
    def _compute_total_patrimonio_neto_pasivo(self):
        for report in self:
            report.total_patrimonio_neto_pasivo = (
                report.patrimonio_neto
                + report.pasivo_no_corriente
                + report.pasivo_corriente
            )

    # =====================================================================
    # COMPUTED METHODS - Profit & Loss
    # =====================================================================

    @api.depends(
        "pyg_importe_neto_cifra_negocios",
        "pyg_variacion_existencias",
        "pyg_trabajos_activo",
        "pyg_aprovisionamientos",
        "pyg_otros_ingresos_explotacion",
        "pyg_gastos_personal",
        "pyg_otros_gastos_explotacion",
        "pyg_amortizacion_inmovilizado",
        "pyg_imputacion_subvenciones",
        "pyg_excesos_provisiones",
        "pyg_deterioro_enajenacion_inmovilizado",
        "pyg_diferencia_negativa_combinaciones",
        "pyg_otros_resultados",
    )
    def _compute_pyg_resultado_explotacion(self):
        for report in self:
            report.pyg_resultado_explotacion = (
                report.pyg_importe_neto_cifra_negocios
                + report.pyg_variacion_existencias
                + report.pyg_trabajos_activo
                + report.pyg_aprovisionamientos
                + report.pyg_otros_ingresos_explotacion
                + report.pyg_gastos_personal
                + report.pyg_otros_gastos_explotacion
                + report.pyg_amortizacion_inmovilizado
                + report.pyg_imputacion_subvenciones
                + report.pyg_excesos_provisiones
                + report.pyg_deterioro_enajenacion_inmovilizado
                + report.pyg_diferencia_negativa_combinaciones
                + report.pyg_otros_resultados
            )

    @api.depends(
        "pyg_ingresos_financieros",
        "pyg_gastos_financieros",
        "pyg_variacion_valor_razonable",
        "pyg_diferencias_cambio",
        "pyg_deterioro_enajenacion_if",
        "pyg_otros_ingresos_gastos_financieros",
    )
    def _compute_pyg_resultado_financiero(self):
        for report in self:
            report.pyg_resultado_financiero = (
                report.pyg_ingresos_financieros
                + report.pyg_gastos_financieros
                + report.pyg_variacion_valor_razonable
                + report.pyg_diferencias_cambio
                + report.pyg_deterioro_enajenacion_if
                + report.pyg_otros_ingresos_gastos_financieros
            )

    @api.depends("pyg_resultado_explotacion", "pyg_resultado_financiero")
    def _compute_pyg_resultado_antes_impuestos(self):
        for report in self:
            report.pyg_resultado_antes_impuestos = (
                report.pyg_resultado_explotacion
                + report.pyg_resultado_financiero
            )

    @api.depends("pyg_resultado_antes_impuestos", "pyg_impuesto_beneficios")
    def _compute_pyg_resultado_ejercicio(self):
        for report in self:
            report.pyg_resultado_ejercicio = (
                report.pyg_resultado_antes_impuestos
                + report.pyg_impuesto_beneficios
            )

    @api.depends("pyg_resultado_ejercicio", "pyg_resultado_ops_interrumpidas")
    def _compute_pyg_resultado_ejercicio_total(self):
        for report in self:
            report.pyg_resultado_ejercicio_total = (
                report.pyg_resultado_ejercicio
                + report.pyg_resultado_ops_interrumpidas
            )

    # =====================================================================
    # COMPUTED METHODS - ECPN
    # =====================================================================

    @api.depends(
        "ecpn_resultado_pyg",
        "ecpn_ingresos_gastos_pn",
        "ecpn_transferencias_pyg",
    )
    def _compute_ecpn_total(self):
        for report in self:
            report.ecpn_total_ingresos_gastos = (
                report.ecpn_resultado_pyg
                + report.ecpn_ingresos_gastos_pn
                + report.ecpn_transferencias_pyg
            )

    @api.depends("ecpn_pn_inicio", "ecpn_ajustes")
    def _compute_ecpn_pn_inicio_ajustado(self):
        for report in self:
            report.ecpn_pn_inicio_ajustado = (
                report.ecpn_pn_inicio + report.ecpn_ajustes
            )

    @api.depends(
        "ecpn_pn_inicio_ajustado",
        "ecpn_total_ingresos_gastos",
        "ecpn_variaciones_pn",
    )
    def _compute_ecpn_pn_final(self):
        for report in self:
            report.ecpn_pn_final = (
                report.ecpn_pn_inicio_ajustado
                + report.ecpn_total_ingresos_gastos
                + report.ecpn_variaciones_pn
            )

    # =====================================================================
    # COMPUTED METHODS - EFE
    # =====================================================================

    @api.depends(
        "efe_flujos_explotacion",
        "efe_flujos_inversion",
        "efe_flujos_financiacion",
        "efe_efecto_tipo_cambio",
    )
    def _compute_efe_total(self):
        for report in self:
            report.efe_aumento_disminucion_efectivo = (
                report.efe_flujos_explotacion
                + report.efe_flujos_inversion
                + report.efe_flujos_financiacion
                + report.efe_efecto_tipo_cambio
            )

    @api.depends("efe_aumento_disminucion_efectivo", "efe_efectivo_inicio")
    def _compute_efe_efectivo_final(self):
        for report in self:
            report.efe_efectivo_final = (
                report.efe_efectivo_inicio
                + report.efe_aumento_disminucion_efectivo
            )

    # =====================================================================
    # COMPUTED METHODS - Liquidation
    # =====================================================================

    @api.depends("deduc_doble_imp_internacional", "deduc_doble_imp_interna")
    def _compute_deduc_doble_imp(self):
        for report in self:
            report.deducciones_doble_imposicion = (
                report.deduc_doble_imp_internacional
                + report.deduc_doble_imp_interna
            )

    @api.depends(
        "bonif_rentas_ceuta_melilla",
        "bonif_cooperativas",
        "bonif_otras",
    )
    def _compute_bonificaciones(self):
        for report in self:
            report.bonificaciones = (
                report.bonif_rentas_ceuta_melilla
                + report.bonif_cooperativas
                + report.bonif_otras
            )

    @api.depends(
        "corr_amortizaciones_aumento",
        "corr_deterioros_aumento",
        "corr_provisiones_aumento",
        "corr_operaciones_vinculadas_aumento",
        "corr_subvenciones_aumento",
        "corr_gastos_no_deducibles_aumento",
        "corr_otras_correcciones_aumento",
        "corr_amortizaciones_disminucion",
        "corr_deterioros_disminucion",
        "corr_provisiones_disminucion",
        "corr_operaciones_vinculadas_disminucion",
        "corr_subvenciones_disminucion",
        "corr_libertad_amortizacion_disminucion",
        "corr_reserva_capitalizacion_disminucion",
        "corr_reserva_nivelacion_disminucion",
        "corr_otras_correcciones_disminucion",
    )
    def _compute_correcciones_totales(self):
        for report in self:
            report.correcciones_aumentos = (
                report.corr_amortizaciones_aumento
                + report.corr_deterioros_aumento
                + report.corr_provisiones_aumento
                + report.corr_operaciones_vinculadas_aumento
                + report.corr_subvenciones_aumento
                + report.corr_gastos_no_deducibles_aumento
                + report.corr_otras_correcciones_aumento
            )
            report.correcciones_disminuciones = (
                report.corr_amortizaciones_disminucion
                + report.corr_deterioros_disminucion
                + report.corr_provisiones_disminucion
                + report.corr_operaciones_vinculadas_disminucion
                + report.corr_subvenciones_disminucion
                + report.corr_libertad_amortizacion_disminucion
                + report.corr_reserva_capitalizacion_disminucion
                + report.corr_reserva_nivelacion_disminucion
                + report.corr_otras_correcciones_disminucion
            )

    @api.depends(
        "deduc_idi",
        "deduc_producciones_cinematograficas",
        "deduc_creacion_empleo",
        "deduc_creacion_empleo_discapacidad",
        "deduc_donativos",
        "deduc_otras_inversiones",
    )
    def _compute_deducciones_inversiones(self):
        for report in self:
            report.deducciones_inversiones = (
                report.deduc_idi
                + report.deduc_producciones_cinematograficas
                + report.deduc_creacion_empleo
                + report.deduc_creacion_empleo_discapacidad
                + report.deduc_donativos
                + report.deduc_otras_inversiones
            )

    @api.depends(
        "resultado_contable",
        "correcciones_aumentos",
        "correcciones_disminuciones",
    )
    def _compute_base_imponible_previa(self):
        for report in self:
            report.base_imponible_previa = (
                report.resultado_contable
                + report.correcciones_aumentos
                - report.correcciones_disminuciones
            )

    @api.depends("base_imponible_previa", "compensacion_bins")
    def _compute_base_imponible(self):
        for report in self:
            report.base_imponible = (
                report.base_imponible_previa - report.compensacion_bins
            )

    @api.depends("base_imponible", "tipo_gravamen")
    def _compute_cuota_integra(self):
        for report in self:
            try:
                rate = int(report.tipo_gravamen or "25")
            except (ValueError, TypeError):
                rate = 25
            report.cuota_integra = report.base_imponible * rate / 100

    @api.depends(
        "cuota_integra",
        "deducciones_doble_imposicion",
        "bonificaciones",
    )
    def _compute_cuota_integra_ajustada(self):
        for report in self:
            report.cuota_integra_ajustada = max(
                0,
                report.cuota_integra
                - report.deducciones_doble_imposicion
                - report.bonificaciones,
            )

    @api.depends("cuota_integra_ajustada", "deducciones_inversiones")
    def _compute_cuota_liquida(self):
        for report in self:
            report.cuota_liquida = max(
                0,
                report.cuota_integra_ajustada - report.deducciones_inversiones,
            )

    @api.depends(
        "cuota_liquida",
        "retenciones_ingresos_cuenta",
        "pagos_fraccionados",
    )
    def _compute_cuota_diferencial(self):
        for report in self:
            report.cuota_diferencial = (
                report.cuota_liquida
                - report.retenciones_ingresos_cuenta
                - report.pagos_fraccionados
            )

    @api.depends("cuota_diferencial")
    def _compute_resultado_liquidacion(self):
        for report in self:
            report.resultado_liquidacion = report.cuota_diferencial

    @api.depends("resultado_liquidacion")
    def _compute_tipo_declaracion(self):
        for report in self:
            rounding = (
                report.company_id.currency_id.rounding
                if report.company_id and report.company_id.currency_id
                else 0.01
            )
            cmp = float_compare(
                report.resultado_liquidacion, 0, precision_rounding=rounding
            )
            if cmp > 0:
                report.tipo_declaracion = "I"
            elif cmp < 0:
                report.tipo_declaracion = "D"
            else:
                report.tipo_declaracion = "N"

    # =====================================================================
    # BUSINESS METHODS
    # =====================================================================

    def calculate(self):
        """Calculate all financial fields from posted account.move.line data.

        Balance sheet accounts (groups 1-5) use cumulative balances up to
        date_end.  P&L accounts (groups 6-7) use only period movements
        between date_start and date_end.
        """
        res = super().calculate()
        MapLine = self.env["l10n.es.aeat.mod200.map.line"]
        AML = self.env["account.move.line"]
        all_maps = MapLine.search([])
        cumulative_maps = all_maps.filtered("cumulative")
        period_maps = all_maps - cumulative_maps
        for report in self:
            field_values = {}
            for map_group, date_start in [
                (cumulative_maps, False),
                (period_maps, report.date_start),
            ]:
                if not map_group:
                    continue
                prefixes = list(set(map_group.mapped("account_prefix")))
                domain = [
                    ("company_id", "=", report.company_id.id),
                    ("date", "<=", report.date_end),
                    ("parent_state", "=", "posted"),
                ]
                if date_start:
                    domain.append(("date", ">=", date_start))
                prefix_domain = [
                    "|" for _ in range(len(prefixes) - 1)
                ] + [
                    ("account_id.code", "=like", f"{p}%") for p in prefixes
                ]
                domain.extend(prefix_domain)
                move_lines = AML.search(domain)
                for ml in map_group:
                    matched = move_lines.filtered(
                        lambda l, pfx=ml.account_prefix: (
                            l.account_id.code
                            and l.account_id.code.startswith(pfx)
                        )
                    )
                    if ml.balance_type == "debit-credit":
                        balance = sum(matched.mapped("debit")) - sum(
                            matched.mapped("credit")
                        )
                    else:
                        balance = sum(matched.mapped("credit")) - sum(
                            matched.mapped("debit")
                        )
                    field_values.setdefault(ml.field_name, 0.0)
                    field_values[ml.field_name] += balance * ml.sign
            valid_fields = {
                k: v
                for k, v in field_values.items()
                if k in self._fields
            }
            report.write(valid_fields)
            report.write(
                {"resultado_contable": report.pyg_resultado_ejercicio_total}
            )
            report._calculate_ecpn()
            report._calculate_efe()
        return res

    def _calculate_ecpn(self):
        """Calculate ECPN from accounting data.

        - PN at start = cumulative balance of accounts 10x-13x at date_start - 1 day
        - PyG result = already calculated as pyg_resultado_ejercicio_total
        - PN at end = cumulative balance of accounts 10x-13x at date_end
        - Income/expense recognized in PN = movements in 13x during the period
        """
        self.ensure_one()
        AML = self.env["account.move.line"]
        pn_prefixes = ["10", "11", "12", "13"]
        date_before_start = self.date_start - timedelta(days=1)

        def _pn_balance(date_limit):
            domain = [
                ("company_id", "=", self.company_id.id),
                ("date", "<=", date_limit),
                ("parent_state", "=", "posted"),
            ]
            prefix_domain = ["|" for _ in range(len(pn_prefixes) - 1)] + [
                ("account_id.code", "=like", f"{p}%") for p in pn_prefixes
            ]
            domain.extend(prefix_domain)
            lines = AML.search(domain)
            return sum(lines.mapped("credit")) - sum(lines.mapped("debit"))

        pn_inicio = _pn_balance(date_before_start)
        pn_final_contable = _pn_balance(self.date_end)

        adj_prefixes = ["13"]
        adj_domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_end),
            ("parent_state", "=", "posted"),
        ]
        adj_prefix_domain = ["|" for _ in range(len(adj_prefixes) - 1)] + [
            ("account_id.code", "=like", f"{p}%") for p in adj_prefixes
        ]
        adj_domain.extend(adj_prefix_domain)
        adj_lines = AML.search(adj_domain)
        ingresos_gastos_pn = sum(adj_lines.mapped("credit")) - sum(
            adj_lines.mapped("debit")
        )

        self.write(
            {
                "ecpn_resultado_pyg": self.pyg_resultado_ejercicio_total,
                "ecpn_ingresos_gastos_pn": ingresos_gastos_pn,
                "ecpn_pn_inicio": pn_inicio,
                "ecpn_variaciones_pn": (
                    pn_final_contable
                    - pn_inicio
                    - self.pyg_resultado_ejercicio_total
                    - ingresos_gastos_pn
                ),
            }
        )

    def _calculate_efe(self):
        """Calculate EFE (cash flow statement) using the indirect method.

        - Operating = Result + Depreciation + Impairments - Working capital changes
        - Investing = Net change in group 2 accounts
        - Financing = Net change in group 1 accounts (excl. PN = 10-13)
        - Cash start = Balance of account 57x at date_start - 1 day
        - Cash end = Balance of account 57x at date_end
        """
        self.ensure_one()
        AML = self.env["account.move.line"]
        date_before_start = self.date_start - timedelta(days=1)

        def _cumulative_balance(prefixes, date_limit, mode="debit-credit"):
            domain = [
                ("company_id", "=", self.company_id.id),
                ("date", "<=", date_limit),
                ("parent_state", "=", "posted"),
            ]
            prefix_domain = ["|" for _ in range(len(prefixes) - 1)] + [
                ("account_id.code", "=like", f"{p}%") for p in prefixes
            ]
            domain.extend(prefix_domain)
            lines = AML.search(domain)
            if mode == "debit-credit":
                return sum(lines.mapped("debit")) - sum(lines.mapped("credit"))
            return sum(lines.mapped("credit")) - sum(lines.mapped("debit"))

        efectivo_inicio = _cumulative_balance(
            ["57"], date_before_start, "debit-credit"
        )
        efectivo_final = _cumulative_balance(
            ["57"], self.date_end, "debit-credit"
        )

        grupo2_inicio = _cumulative_balance(
            ["2"], date_before_start, "debit-credit"
        )
        grupo2_final = _cumulative_balance(
            ["2"], self.date_end, "debit-credit"
        )
        flujos_inversion = -(grupo2_final - grupo2_inicio)

        financ_prefixes = ["14", "15", "16", "17", "18", "19"]
        financ_inicio = _cumulative_balance(
            financ_prefixes, date_before_start, "credit-debit"
        )
        financ_final = _cumulative_balance(
            financ_prefixes, self.date_end, "credit-debit"
        )
        flujos_financiacion = financ_final - financ_inicio

        flujos_explotacion = (
            efectivo_final
            - efectivo_inicio
            - flujos_inversion
            - flujos_financiacion
        )

        self.write(
            {
                "efe_efectivo_inicio": efectivo_inicio,
                "efe_flujos_explotacion": flujos_explotacion,
                "efe_flujos_inversion": flujos_inversion,
                "efe_flujos_financiacion": flujos_financiacion,
            }
        )

    def _get_pago_fraccionado_base(self):
        """Return the base for Model 202 fractional payment (Modality A).

        Formula: cuota_integra - deducciones - bonificaciones - retenciones
        This is the amount from which Model 202 calculates 18%.
        Ref: Art. 40.2 LIS
        """
        self.ensure_one()
        return (
            self.cuota_integra
            - self.deducciones_doble_imposicion
            - self.bonificaciones
            - self.retenciones_ingresos_cuenta
        )

    def button_confirm(self):
        for report in self:
            errors = report._get_validation_errors()
            if errors:
                raise exceptions.UserError("\n".join(errors))
        return super().button_confirm()

    def _get_validation_errors(self):
        """Return a list of validation error messages."""
        self.ensure_one()
        errors = []
        rounding = (
            self.company_id.currency_id.rounding
            if self.company_id and self.company_id.currency_id
            else 0.01
        )
        if float_compare(
            self.total_activo,
            self.total_patrimonio_neto_pasivo,
            precision_rounding=rounding,
        ):
            errors.append(
                "El balance no cuadra: Total Activo (%.2f) ≠ "
                "Total Patrimonio Neto y Pasivo (%.2f)"
                % (self.total_activo, self.total_patrimonio_neto_pasivo)
            )
        if not self.tipo_gravamen:
            errors.append("Debe seleccionar el tipo de gravamen.")
        if not self.cnae_actividad:
            errors.append("Debe informar el CNAE de la actividad principal.")
        if self.tipo_declaracion == "D" and not self.partner_bank_id:
            errors.append(
                "Para declaraciones a devolver debe indicar una cuenta bancaria."
            )
        return errors

    def _compute_error_count(self):
        for report in self:
            report.error_count = len(report._get_validation_errors())

    def _compute_allow_posting(self):
        for report in self:
            report.allow_posting = bool(report.resultado_liquidacion)

    def create_regularization_move(self):
        """Create the IS regularization journal entry.

        Mod200 does not inherit from tax.mapping, so it implements its own
        regularization move with a single line for the IS result against the
        configured counterpart account.
        """
        self.ensure_one()
        if not self.counterpart_account_id or not self.journal_id:
            return
        amount = abs(self.resultado_liquidacion)
        if not amount:
            return
        is_payable = self.resultado_liquidacion > 0
        move_vals = {
            "journal_id": self.journal_id.id,
            "date": self.date_end,
            "ref": f"Modelo 200 - {self.name}",
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": self.counterpart_account_id.id,
                        "name": f"Modelo 200 - {self.name}",
                        "debit": amount if not is_payable else 0.0,
                        "credit": amount if is_payable else 0.0,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": self.counterpart_account_id.id,
                        "name": f"Modelo 200 - {self.name}",
                        "debit": amount if is_payable else 0.0,
                        "credit": amount if not is_payable else 0.0,
                    },
                ),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()
        self.move_id = move.id
