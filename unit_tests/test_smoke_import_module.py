import unittest

class TestSmokeImport(unittest.TestCase):
    def test_module_imports(self):
        # Vérifie que le module s'importe (syntaxe ok, dépendances ok)
        import migration.import_healthcare_dataset_to_mongodb

if __name__ == "__main__":
    unittest.main()