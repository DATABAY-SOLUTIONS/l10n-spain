# Copyright 2025 OCA - Odoo Community Association
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
from odoo.tests.common import TransactionCase


class TestL10nEsAeatMod202(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env.user.company_id = cls.company

    def _create_report(self, modalidad="A", **kwargs):
        vals = {
            "company_id": self.company.id,
            "year": 2025,
            "period_type": "1P",
            "date_start": "2025-01-01",
            "date_end": "2025-03-31",
            "liquidacion_modalidad": modalidad,
        }
        vals.update(kwargs)
        return self.env["l10n.es.aeat.mod202.report"].create(vals)

    def test_modalidad_a_basic(self):
        """Test Modality A: simple 18% of last IS quota."""
        report = self._create_report(
            modalidad="A",
            casilla_01=5000.0,
        )
        self.assertEqual(report.casilla_03, 5000.0)
        self.assertEqual(report.tipo_declaracion, "I")

    def test_modalidad_a_complementaria(self):
        """Test Modality A: complementary declaration."""
        report = self._create_report(
            modalidad="A",
            casilla_01=5000.0,
            casilla_02=3000.0,
        )
        self.assertEqual(report.casilla_03, 2000.0)

    def test_modalidad_a_negative(self):
        """Test Modality A: negative result."""
        report = self._create_report(
            modalidad="A",
            casilla_01=0.0,
        )
        self.assertEqual(report.casilla_03, 0.0)
        self.assertEqual(report.tipo_declaracion, "N")

    def test_modalidad_b_general(self):
        """Test Modality B: single percentage (B1)."""
        report = self._create_report(
            modalidad="B",
            casilla_04=100000.0,
            casilla_17_pct=24.0,
            casilla_29_pct=100.0,
        )
        self.assertEqual(report.casilla_13, 100000.0)
        self.assertAlmostEqual(report.casilla_17_base, 100000.0, places=2)
        self.assertAlmostEqual(report.casilla_20, 24000.0, places=2)
        self.assertAlmostEqual(report.casilla_32, 24000.0, places=2)

    def test_modalidad_b_with_corrections(self):
        """Test Modality B: with corrections to accounting result."""
        report = self._create_report(
            modalidad="B",
            casilla_04=100000.0,
            casilla_05=5000.0,
            casilla_06=2000.0,
            casilla_08=3000.0,
            casilla_09=1000.0,
            casilla_17_pct=24.0,
            casilla_29_pct=100.0,
        )
        self.assertEqual(report.casilla_38, 8000.0)
        self.assertEqual(report.casilla_39, 3000.0)
        self.assertEqual(report.casilla_13, 105000.0)

    def test_modalidad_b_minimo_ingresar(self):
        """Test Modality B: minimum payment for CN >= 10M."""
        report = self._create_report(
            modalidad="B",
            casilla_04=100000.0,
            casilla_17_pct=24.0,
            casilla_29_pct=100.0,
            cn_tramo="1",
            casilla_33=30000.0,
        )
        self.assertAlmostEqual(report.casilla_34, 30000.0, places=2)

    def test_modalidad_b_multiples_porcentajes(self):
        """Test Modality B: multiple percentages (B2)."""
        report = self._create_report(
            modalidad="B",
            casilla_04=100000.0,
            use_b2=True,
            b2_tramo1_base=60000.0,
            b2_tramo1_pct=20.0,
            b2_tramo2_base=40000.0,
            b2_tramo2_pct=25.0,
            casilla_29_pct=100.0,
        )
        self.assertAlmostEqual(report.b2_tramo1_resultado, 12000.0, places=2)
        self.assertAlmostEqual(report.b2_tramo1_acumulado, 12000.0, places=2)
        self.assertAlmostEqual(report.b2_tramo2_resultado, 10000.0, places=2)
        self.assertAlmostEqual(report.b2_tramo2_acumulado, 22000.0, places=2)
        self.assertAlmostEqual(report.b2_resultado_previo, 22000.0, places=2)
        self.assertAlmostEqual(report.casilla_32, 22000.0, places=2)

    def test_total_correcciones_compute(self):
        """Test that total corrections are correctly computed."""
        report = self._create_report(
            modalidad="B",
            casilla_04=50000.0,
            casilla_05=1000.0,
            casilla_06=500.0,
            casilla_07=200.0,
            casilla_37=300.0,
            casilla_08=2000.0,
            casilla_09=100.0,
        )
        self.assertEqual(report.casilla_38, 3000.0)
        self.assertEqual(report.casilla_39, 1100.0)

    def test_calculate_b_percentage(self):
        """Test auto-calculation of B1 percentage from tipo_gravamen."""
        report = self._create_report(
            modalidad="B",
            casilla_04=100000.0,
            tipo_gravamen="25",
        )
        report.calculate()
        self.assertGreater(report.casilla_17_pct, 0)
