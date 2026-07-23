import tempfile
import unittest
from pathlib import Path

from repair_event_pack.core import PackError, build_pack, verify_pack


class RepairPackTests(unittest.TestCase):
    CSV = "event_date,event_name,item_id,item_category,brand,model,approx_age,fault,assessment,outcome,outcome_note\n2026-07-23,Demo Fix Day,R-001,Lamp,Acme,L1,4,No power,Loose wire,fixed,Reconnected wire\n2026-07-23,Demo Fix Day,R-002,Laptop,Byte,Air,7,Won't boot,Needs part,repairable,Return with part\n"

    def test_build_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "records.csv"
            out = root / "pack"
            source.write_text(self.CSV, encoding="utf-8")
            record = build_pack(source, out, {"data_provider": "Demo Group"})
            self.assertEqual(len(record["rows"]), 2)
            self.assertEqual(verify_pack(out), [])
            self.assertIn("repair_status", (out / "open-repair-data.csv").read_text(encoding="utf-8"))

    def test_duplicate_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "records.csv"
            source.write_text(self.CSV.replace("R-002", "R-001"), encoding="utf-8")
            with self.assertRaises(PackError):
                build_pack(source, Path(tmp) / "pack")

    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "records.csv"
            out = root / "pack"
            source.write_text(self.CSV, encoding="utf-8")
            build_pack(source, out)
            (out / "index.html").write_text("changed", encoding="utf-8")
            (out / "inspection.json").write_text("{}\n", encoding="utf-8")
            self.assertTrue(verify_pack(out))


if __name__ == "__main__":
    unittest.main()
