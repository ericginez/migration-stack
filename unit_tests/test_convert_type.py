import unittest
from datetime import datetime
from migration.import_healthcare_dataset_to_mongodb import convert_type

class TestConvertType(unittest.TestCase):
    """Tests unitaires de la fonction `convert_type`.

    Objectif
    --------
    Vérifier que la fonction :
    - convertit correctement les types attendus
    - gère les valeurs manquantes (None, chaînes vides)
    - lève des erreurs explicites en cas de format invalide

    Ces tests garantissent la robustesse de la phase de typage
    lors de l'import des données CSV vers MongoDB.
    """

    # =========================================================
    # Age -> int
    # =========================================================

    def test_age_string_to_int(self):
        """Une chaîne numérique valide doit être convertie en entier."""
        result = convert_type("Age", "42")
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    def test_age_with_spaces(self):
        """Les espaces superflus doivent être ignorés lors de la conversion."""
        result = convert_type("Age", "  18 ")
        self.assertEqual(result, 18)

    def test_age_empty_string_returns_none(self):
        """Une chaîne vide doit être interprétée comme une valeur manquante."""
        result = convert_type("Age", "")
        self.assertIsNone(result)

    def test_age_none_returns_none(self):
        """Une valeur None doit rester None après conversion."""
        result = convert_type("Age", None)
        self.assertIsNone(result)

    def test_age_invalid(self):
        """Une valeur non numérique doit lever une exception ValueError."""
        with self.assertRaises(ValueError):
            convert_type("Age", "quarante-deux")

    # =========================================================
    # Billing Amount -> float
    # =========================================================

    def test_billing_amount_to_float(self):
        """Un montant valide doit être converti en nombre flottant."""
        result = convert_type("Billing Amount", "1250.75")
        self.assertEqual(result, 1250.75)
        self.assertIsInstance(result, float)

    def test_billing_amount_invalid(self):
        """Un format invalide (virgule) doit lever une exception."""
        with self.assertRaises(ValueError):
            convert_type("Billing Amount", "1250,75")

    # =========================================================
    # Date of Admission -> datetime
    # =========================================================

    def test_date_of_admission_to_datetime(self):
        """Une date au format ISO (YYYY-MM-DD) doit être convertie en datetime."""
        result = convert_type("Date of Admission", "2023-01-10")
        self.assertEqual(result, datetime(2023, 1, 10))
        self.assertIsInstance(result, datetime)

    def test_date_of_admission_invalid(self):
        """Un format de date invalide doit lever une exception."""
        with self.assertRaises(ValueError):
            convert_type("Date of Admission", "10-01-2023")

    # =========================================================
    # Name -> normalisation de la casse
    # =========================================================

    def test_name_case_normalization(self):
        """Le nom doit être nettoyé et normalisé (Title Case)."""
        result = convert_type("Name", "  DaNnY sMitH  ")
        self.assertEqual(result, "Danny Smith")
        self.assertIsInstance(result, str)


# Lancement du main
if __name__ == "__main__":
    unittest.main()
