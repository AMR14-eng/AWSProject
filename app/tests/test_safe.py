"""
Tests SEGUROS para CI - Sin ejecutar código AWS durante importación
"""
import unittest
import sys
import os

# Configurar environment ANTES de cualquier import
os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['AWS_ACCESS_KEY_ID'] = 'test-key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret'

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class SafeTests(unittest.TestCase):
    """Tests que no ejecutan código AWS al importar"""
    
    def test_1_basic_import(self):
        """Test que Flask se puede importar"""
        try:
            import flask
            print("✅ Flask imported")
            success = True
        except ImportError:
            success = False
        self.assertTrue(success)
    
    def test_2_app_structure(self):
        """Test que los archivos esenciales existen"""
        files = [
            'app/__init__.py',
            'app/auth.py',
            'app/config.py',
            'app/models.py',
            'requirements.txt',
            '.github/workflows/ci-cd.yml',
            'app/Dockerfile'
        ]
        
        for file in files:
            exists = os.path.exists(file)
            self.assertTrue(exists, f"Missing: {file}")
            if exists:
                print(f"✅ {file} exists")
    
    def test_3_ci_cd_configuration(self):
        """Test que el pipeline CI/CD está configurado"""
        # Verificar workflow file
        workflow_path = '.github/workflows/ci-cd.yml'
        self.assertTrue(os.path.exists(workflow_path))
        
        with open(workflow_path, 'r') as f:
            content = f.read()
            self.assertIn('name: CI/CD Pipeline', content)
            self.assertIn('pull_request', content)
            self.assertIn('docker build', content)
        
        print("✅ CI/CD pipeline configured correctly")
    
    def test_4_dockerfile_valid(self):
        """Test que Dockerfile es válido"""
        dockerfile = 'app/Dockerfile'
        self.assertTrue(os.path.exists(dockerfile))
        
        with open(dockerfile, 'r') as f:
            content = f.read()
            self.assertIn('FROM python', content)
            self.assertIn('EXPOSE 5000', content)
        
        print("✅ Dockerfile is valid")

if __name__ == '__main__':
    unittest.main()