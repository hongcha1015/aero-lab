import unittest

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

if np is not None:
    from aero_lab.calc.airfoil import (
        AirfoilSettings,
        average_skin_friction_coefficient,
        airfoil_outline,
        boundary_layer_thickness,
        drag_force,
        estimate_coefficients,
        flow_regime,
        flow_field,
        reynolds_number,
    )


@unittest.skipIf(np is None, "numpy optional dependency is not installed")
class AirfoilModelTests(unittest.TestCase):
    def test_lift_increases_with_angle_of_attack(self) -> None:
        low = estimate_coefficients(AirfoilSettings(shape_model="wing", angle_of_attack_degrees=0.0))
        high = estimate_coefficients(AirfoilSettings(shape_model="wing", angle_of_attack_degrees=10.0))
        self.assertGreater(high.lift_coefficient, low.lift_coefficient)

    def test_rear_wing_setting_increases_drag(self) -> None:
        clean = estimate_coefficients(AirfoilSettings(shape_model="wing", rear_wing_degrees=0.0))
        loaded = estimate_coefficients(AirfoilSettings(shape_model="wing", rear_wing_degrees=25.0))
        self.assertGreater(loaded.drag_coefficient, clean.drag_coefficient)

    def test_simple_body_ignores_wing_lift_controls(self) -> None:
        clean = estimate_coefficients(AirfoilSettings(shape_model="simple_body"))
        loaded = estimate_coefficients(
            AirfoilSettings(shape_model="simple_body", angle_of_attack_degrees=14.0, rear_wing_degrees=35.0)
        )

        self.assertEqual(clean.lift_coefficient, 0.0)
        self.assertEqual(loaded.lift_coefficient, 0.0)
        self.assertEqual(loaded.circulation_m2_s, 0.0)
        self.assertAlmostEqual(clean.pressure_drag_coefficient, loaded.pressure_drag_coefficient)

    def test_drag_uses_frontal_area_and_dynamic_pressure(self) -> None:
        settings = AirfoilSettings(wind_speed=40.0, air_density=1.2, frontal_area=0.5)
        self.assertAlmostEqual(drag_force(settings, 0.8), 0.5 * 1.2 * 40.0 * 40.0 * 0.5 * 0.8)

    def test_total_drag_is_skin_friction_plus_pressure_drag(self) -> None:
        coefficients = estimate_coefficients(AirfoilSettings(body_width=1.2, body_height=0.18, body_length=1.6))

        self.assertAlmostEqual(
            coefficients.drag_newtons,
            coefficients.skin_friction_drag_newtons + coefficients.pressure_drag_newtons,
        )
        self.assertGreater(coefficients.skin_friction_coefficient, 0.0)
        self.assertGreater(coefficients.pressure_drag_coefficient, 0.0)
        self.assertAlmostEqual(coefficients.frontal_area_m2, 1.2 * 0.18)

    def test_flow_field_masks_airfoil_body(self) -> None:
        field = flow_field(AirfoilSettings(), x_points=28, y_points=18)
        self.assertEqual(field["u"].shape, (18, 28))
        self.assertTrue(np.isnan(field["u"]).any())

    def test_airfoil_outline_is_closed_shape_points(self) -> None:
        x, y = airfoil_outline(AirfoilSettings(), points=50)
        self.assertEqual(len(x), 100)
        self.assertEqual(len(y), 100)

    def test_reynolds_number_and_boundary_layer_are_computed(self) -> None:
        settings = AirfoilSettings(wind_speed=50.0, chord=1.2, air_density=1.225, dynamic_viscosity=1.81e-5)
        reynolds = reynolds_number(settings)
        laminar, turbulent = boundary_layer_thickness(settings, reynolds)
        coefficients = estimate_coefficients(settings)

        self.assertAlmostEqual(reynolds, 1.225 * 50.0 * 1.2 / 1.81e-5)
        self.assertGreater(laminar, 0.0)
        self.assertGreater(turbulent, laminar)
        self.assertAlmostEqual(coefficients.reynolds_number, reynolds)

    def test_flow_regime_follows_external_flow_reynolds_thresholds(self) -> None:
        self.assertEqual(flow_regime(100_000), "laminar")
        self.assertEqual(flow_regime(1_000_000), "transitional")
        self.assertEqual(flow_regime(4_000_000), "turbulent")

    def test_skin_friction_is_higher_for_turbulent_flow_than_laminar_fit_at_same_reynolds(self) -> None:
        self.assertGreater(average_skin_friction_coefficient(4_000_000), 1.328 / np.sqrt(4_000_000))


if __name__ == "__main__":
    unittest.main()
