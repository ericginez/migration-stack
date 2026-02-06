import unittest

class TestSmokeImport(unittest.TestCase):
    """Test de fumée (smoke test) du module d'import MongoDB.

    Objectif
    --------
    Vérifier que le module `import_healthcare_dataset_to_mongodb` :
    - peut être importé sans erreur
    - ne contient pas d'erreur de syntaxe
    - a toutes ses dépendances correctement installées

    Ce test ne vérifie PAS la logique métier.
    Il sert de garde-fou rapide en CI pour détecter :
    - une dépendance manquante
    - une erreur de nom de fichier ou de package
    - une erreur bloquante au chargement du module
    """

    def test_module_imports(self):
        """Le module doit pouvoir être importé sans lever d'exception."""
        # Si l'import échoue, le test échoue automatiquement
        import migration.import_healthcare_dataset_to_mongodb


if __name__ == "__main__":
    # Permet l'exécution directe du fichier de test
    unittest.main()
