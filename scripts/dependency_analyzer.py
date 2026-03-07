"""
Service-Layer Dependency Graph Analyzer

This module analyzes Python module dependencies to:
- Generate dependency graphs
- Detect circular dependencies
- Enforce architectural boundaries
- Provide visualization output

Usage:
    python scripts/dependency_analyzer.py --analyze backend/
    python scripts/dependency_analyzer.py --check-circular
    python scripts/dependency_analyzer.py --visualize --output deps.svg
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json
import re


@dataclass
class Module:
    """Represents a Python module in the dependency graph."""
    name: str
    file_path: Path
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    layer: Optional[str] = None  # e.g., 'service', 'router', 'model'


@dataclass
class CircularDependency:
    """Represents a detected circular dependency."""
    cycle: List[str]
    severity: str = "error"  # error, warning
    
    def __str__(self) -> str:
        return " -> ".join(self.cycle + [self.cycle[0]])


class DependencyAnalyzer:
    """Analyzes Python module dependencies and detects architectural violations."""
    
    # Architectural layer rules
    LAYER_HIERARCHY = {
        'router': ['service', 'model', 'schema', 'exception'],
        'service': ['model', 'schema', 'exception', 'util'],
        'model': ['exception'],
        'schema': ['exception'],
        'util': [],
        'exception': []
    }
    
    def __init__(self, root_path: Path, exclude_patterns: Optional[List[str]] = None):
        """
        Initialize the dependency analyzer.
        
        Args:
            root_path: Root directory to analyze
            exclude_patterns: List of patterns to exclude (e.g., ['test_*', '__pycache__'])
        """
        self.root_path = Path(root_path).resolve()
        self.exclude_patterns = exclude_patterns or [
            '__pycache__',
            '.venv',
            'venv',
            'tests',
            'test_*',
            '*.pyc',
            'migrations'
        ]
        self.modules: Dict[str, Module] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        
    def should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from analysis."""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern.startswith('*.'):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert a file path to a module name."""
        try:
            rel_path = file_path.relative_to(self.root_path)
            module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
            if module_parts[-1] == '__init__':
                module_parts = module_parts[:-1]
            return '.'.join(module_parts)
        except ValueError:
            return str(file_path)
    
    def detect_layer(self, module_name: str, file_path: Path) -> str:
        """Detect the architectural layer of a module."""
        path_lower = str(file_path).lower()
        name_lower = module_name.lower()
        
        # Check file path and name for layer indicators
        if 'router' in path_lower or 'endpoint' in path_lower:
            return 'router'
        elif 'service' in path_lower:
            return 'service'
        elif 'model' in path_lower and 'schema' not in path_lower:
            return 'model'
        elif 'schema' in path_lower or 'pydantic' in path_lower:
            return 'schema'
        elif 'exception' in path_lower or 'error' in path_lower:
            return 'exception'
        elif 'infra' in path_lower:
            return 'infra'
        elif 'util' in path_lower or 'helper' in path_lower:
            return 'util'
        
        return 'unknown'
    
    def extract_imports(self, file_path: Path) -> List[str]:
        """
        Extract import statements from a Python file.
        
        Handles:
        - Standard imports (import x)
        - From imports (from x import y)
        - Conditional imports (if TYPE_CHECKING)
        - Dynamic imports (importlib)
        """
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                # Standard import
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                
                # From import
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_base = node.module.split('.')[0]
                        imports.append(module_base)
                
                # Dynamic imports (importlib.import_module)
                elif isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Attribute) and
                        isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'importlib' and
                        node.func.attr == 'import_module'):
                        if node.args and isinstance(node.args[0], ast.Constant):
                            imports.append(node.args[0].value.split('.')[0])
                    
                    # __import__()
                    elif (isinstance(node.func, ast.Name) and 
                          node.func.id == '__import__'):
                        if node.args and isinstance(node.args[0], ast.Constant):
                            imports.append(node.args[0].value.split('.')[0])
            
            # Deduplicate
            return list(set(imports))
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return []
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []
    
    def scan_directory(self) -> None:
        """Scan directory and build module registry."""
        print(f"Scanning directory: {self.root_path}")
        
        for py_file in self.root_path.rglob('*.py'):
            if self.should_exclude(py_file):
                continue
            
            module_name = self.get_module_name(py_file)
            imports = self.extract_imports(py_file)
            layer = self.detect_layer(module_name, py_file)
            
            module = Module(
                name=module_name,
                file_path=py_file,
                imports=imports,
                layer=layer
            )
            
            self.modules[module_name] = module
        
        print(f"Found {len(self.modules)} modules")
    
    def build_graph(self) -> None:
        """Build the dependency graph from scanned modules."""
        for module_name, module in self.modules.items():
            for imported in module.imports:
                # Try to match to a known module
                for known_module in self.modules.keys():
                    if known_module.startswith(imported) or imported in known_module:
                        self.dependency_graph[module_name].add(known_module)
                        self.reverse_graph[known_module].add(module_name)
                        
                        # Update imported_by
                        if known_module in self.modules:
                            self.modules[known_module].imported_by.append(module_name)
    
    def detect_circular_dependencies(self) -> List[CircularDependency]:
        """
        Detect circular dependencies using DFS with cycle detection.
        
        Returns:
            List of detected circular dependencies
        """
        circular_deps = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """DFS with cycle detection."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    circular_deps.append(CircularDependency(cycle=cycle))
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for module in self.modules.keys():
            if module not in visited:
                dfs(module)
        
        # Deduplicate cycles (same cycle in different order)
        unique_cycles = []
        seen_cycles = set()
        
        for dep in circular_deps:
            # Normalize cycle (start from smallest element)
            cycle = dep.cycle[:-1]  # Remove duplicate last element
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
            
            if normalized not in seen_cycles:
                seen_cycles.add(normalized)
                unique_cycles.append(dep)
        
        return unique_cycles
    
    def check_layer_violations(self) -> List[Tuple[str, str, str]]:
        """
        Check for architectural layer violations.
        
        Returns:
            List of (module, imported_module, reason) tuples
        """
        violations = []
        
        for module_name, module in self.modules.items():
            if module.layer == 'unknown':
                continue
            
            allowed_layers = self.LAYER_HIERARCHY.get(module.layer, [])
            
            for imported_name in module.imports:
                # Find the imported module
                imported_module = None
                for known_module in self.modules.keys():
                    if known_module.startswith(imported_name) or imported_name in known_module:
                        imported_module = self.modules[known_module]
                        break
                
                if imported_module and imported_module.layer not in allowed_layers:
                    reason = (f"{module.layer} layer cannot import from "
                             f"{imported_module.layer} layer")
                    violations.append((module_name, imported_module.name, reason))
        
        return violations
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive analysis report."""
        circular_deps = self.detect_circular_dependencies()
        layer_violations = self.check_layer_violations()
        
        # Calculate metrics
        total_modules = len(self.modules)
        total_dependencies = sum(len(deps) for deps in self.dependency_graph.values())
        avg_dependencies = total_dependencies / total_modules if total_modules > 0 else 0
        
        # Find modules with most dependencies
        most_deps = sorted(
            [(name, len(deps)) for name, deps in self.dependency_graph.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Find most imported modules
        most_imported = sorted(
            [(name, len(importers)) for name, importers in self.reverse_graph.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        report = {
            'summary': {
                'total_modules': total_modules,
                'total_dependencies': total_dependencies,
                'average_dependencies': round(avg_dependencies, 2),
                'circular_dependencies': len(circular_deps),
                'layer_violations': len(layer_violations)
            },
            'circular_dependencies': [
                {'cycle': dep.cycle, 'severity': dep.severity}
                for dep in circular_deps
            ],
            'layer_violations': [
                {'from': m1, 'to': m2, 'reason': reason}
                for m1, m2, reason in layer_violations
            ],
            'modules_with_most_dependencies': [
                {'module': name, 'count': count} for name, count in most_deps
            ],
            'most_imported_modules': [
                {'module': name, 'count': count} for name, count in most_imported
            ]
        }
        
        return report
    
    def export_dot(self, output_file: Path) -> None:
        """
        Export dependency graph in DOT format for visualization.
        
        Args:
            output_file: Output file path
        """
        with open(output_file, 'w') as f:
            f.write('digraph dependencies {\n')
            f.write('  rankdir=LR;\n')
            f.write('  node [shape=box, style=rounded];\n\n')
            
            # Color nodes by layer
            layer_colors = {
                'router': '#ff6b6b',
                'service': '#4ecdc4',
                'model': '#45b7d1',
                'schema': '#96ceb4',
                'util': '#ffeaa7',
                'exception': '#dfe6e9',
                'unknown': '#b2bec3'
            }
            
            # Write nodes with colors
            for module_name, module in self.modules.items():
                color = layer_colors.get(module.layer, '#b2bec3')
                label = module_name.split('.')[-1]  # Short name
                f.write(f'  "{module_name}" [label="{label}", '
                       f'fillcolor="{color}", style="filled"];\n')
            
            f.write('\n')
            
            # Write edges
            for module_name, deps in self.dependency_graph.items():
                for dep in deps:
                    f.write(f'  "{module_name}" -> "{dep}";\n')
            
            f.write('}\n')
        
        print(f"DOT graph exported to: {output_file}")
    
    def export_json(self, output_file: Path) -> None:
        """Export dependency graph in JSON format."""
        graph_data = {
            'modules': {
                name: {
                    'file_path': str(module.file_path),
                    'imports': module.imports,
                    'imported_by': module.imported_by,
                    'layer': module.layer
                }
                for name, module in self.modules.items()
            },
            'dependencies': {
                name: list(deps) for name, deps in self.dependency_graph.items()
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        print(f"JSON graph exported to: {output_file}")


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze Python module dependencies and detect circular dependencies'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='backend',
        help='Path to analyze (default: backend)'
    )
    parser.add_argument(
        '--check-circular',
        action='store_true',
        help='Check for circular dependencies and exit with error if found'
    )
    parser.add_argument(
        '--check-layers',
        action='store_true',
        help='Check for architectural layer violations'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualization output'
    )
    parser.add_argument(
        '--output',
        default='dependency_graph',
        help='Output file name (without extension)'
    )
    parser.add_argument(
        '--format',
        choices=['dot', 'json', 'both'],
        default='both',
        help='Output format'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed report'
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = DependencyAnalyzer(Path(args.path))
    
    # Scan and build graph
    analyzer.scan_directory()
    analyzer.build_graph()
    
    # Generate report
    if args.report or args.check_circular or args.check_layers:
        report = analyzer.generate_report()
        
        print("\n" + "="*80)
        print("DEPENDENCY ANALYSIS REPORT")
        print("="*80)
        print(f"\nTotal Modules: {report['summary']['total_modules']}")
        print(f"Total Dependencies: {report['summary']['total_dependencies']}")
        print(f"Average Dependencies per Module: {report['summary']['average_dependencies']}")
        print(f"Circular Dependencies: {report['summary']['circular_dependencies']}")
        print(f"Layer Violations: {report['summary']['layer_violations']}")
        
        if report['circular_dependencies']:
            print("\n" + "-"*80)
            print("CIRCULAR DEPENDENCIES:")
            print("-"*80)
            for dep in report['circular_dependencies']:
                cycle_str = " -> ".join(dep['cycle'])
                print(f"  [{dep['severity'].upper()}] {cycle_str}")
        
        if report['layer_violations']:
            print("\n" + "-"*80)
            print("LAYER VIOLATIONS:")
            print("-"*80)
            for violation in report['layer_violations']:
                print(f"  {violation['from']} -> {violation['to']}")
                print(f"    Reason: {violation['reason']}")
        
        if report['modules_with_most_dependencies']:
            print("\n" + "-"*80)
            print("MODULES WITH MOST DEPENDENCIES:")
            print("-"*80)
            for item in report['modules_with_most_dependencies'][:5]:
                print(f"  {item['module']}: {item['count']}")
        
        if report['most_imported_modules']:
            print("\n" + "-"*80)
            print("MOST IMPORTED MODULES:")
            print("-"*80)
            for item in report['most_imported_modules'][:5]:
                print(f"  {item['module']}: {item['count']}")
        
        print("\n" + "="*80)
        
        # Save report to JSON
        report_file = Path(f"{args.output}_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")
    
    # Check for circular dependencies (CI mode)
    if args.check_circular:
        circular_deps = analyzer.detect_circular_dependencies()
        if circular_deps:
            print(f"\n❌ FAIL: Found {len(circular_deps)} circular dependencies")
            sys.exit(1)
        else:
            print("\n✅ PASS: No circular dependencies found")
    
    # Check for layer violations (CI mode)
    if args.check_layers:
        violations = analyzer.check_layer_violations()
        if violations:
            print(f"\n❌ FAIL: Found {len(violations)} layer violations")
            sys.exit(1)
        else:
            print("\n✅ PASS: No layer violations found")
    
    # Generate visualization
    if args.visualize:
        if args.format in ['dot', 'both']:
            dot_file = Path(f"{args.output}.dot")
            analyzer.export_dot(dot_file)
        
        if args.format in ['json', 'both']:
            json_file = Path(f"{args.output}.json")
            analyzer.export_json(json_file)


if __name__ == '__main__':
    main()
