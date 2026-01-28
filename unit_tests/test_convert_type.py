import unittest
from datetime import datetime
from migration.import_healthcare_dataset_to_mongodb import convert_type

class TestConvertType(unittest.TestCase):
    # -------------------------
    # Age -> int
    # -------------------------
    def test_age_string_to_int(self):
        result = convert_type("Age", "42")
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    def test_age_with_spaces(self):
        result = convert_type("Age", "  18 ")
        self.assertEqual(result, 18)

    def test_age_empty_string_returns_none(self):
        result = convert_type("Age", "")
        self.assertIsNone(result)

    def test_age_none_returns_none(self):
        result = convert_type("Age", None)
        self.assertIsNone(result)

    def test_age_invalid(self):
        with self.assertRaises(ValueError):
            convert_type("Age", "quarante-deux")

    # -------------------------
    # Billing Amount -> float
    # -------------------------
    def test_billing_amount_to_float(self):
        result = convert_type("Billing Amount", "1250.75")
        self.assertEqual(result, 1250.75)
        self.assertIsInstance(result, float)

    def test_billing_amount_invalid(self):
        with self.assertRaises(ValueError):
            convert_type("Billing Amount", "1250,75")

    # -------------------------
    # Date of Admission -> date
    # -------------------------
    def test_date_of_admission_to_datetime(self):
        result = convert_type("Date of Admission", "2023-01-10")
        self.assertEqual(result, datetime(2023, 1, 10))
        self.assertIsInstance(result, datetime)

    def test_date_of_admission_invalid(self):
        with self.assertRaises(ValueError):
            convert_type("Date of Admission", "10-01-2023")

    # -------------------------
    # Name -> casse normalisée
    # -------------------------
    def test_name_case_normalization(self):
        result = convert_type("Name", "  DaNnY sMitH  ")
        self.assertEqual(result, "Danny Smith")
        self.assertIsInstance(result, str)

if __name__ == "__main__":
    unittest.main()