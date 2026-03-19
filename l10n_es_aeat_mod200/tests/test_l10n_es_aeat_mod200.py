# Copyright 2025 Databay Solutions
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestL10nEsAeatMod200(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.vat = "ESA12345674"
        cls.report_model = cls.env["l10n.es.aeat.mod200.report"]
        cls.report = cls.report_model.create(
            {
                "company_id": cls.company.id,
                "company_vat": "A12345674",
                "year": 2024,
                "period_type": "0A",
                "date_start": "2024-01-01",
                "date_end": "2024-12-31",
                "cnae_actividad": "6201",
                "tipo_gravamen": "25",
            }
        )

    # ---------------------------------------------------------------
    # Balance sheet computed totals
    # ---------------------------------------------------------------

    def test_balance_totals(self):
        """Total activo = activo no corriente + activo corriente."""
        self.report.write(
            {
                "activo_inmovilizado_intangible": 10000,
                "activo_inmovilizado_material": 50000,
                "activo_efectivo": 20000,
                "activo_deudores_comerciales": 5000,
            }
        )
        self.assertEqual(self.report.activo_no_corriente, 60000)
        self.assertEqual(self.report.activo_corriente, 25000)
        self.assertEqual(self.report.total_activo, 85000)

    def test_pasivo_totals(self):
        """Total PN + pasivo = patrimonio_neto + pasivo_nc + pasivo_c."""
        self.report.write(
            {
                "pn_capital": 50000,
                "pn_reservas": 10000,
                "pasivo_deudas_lp": 20000,
                "pasivo_acreedores_comerciales": 5000,
            }
        )
        self.assertEqual(self.report.patrimonio_neto, 60000)
        self.assertEqual(self.report.pasivo_no_corriente, 20000)
        self.assertEqual(self.report.pasivo_corriente, 5000)
        self.assertEqual(self.report.total_patrimonio_neto_pasivo, 85000)

    def test_balance_equilibrium(self):
        """Activo should equal PN + Pasivo when properly filled."""
        self.report.write(
            {
                "activo_inmovilizado_material": 50000,
                "activo_efectivo": 35000,
                "pn_capital": 60000,
                "pn_reservas": 5000,
                "pasivo_deudas_lp": 20000,
            }
        )
        self.assertEqual(self.report.total_activo, 85000)
        self.assertEqual(self.report.total_patrimonio_neto_pasivo, 85000)

    # ---------------------------------------------------------------
    # P&L computed totals
    # ---------------------------------------------------------------

    def test_pyg_resultado_explotacion(self):
        """Operating result = sum of revenue - expenses."""
        self.report.write(
            {
                "pyg_importe_neto_cifra_negocios": 100000,
                "pyg_aprovisionamientos": -40000,
                "pyg_gastos_personal": -30000,
                "pyg_otros_gastos_explotacion": -10000,
                "pyg_amortizacion_inmovilizado": -5000,
            }
        )
        self.assertEqual(self.report.pyg_resultado_explotacion, 15000)

    def test_pyg_resultado_ejercicio(self):
        """Full P&L chain: exploitation + financial - tax = result."""
        self.report.write(
            {
                "pyg_importe_neto_cifra_negocios": 100000,
                "pyg_aprovisionamientos": -40000,
                "pyg_gastos_personal": -30000,
                "pyg_ingresos_financieros": 2000,
                "pyg_gastos_financieros": -1000,
                "pyg_impuesto_beneficios": -7750,
            }
        )
        self.assertEqual(self.report.pyg_resultado_explotacion, 30000)
        self.assertEqual(self.report.pyg_resultado_financiero, 1000)
        self.assertEqual(self.report.pyg_resultado_antes_impuestos, 31000)
        self.assertEqual(self.report.pyg_resultado_ejercicio, 23250)
        self.assertEqual(self.report.pyg_resultado_ejercicio_total, 23250)

    # ---------------------------------------------------------------
    # Corrections detail -> total
    # ---------------------------------------------------------------

    def test_correcciones_totales(self):
        """Correction totals = sum of individual correction fields."""
        self.report.write(
            {
                "corr_amortizaciones_aumento": 5000,
                "corr_gastos_no_deducibles_aumento": 3000,
                "corr_otras_correcciones_aumento": 2000,
                "corr_libertad_amortizacion_disminucion": 4000,
                "corr_reserva_capitalizacion_disminucion": 1000,
            }
        )
        self.assertEqual(self.report.correcciones_aumentos, 10000)
        self.assertEqual(self.report.correcciones_disminuciones, 5000)

    # ---------------------------------------------------------------
    # Deductions detail -> total
    # ---------------------------------------------------------------

    def test_deducciones_inversiones_total(self):
        """Deduction total = sum of individual deduction fields."""
        self.report.write(
            {
                "deduc_idi": 2000,
                "deduc_donativos": 500,
            }
        )
        self.assertEqual(self.report.deducciones_inversiones, 2500)

    def test_deduc_doble_imposicion(self):
        """Double imposition deductions total."""
        self.report.write(
            {
                "deduc_doble_imp_internacional": 1000,
                "deduc_doble_imp_interna": 500,
            }
        )
        self.assertEqual(self.report.deducciones_doble_imposicion, 1500)

    def test_bonificaciones_total(self):
        """Bonificaciones total."""
        self.report.write(
            {
                "bonif_rentas_ceuta_melilla": 200,
                "bonif_cooperativas": 100,
                "bonif_otras": 50,
            }
        )
        self.assertEqual(self.report.bonificaciones, 350)

    # ---------------------------------------------------------------
    # Liquidation chain
    # ---------------------------------------------------------------

    def test_liquidacion_general(self):
        """Full liquidation: result -> base -> cuota -> diferencial."""
        self.report.write({"resultado_contable": 50000})
        self.assertEqual(self.report.base_imponible_previa, 50000)
        self.assertEqual(self.report.base_imponible, 50000)
        self.assertEqual(self.report.cuota_integra, 12500)
        self.assertEqual(self.report.cuota_integra_ajustada, 12500)
        self.assertEqual(self.report.cuota_liquida, 12500)
        self.assertEqual(self.report.cuota_diferencial, 12500)
        self.assertEqual(self.report.tipo_declaracion, "I")

    def test_liquidacion_con_retenciones(self):
        """Retenciones > cuota -> resultado negativo (a devolver)."""
        self.report.write(
            {
                "resultado_contable": 10000,
                "retenciones_ingresos_cuenta": 5000,
            }
        )
        self.assertEqual(self.report.cuota_integra, 2500)
        self.assertEqual(self.report.cuota_diferencial, -2500)
        self.assertEqual(self.report.tipo_declaracion, "D")

    def test_liquidacion_cuota_cero(self):
        """Zero result -> tipo N."""
        self.report.write({"resultado_contable": 0})
        self.assertEqual(self.report.resultado_liquidacion, 0)
        self.assertEqual(self.report.tipo_declaracion, "N")

    def test_liquidacion_with_corrections(self):
        """Corrections flow through to base imponible."""
        self.report.write(
            {
                "resultado_contable": 100000,
                "corr_gastos_no_deducibles_aumento": 5000,
                "corr_libertad_amortizacion_disminucion": 10000,
            }
        )
        self.assertEqual(self.report.correcciones_aumentos, 5000)
        self.assertEqual(self.report.correcciones_disminuciones, 10000)
        self.assertEqual(self.report.base_imponible_previa, 95000)

    # ---------------------------------------------------------------
    # Pago fraccionado base
    # ---------------------------------------------------------------

    def test_pago_fraccionado_base(self):
        """_get_pago_fraccionado_base returns correct base for mod202."""
        self.report.write(
            {
                "resultado_contable": 100000,
                "deduc_doble_imp_internacional": 1000,
                "bonif_otras": 500,
                "retenciones_ingresos_cuenta": 2000,
            }
        )
        expected = self.report.cuota_integra - 1500 - 500 - 2000
        self.assertEqual(self.report._get_pago_fraccionado_base(), expected)

    # ---------------------------------------------------------------
    # ECPN & EFE computed totals
    # ---------------------------------------------------------------

    def test_ecpn_totals(self):
        """ECPN final = inicio_ajustado + ingresos_gastos + variaciones."""
        self.report.write(
            {
                "ecpn_resultado_pyg": 50000,
                "ecpn_ingresos_gastos_pn": 5000,
                "ecpn_transferencias_pyg": -2000,
                "ecpn_pn_inicio": 100000,
                "ecpn_ajustes": -3000,
                "ecpn_variaciones_pn": 10000,
            }
        )
        self.assertEqual(self.report.ecpn_total_ingresos_gastos, 53000)
        self.assertEqual(self.report.ecpn_pn_inicio_ajustado, 97000)
        self.assertEqual(self.report.ecpn_pn_final, 160000)

    def test_efe_totals(self):
        """EFE final = inicio + (explotacion + inversion + financiacion + tc)."""
        self.report.write(
            {
                "efe_flujos_explotacion": 30000,
                "efe_flujos_inversion": -15000,
                "efe_flujos_financiacion": -5000,
                "efe_efecto_tipo_cambio": 0,
                "efe_efectivo_inicio": 20000,
            }
        )
        self.assertEqual(self.report.efe_aumento_disminucion_efectivo, 10000)
        self.assertEqual(self.report.efe_efectivo_final, 30000)

    # ---------------------------------------------------------------
    # allow_posting
    # ---------------------------------------------------------------

    def test_allow_posting(self):
        """allow_posting is True when resultado_liquidacion is non-zero."""
        self.report.write({"resultado_contable": 10000})
        self.assertTrue(self.report.allow_posting)
        self.report.write({"resultado_contable": 0})
        self.assertFalse(self.report.allow_posting)

    # ---------------------------------------------------------------
    # Validations
    # ---------------------------------------------------------------

    def test_validation_balance_mismatch(self):
        """Validation error when balance doesn't square."""
        self.report.write(
            {
                "activo_inmovilizado_material": 100000,
                "pn_capital": 50000,
            }
        )
        errors = self.report._get_validation_errors()
        self.assertTrue(any("balance" in e.lower() for e in errors))

    def test_validation_no_cnae(self):
        """Validation error when CNAE is missing."""
        self.report.write({"cnae_actividad": False})
        errors = self.report._get_validation_errors()
        self.assertTrue(any("CNAE" in e for e in errors))

    def test_validation_devolver_no_bank(self):
        """Validation error for devolver without bank account."""
        self.report.write(
            {
                "resultado_contable": -10000,
                "retenciones_ingresos_cuenta": 20000,
            }
        )
        self.assertEqual(self.report.tipo_declaracion, "D")
        errors = self.report._get_validation_errors()
        self.assertTrue(any("cuenta bancaria" in e for e in errors))

    def test_error_count(self):
        """Error count reflects number of validation errors."""
        self.report.write(
            {
                "cnae_actividad": False,
                "activo_inmovilizado_material": 100000,
                "pn_capital": 50000,
            }
        )
        self.assertGreater(self.report.error_count, 0)

    # ---------------------------------------------------------------
    # Administrators
    # ---------------------------------------------------------------

    def test_admin_creation(self):
        """Admins can be created and linked to the report."""
        admin = self.env["l10n.es.aeat.mod200.admin"].create(
            {
                "report_id": self.report.id,
                "vat": "12345678A",
                "name": "Test Admin",
                "person_type": "F",
                "position_type": "05",
            }
        )
        self.assertIn(admin, self.report.admin_ids)

    # ---------------------------------------------------------------
    # Type of annual accounts
    # ---------------------------------------------------------------

    def test_tipo_cuentas_anuales_default(self):
        """Default tipo_cuentas_anuales is PYMES."""
        self.assertEqual(self.report.tipo_cuentas_anuales, "P")
