import unittest

from psicrometria.psicrometria import (
    estado_desde_bulbo_humedo,
    estado_desde_hr,
    presion_por_altitud,
    presion_saturacion,
)


class TestPsicrometria(unittest.TestCase):
    def test_presion_saturacion_tablas_ashrae(self):
        # Valores de tabla (kPa). Hyland-Wexler difiere < 0,05 % de IAPWS.
        self.assertAlmostEqual(presion_saturacion(0.01), 0.6117, delta=0.0005)
        self.assertAlmostEqual(presion_saturacion(25), 3.1699, delta=0.0015)
        self.assertAlmostEqual(presion_saturacion(100), 101.42, delta=0.05)
        self.assertAlmostEqual(presion_saturacion(-10), 0.2599, delta=0.0005)

    def test_presion_por_altitud(self):
        self.assertAlmostEqual(presion_por_altitud(0), 101.325)
        self.assertAlmostEqual(presion_por_altitud(1500), 84.556, places=2)

    def test_estado_25c_50hr(self):
        e = estado_desde_hr(25, 50)
        self.assertAlmostEqual(e.w_g_kg, 9.88, places=1)
        self.assertAlmostEqual(e.entalpia_kj_kg, 50.3, places=0)
        self.assertAlmostEqual(e.rocio_c, 13.9, delta=0.1)
        self.assertAlmostEqual(e.tbh_c, 17.9, delta=0.15)
        self.assertAlmostEqual(e.volumen_m3_kg, 0.858, places=3)
        self.assertAlmostEqual(e.densidad_kg_m3, 1.177, places=2)

    def test_saturado_coincide_rocio_y_bulbos(self):
        e = estado_desde_hr(20, 100)
        self.assertAlmostEqual(e.rocio_c, 20, places=3)
        self.assertAlmostEqual(e.tbh_c, 20, places=3)

    def test_ida_y_vuelta_hr_bulbo_humedo(self):
        e1 = estado_desde_hr(32, 40)
        e2 = estado_desde_bulbo_humedo(32, e1.tbh_c)
        self.assertAlmostEqual(e2.hr_pct, 40, places=2)
        self.assertAlmostEqual(e2.w_kg_kg, e1.w_kg_kg, places=6)

    def test_altitud_aumenta_humedad_absoluta(self):
        mar = estado_desde_hr(25, 50)
        altura = estado_desde_hr(25, 50, presion_por_altitud(2000))
        self.assertGreater(altura.w_kg_kg, mar.w_kg_kg)
        self.assertLess(altura.densidad_kg_m3, mar.densidad_kg_m3)

    def test_bajo_cero(self):
        e = estado_desde_hr(-5, 80)
        self.assertLess(e.rocio_c, -5)
        self.assertLess(e.tbh_c, -5 + 1e-9)

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            estado_desde_hr(25, 120)
        with self.assertRaises(ValueError):
            estado_desde_bulbo_humedo(20, 25)
        with self.assertRaises(ValueError):
            presion_saturacion(300)


if __name__ == "__main__":
    unittest.main()
