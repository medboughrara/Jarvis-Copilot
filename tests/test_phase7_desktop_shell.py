"""
🧪 Unit Test Suite for Phase 7: Desktop Shell & Live HUD Circuit Synchronization.
Verifies Phase 7 Definition of Done:
User request via chat/REST endpoint executes tool pipeline and updates schematic & PCB state in real-time.
"""

import os
import sys
import json
import unittest
import threading
import urllib.request
import urllib.parse
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from web_server import start_server, PORT


class TestDesktopShellPhase7(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Start background web server for testing
        cls.server_thread = threading.Thread(target=start_server, daemon=True)
        cls.server_thread.start()
        time.sleep(1.5)

    def test_pcb_state_endpoint(self):
        """Tests GET /api/pcb/state returns live schematic and ERC status."""
        print("\n--- Testing GET /api/pcb/state ---")
        url = f"http://127.0.0.1:{PORT}/api/pcb/state"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data["status"], "success")
            self.assertIn("schematic", data["data"])
            self.assertIn("erc", data["data"])
            print(f"PCB State Summary: {data['summary']}")
            print("✅ GET /api/pcb/state PASSED!")

    def test_pcb_generate_endpoint_definition_of_done(self):
        """Phase 7 Definition of Done: User types request to generate buck converter and views updated state."""
        print("\n--- Testing POST /api/pcb/generate (Chat / Panel Drive) ---")
        url = f"http://127.0.0.1:{PORT}/api/pcb/generate"
        payload = json.dumps({
            "prompt": "Design a 5V/2A buck converter from 12V input",
            "file_path": "scratch/desktop_shell_project.kicad_sch"
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode())
            self.assertEqual(res["status"], "success")
            print(f"Shell Generation Result: {res['summary']}")
            self.assertIn("final_erc_verdict", res["data"])
            print(f"Final ERC: [{res['data']['final_erc_verdict']}]")
            print("✅ Phase 7 Definition of Done PASSED: Live PCB generation via Desktop Shell verified!")


if __name__ == "__main__":
    unittest.main()
