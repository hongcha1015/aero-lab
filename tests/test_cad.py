import unittest
from pathlib import Path

from aero_lab.cad.adapters import CadImportRequest, supported_cad_extensions, validate_cad_import


class CadImportPlaceholderTests(unittest.TestCase):
    def test_supported_extensions_include_common_mesh_and_cad_formats(self) -> None:
        extensions = supported_cad_extensions()
        self.assertIn(".stl", extensions)
        self.assertIn(".obj", extensions)
        self.assertIn(".step", extensions)
        self.assertIn(".glb", extensions)

    def test_validate_rejects_unknown_extension(self) -> None:
        with self.assertRaises(ValueError):
            validate_cad_import(CadImportRequest(Path("wing.txt")))


if __name__ == "__main__":
    unittest.main()
