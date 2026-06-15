import unittest

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

if np is not None:
    from aero_lab.calc.airfoil import AirfoilSettings, airfoil_outline, estimate_coefficients, flow_field


@unittest.skipIf(np is None, "numpy optional dependency is not installed")
class AirfoilModelTests(unittest.TestCase):
    def test_lift_increases_with_angle_of_attack(self) -> None:
        low = estimate_coefficients(AirfoilSettings(angle_of_attack_degrees=0.0))
        high = estimate_coefficients(AirfoilSettings(angle_of_attack_degrees=10.0))
        self.assertGreater(high.lift_coefficient, low.lift_coefficient)

    def test_rear_wing_setting_increases_drag(self) -> None:
        clean = estimate_coefficients(AirfoilSettings(rear_wing_degrees=0.0))
        loaded = estimate_coefficients(AirfoilSettings(rear_wing_degrees=25.0))
        self.assertGreater(loaded.drag_coefficient, clean.drag_coefficient)

    def test_flow_field_masks_airfoil_body(self) -> None:
        field = flow_field(AirfoilSettings(), x_points=28, y_points=18)
        self.assertEqual(field["u"].shape, (18, 28))
        self.assertTrue(np.isnan(field["u"]).any())

    def test_airfoil_outline_is_closed_shape_points(self) -> None:
        x, y = airfoil_outline(AirfoilSettings(), points=50)
        self.assertEqual(len(x), 100)
        self.assertEqual(len(y), 100)


if __name__ == "__main__":
    unittest.main()
