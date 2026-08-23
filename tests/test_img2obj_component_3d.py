"""
🧪 Unit Test Suite for img2obj Electronic Component 3D Modeling Tool.
"""

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.abspath("."))

from tools.img2obj_component_3d_tool import (
    generate_3d_part_from_image_or_spec,
    attach_3d_model_to_kicad_footprint,
    preview_3d_component_threejs
)


class TestImg2ObjComponent3D(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_3d_models_")

    def test_generate_smd_0805_obj(self):
        res = generate_3d_part_from_image_or_spec.invoke({
            "package_or_image": "0805",
            "output_name": "resistor_0805",
            "output_dir": self.temp_dir
        })
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["data"]["obj_path"]))
        self.assertTrue(os.path.exists(res["data"]["mtl_path"]))
        self.assertTrue(os.path.exists(res["data"]["threejs_path"]))
        self.assertGreater(res["data"]["vertices_count"], 0)
        self.assertGreater(res["data"]["faces_count"], 0)

        # Inspect OBJ file structure
        with open(res["data"]["obj_path"], "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("v ", content)
        self.assertIn("f ", content)
        self.assertIn("usemtl Leads_Matte_Tin", content)

    def test_generate_sot223_regulator(self):
        res = generate_3d_part_from_image_or_spec.invoke({
            "package_or_image": "SOT-223",
            "output_name": "regulator_ams1117",
            "output_dir": self.temp_dir
        })
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["data"]["vertices_count"], 20)

    def test_generate_qfp48_microcontroller(self):
        res = generate_3d_part_from_image_or_spec.invoke({
            "package_or_image": "QFP-48",
            "output_name": "stm32_qfp48",
            "output_dir": self.temp_dir
        })
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["data"]["faces_count"], 50)

    def test_generate_usb_c_connector(self):
        res = generate_3d_part_from_image_or_spec.invoke({
            "package_or_image": "USB-C",
            "output_name": "type_c_receptacle",
            "output_dir": self.temp_dir
        })
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["data"]["obj_path"]))

    def test_preview_threejs_factory(self):
        res = preview_3d_component_threejs.invoke({
            "package_name": "SOT-223"
        })
        self.assertEqual(res["status"], "success")
        self.assertIn("createPartMesh", res["data"]["threejs_source"])
        self.assertIn("THREE.MeshStandardMaterial", res["data"]["threejs_source"])

    def test_attach_3d_model_to_kicad_footprint(self):
        # Create a mock .kicad_pcb file
        mock_pcb = os.path.join(self.temp_dir, "test_board.kicad_pcb")
        with open(mock_pcb, "w", encoding="utf-8") as f:
            f.write("""(kicad_pcb (version 20221018) (generator pcbnew)
  (footprint "Package_TO_SOT_SMD:SOT-223-3_TabPin2" (layer "F.Cu")
    (fp_text reference "U1" (at 0 -4.5) (layer "F.SilkS"))
    (fp_text value "AMS1117-3.3" (at 0 4.5) (layer "F.Fab"))
  )
)""")
        
        obj_file = os.path.join(self.temp_dir, "regulator_ams1117.obj")
        res = attach_3d_model_to_kicad_footprint.invoke({
            "pcb_file_path": mock_pcb,
            "reference_designator": "U1",
            "model_obj_path": obj_file
        })
        self.assertEqual(res["status"], "success")
        
        # Verify content was injected
        with open(mock_pcb, "r", encoding="utf-8") as f:
            updated = f.read()
        self.assertIn('(model "', updated)
        self.assertIn("regulator_ams1117.obj", updated)


if __name__ == "__main__":
    unittest.main()
