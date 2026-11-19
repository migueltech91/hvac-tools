import unittest

from carga_termica.carga_termica import (
    Ambiente,
    calcular_carga,
    equipo_sugerido,
    informe,
)


class TestCargaTermica(unittest.TestCase):
    def test_dormitorio_basico(self):
        # 12 m² en clima cálido, 1 persona, sin ventanas ni equipos.
        r = calcular_carga(Ambiente(area_m2=12, personas=1))
        # (12*550 + 450) * 1.10 = 7755
        self.assertAlmostEqual(r.total_btu_h, 7755.0)
        self.assertEqual(r.equipo_sugerido_btu_h, 9000)

    def test_desglose_completo(self):
        r = calcular_carga(
            Ambiente(
                area_m2=20,
                personas=2,
                ventanas_m2=3,
                exposicion="media",
                equipos_w=400,
                clima="calido",
            )
        )
        d = r.desglose_btu_h
        self.assertAlmostEqual(d["envolvente"], 11000.0)
        self.assertAlmostEqual(d["ventanas"], 960.0)
        self.assertAlmostEqual(d["personas"], 900.0)
        self.assertAlmostEqual(d["equipos"], 1364.86, places=2)
        self.assertAlmostEqual(r.total_btu_h, r.subtotal_btu_h * 1.10)
        self.assertEqual(r.equipo_sugerido_btu_h, 18000)

    def test_altura_escala_envolvente(self):
        baja = calcular_carga(Ambiente(area_m2=10, personas=0, altura_m=2.5))
        alta = calcular_carga(Ambiente(area_m2=10, personas=0, altura_m=5.0))
        self.assertAlmostEqual(alta.total_btu_h, 2 * baja.total_btu_h)

    def test_conversiones(self):
        r = calcular_carga(Ambiente(area_m2=10, personas=0, factor_seguridad=0))
        self.assertAlmostEqual(r.total_tr, 5500 / 12000)
        self.assertAlmostEqual(r.total_kw, 5500 / 3412.142, places=4)

    def test_equipo_sugerido_limites(self):
        self.assertEqual(equipo_sugerido(9000), 9000)
        self.assertEqual(equipo_sugerido(9001), 12000)
        self.assertIsNone(equipo_sugerido(70000))

    def test_carga_grande_sin_equipo(self):
        r = calcular_carga(Ambiente(area_m2=150, personas=20))
        self.assertIsNone(r.equipo_sugerido_btu_h)
        self.assertIn("sistema central", informe(r))

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            calcular_carga(Ambiente(area_m2=0))
        with self.assertRaises(ValueError):
            calcular_carga(Ambiente(area_m2=10, clima="polar"))
        with self.assertRaises(ValueError):
            calcular_carga(Ambiente(area_m2=10, personas=-1))


if __name__ == "__main__":
    unittest.main()
