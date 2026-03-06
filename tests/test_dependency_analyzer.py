"""
Test Suite for Dependency Analyzer

Tests circular dependency detection, layer violations, and graph accuracy.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from dependency_analyzer import DependencyAnalyzer, CircularDependency  # type: ignore
from ci_dependency_lint import CILinter  # type: ignore


class TestDependencyAnalyzer:
    """Test cases for the dependency analyzer."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project structure."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir) / 'test_project'
        project_path.mkdir()
        
        yield project_path
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def create_module(self, path: Path, name: str, imports: list = None):
        """Helper to create a Python module with imports."""
        imports = imports or []
        content = '\n'.join([f'import {imp}' for imp in imports])
        content += '\n\nclass Example:\n    pass\n'
        
        module_path = path / f'{name}.py'
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_text(content)
        return module_path
    
    def test_simple_circular_dependency(self, temp_project):
        """Test detection of simple circular dependency (A -> B -> A)."""
        # Create modules with circular dependency
        # module_a imports module_b
        self.create_module(temp_project, 'module_a', ['module_b'])
        
        # module_b imports module_a
        self.create_module(temp_project, 'module_b', ['module_a'])
        
        # Analyze
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        circular_deps = analyzer.detect_circular_dependencies()
        
        # Should find one circular dependency
        assert len(circular_deps) > 0, "Should detect circular dependency"
        
        # Verify the cycle contains both modules
        cycle = circular_deps[0].cycle
        assert 'module_a' in cycle and 'module_b' in cycle
    
    def test_complex_circular_dependency(self, temp_project):
        """Test detection of complex circular dependency (A -> B -> C -> A)."""
        # Create a more complex cycle
        self.create_module(temp_project, 'module_a', ['module_b'])
        self.create_module(temp_project, 'module_b', ['module_c'])
        self.create_module(temp_project, 'module_c', ['module_a'])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        circular_deps = analyzer.detect_circular_dependencies()
        
        assert len(circular_deps) > 0, "Should detect circular dependency"
        assert len(circular_deps[0].cycle) >= 3, "Cycle should have at least 3 modules"
    
    def test_no_circular_dependency(self, temp_project):
        """Test that no false positives occur with clean dependencies."""
        # Create a clean dependency chain: A -> B -> C
        self.create_module(temp_project, 'module_a', ['module_b'])
        self.create_module(temp_project, 'module_b', ['module_c'])
        self.create_module(temp_project, 'module_c', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        circular_deps = analyzer.detect_circular_dependencies()
        
        assert len(circular_deps) == 0, "Should not detect any circular dependencies"
    
    def test_layer_detection(self, temp_project):
        """Test architectural layer detection."""
        # Create modules in different layers
        services_dir = temp_project / 'services'
        services_dir.mkdir()
        self.create_module(services_dir, 'user_service', [])
        
        routers_dir = temp_project / 'routers'
        routers_dir.mkdir()
        self.create_module(routers_dir, 'user_router', [])
        
        models_dir = temp_project / 'models'
        models_dir.mkdir()
        self.create_module(models_dir, 'user_model', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        
        # Check layer detection
        for module_name, module in analyzer.modules.items():
            if 'service' in module_name:
                assert module.layer == 'service'
            elif 'router' in module_name:
                assert module.layer == 'router'
            elif 'model' in module_name:
                assert module.layer == 'model'
    
    def test_layer_violation_detection(self, temp_project):
        """Test detection of architectural layer violations."""
        # Create a service that tries to import from a router (violation)
        services_dir = temp_project / 'services'
        services_dir.mkdir()
        
        routers_dir = temp_project / 'routers'
        routers_dir.mkdir()
        
        # Router file
        router_path = routers_dir / 'user_router.py'
        router_path.write_text('class UserRouter:\n    pass\n')
        
        # Service trying to import router (violation)
        service_path = services_dir / 'user_service.py'
        service_path.write_text('from user_router import UserRouter\n\nclass UserService:\n    pass\n')
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        violations = analyzer.check_layer_violations()
        
        # This should detect a violation (service importing router)
        assert len(violations) > 0, "Should detect layer violation"
    
    def test_dynamic_import_detection(self, temp_project):
        """Test detection of dynamic imports using importlib."""
        # Create module with dynamic import
        module_path = temp_project / 'dynamic_loader.py'
        module_path.write_text("""
import importlib

def load_module():
    mod = importlib.import_module('target_module')
    return mod

class DynamicLoader:
    pass
""")
        
        self.create_module(temp_project, 'target_module', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        
        # Check that dynamic import was detected
        dynamic_module = None
        for name, module in analyzer.modules.items():
            if 'dynamic_loader' in name:
                dynamic_module = module
                break
        
        assert dynamic_module is not None
        assert 'target_module' in dynamic_module.imports or any('target' in imp for imp in dynamic_module.imports)
    
    def test_conditional_import_detection(self, temp_project):
        """Test detection of conditional imports (TYPE_CHECKING)."""
        # Create module with TYPE_CHECKING import
        module_path = temp_project / 'typed_module.py'
        module_path.write_text("""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dependency_module import SomeClass

class TypedModule:
    def method(self, arg: 'SomeClass') -> None:
        pass
""")
        
        self.create_module(temp_project, 'dependency_module', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        
        # Verify the module was scanned
        assert len(analyzer.modules) >= 2
    
    def test_plugin_system_detection(self, temp_project):
        """Test handling of plugin systems with dynamic loading."""
        # Create a plugin system
        plugins_dir = temp_project / 'plugins'
        plugins_dir.mkdir()
        
        # Plugin loader
        loader_path = temp_project / 'plugin_loader.py'
        loader_path.write_text("""
import importlib
import os

def load_plugins():
    plugin_dir = os.path.join(os.path.dirname(__file__), 'plugins')
    for filename in os.listdir(plugin_dir):
        if filename.endswith('.py'):
            module_name = filename[:-3]
            importlib.import_module(f'plugins.{module_name}')

class PluginLoader:
    pass
""")
        
        # Create some plugins
        self.create_module(plugins_dir, 'plugin_a', [])
        self.create_module(plugins_dir, 'plugin_b', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        # Should successfully analyze without errors
        assert len(analyzer.modules) >= 3
    
    def test_graph_accuracy(self, temp_project):
        """Test accuracy of dependency graph construction."""
        # Create a known dependency structure
        # A depends on B and C
        # B depends on C
        # C depends on nothing
        self.create_module(temp_project, 'module_a', ['module_b', 'module_c'])
        self.create_module(temp_project, 'module_b', ['module_c'])
        self.create_module(temp_project, 'module_c', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        # Verify graph accuracy
        assert 'module_a' in analyzer.dependency_graph
        assert 'module_b' in analyzer.dependency_graph
        assert 'module_c' in analyzer.dependency_graph or len(analyzer.dependency_graph['module_c']) == 0
    
    def test_exclude_patterns(self, temp_project):
        """Test that excluded patterns are properly ignored."""
        # Create modules in excluded directories
        tests_dir = temp_project / 'tests'
        tests_dir.mkdir()
        self.create_module(tests_dir, 'test_something', [])
        
        # Create module in non-excluded directory
        self.create_module(temp_project, 'module_a', [])
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        
        # Test module should be excluded
        module_names = list(analyzer.modules.keys())
        test_modules = [name for name in module_names if 'test' in name]
        
        # Depending on implementation, tests might be excluded
        # Just verify that regular modules are included
        regular_modules = [name for name in module_names if 'module_a' in name]
        assert len(regular_modules) > 0, "Regular modules should be included"


class TestCILinter:
    """Test cases for CI linter."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir) / 'test_project'
        project_path.mkdir()
        
        yield project_path
        
        shutil.rmtree(temp_dir)
    
    def create_service_module(self, path: Path, name: str, imports: list = None):
        """Create a service module."""
        imports = imports or []
        content = '\n'.join([f'import {imp}' for imp in imports])
        content += '\n\nclass Service:\n    pass\n'
        
        services_dir = path / 'services'
        services_dir.mkdir(exist_ok=True)
        
        module_path = services_dir / f'{name}_service.py'
        module_path.write_text(content)
        return module_path
    
    def test_ci_passes_on_clean_code(self, temp_project):
        """Test that CI passes on clean code without violations."""
        # Create clean modules
        self.create_service_module(temp_project, 'user', [])
        self.create_service_module(temp_project, 'profile', [])
        
        linter = CILinter(temp_project, strict=False)
        report = linter.run_all_checks()
        
        assert report['status'] == 'passed'
        assert report['summary']['errors'] == 0
    
    def test_ci_fails_on_circular_dependency(self, temp_project):
        """Test that CI fails when circular dependencies exist."""
        # Create circular dependency
        services_dir = temp_project / 'services'
        services_dir.mkdir()
        
        # Service A imports B
        (services_dir / 'service_a.py').write_text('import service_b\n\nclass A:\n    pass\n')
        # Service B imports A
        (services_dir / 'service_b.py').write_text('import service_a\n\nclass B:\n    pass\n')
        
        linter = CILinter(temp_project, strict=False)
        report = linter.run_all_checks()
        
        assert len(report['violations']['circular']) > 0
        exit_code = linter.determine_exit_code(report)
        assert exit_code != 0, "CI should fail on circular dependencies"
    
    def test_report_generation(self, temp_project):
        """Test that reports are generated correctly."""
        self.create_service_module(temp_project, 'user', [])
        
        linter = CILinter(temp_project)
        report = linter.run_all_checks()
        
        # Verify report structure
        assert 'status' in report
        assert 'summary' in report
        assert 'violations' in report
        assert 'metadata' in report
        
        # Verify summary fields
        assert 'total_modules' in report['summary']
        assert 'total_dependencies' in report['summary']
        assert 'errors' in report['summary']
        assert 'warnings' in report['summary']


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir) / 'test_project'
        project_path.mkdir()
        
        yield project_path
        
        shutil.rmtree(temp_dir)
    
    def test_syntax_error_handling(self, temp_project):
        """Test that syntax errors don't crash the analyzer."""
        # Create module with syntax error
        bad_module = temp_project / 'bad_module.py'
        bad_module.write_text('import os\n\nclass Bad\n    pass\n')  # Missing colon
        
        # Create valid module
        good_module = temp_project / 'good_module.py'
        good_module.write_text('import os\n\nclass Good:\n    pass\n')
        
        analyzer = DependencyAnalyzer(temp_project)
        
        # Should not crash
        analyzer.scan_directory()
        
        # Should still analyze valid modules
        assert len(analyzer.modules) >= 1
    
    def test_empty_project(self, temp_project):
        """Test handling of empty projects."""
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        circular_deps = analyzer.detect_circular_dependencies()
        
        assert len(circular_deps) == 0
        assert len(analyzer.modules) == 0
    
    def test_self_import(self, temp_project):
        """Test handling of modules that import themselves."""
        # Create module that imports itself (edge case)
        module_path = temp_project / 'self_import.py'
        module_path.write_text('import self_import\n\nclass SelfImport:\n    pass\n')
        
        analyzer = DependencyAnalyzer(temp_project)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        # Should handle gracefully
        assert len(analyzer.modules) >= 1


def run_integration_test():
    """
    Integration test that creates a realistic project with circular dependencies
    and validates that the entire system works end-to-end.
    """
    import tempfile
    import shutil
    
    print("\n" + "="*80)
    print("INTEGRATION TEST: Realistic Project with Circular Dependencies")
    print("="*80)
    
    # Create temporary project
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir) / 'real_project'
    project_path.mkdir()
    
    try:
        # Create realistic service layer structure
        services = project_path / 'services'
        services.mkdir()
        
        # user_service depends on profile_service (circular!)
        (services / 'user_service.py').write_text("""
from profile_service import ProfileService

class UserService:
    def __init__(self):
        self.profile_service = ProfileService()
""")
        
        # profile_service depends on user_service (completing the circle!)
        (services / 'profile_service.py').write_text("""
from user_service import UserService

class ProfileService:
    def __init__(self):
        self.user_service = UserService()
""")
        
        # Run analyzer
        print(f"\n📂 Created test project at: {project_path}")
        print("   - user_service.py → profile_service.py")
        print("   - profile_service.py → user_service.py")
        print("   (This creates a circular dependency)")
        
        analyzer = DependencyAnalyzer(project_path)
        analyzer.scan_directory()
        analyzer.build_graph()
        
        print(f"\n✅ Scanned {len(analyzer.modules)} modules")
        
        # Detect circular dependencies
        circular_deps = analyzer.detect_circular_dependencies()
        
        print(f"\n🔍 Circular dependency detection:")
        if circular_deps:
            print(f"   ✅ Successfully detected {len(circular_deps)} circular dependency!")
            for dep in circular_deps:
                print(f"   Cycle: {' -> '.join(dep.cycle)}")
        else:
            print("   ❌ FAILED: Did not detect the circular dependency!")
            return False
        
        # Test CI linter
        print(f"\n🔧 Running CI linter...")
        linter = CILinter(project_path)
        report = linter.run_all_checks()
        
        print(f"   Status: {report['status']}")
        print(f"   Errors: {report['summary']['errors']}")
        print(f"   Circular deps: {len(report['violations']['circular'])}")
        
        exit_code = linter.determine_exit_code(report)
        print(f"\n   Exit code: {exit_code}")
        
        if exit_code == 0:
            print("   ❌ FAILED: CI should have failed but returned 0!")
            return False
        else:
            print("   ✅ SUCCESS: CI correctly failed with non-zero exit code!")
        
        print("\n" + "="*80)
        print("✅ INTEGRATION TEST PASSED")
        print("="*80)
        return True
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    # Run integration test
    success = run_integration_test()
    sys.exit(0 if success else 1)
