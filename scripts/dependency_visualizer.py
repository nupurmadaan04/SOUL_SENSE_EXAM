"""
Dependency Graph Visualization

Provides enhanced visualization capabilities including:
- Converting DOT to SVG
- Interactive HTML visualization
- Circular dependency highlighting
"""

import subprocess
from pathlib import Path
from typing import Optional, Set
import json


class DependencyVisualizer:
    """Enhanced dependency graph visualization."""
    
    def __init__(self, analyzer):
        """
        Initialize visualizer.
        
        Args:
            analyzer: DependencyAnalyzer instance
        """
        self.analyzer = analyzer
        
    def generate_dot_with_highlights(
        self, 
        output_file: Path,
        circular_deps: Optional[list] = None,
        highlight_modules: Optional[Set[str]] = None
    ) -> None:
        """
        Generate DOT file with circular dependencies highlighted.
        
        Args:
            output_file: Output DOT file path
            circular_deps: List of CircularDependency objects to highlight
            highlight_modules: Additional modules to highlight
        """
        circular_modules = set()
        circular_edges = set()
        
        if circular_deps:
            for dep in circular_deps:
                # Add all modules in cycle
                circular_modules.update(dep.cycle)
                
                # Add all edges in cycle
                for i in range(len(dep.cycle) - 1):
                    circular_edges.add((dep.cycle[i], dep.cycle[i + 1]))
        
        if highlight_modules:
            circular_modules.update(highlight_modules)
        
        with open(output_file, 'w') as f:
            f.write('digraph dependencies {\n')
            f.write('  rankdir=TB;\n')
            f.write('  node [shape=box, style=rounded];\n')
            f.write('  graph [layout=dot, splines=ortho];\n\n')
            
            # Color scheme
            layer_colors = {
                'router': '#FF6B6B',
                'service': '#4ECDC4',
                'repository': '#45B7D1',
                'model': '#96CEB4',
                'schema': '#FFEAA7',
                'util': '#DFE6E9',
                'exception': '#FD79A8',
                'middleware': '#A29BFE',
                'config': '#74B9FF',
                'unknown': '#B2BEC3'
            }
            
            # Group nodes by layer
            layers = {}
            for module_name, module in self.analyzer.modules.items():
                layer = module.layer
                if layer not in layers:
                    layers[layer] = []
                layers[layer].append(module_name)
            
            # Write layer subgraphs
            for layer, modules in layers.items():
                f.write(f'  subgraph cluster_{layer} {{\n')
                f.write(f'    label="{layer.upper()} LAYER";\n')
                f.write(f'    style=filled;\n')
                f.write(f'    color=lightgrey;\n\n')
                
                for module_name in modules:
                    module = self.analyzer.modules[module_name]
                    color = layer_colors.get(layer, '#B2BEC3')
                    label = module_name.split('.')[-1]
                    
                    # Highlight circular modules
                    if module_name in circular_modules:
                        f.write(f'    "{module_name}" [label="{label}", '
                               f'fillcolor="{color}", style="filled,bold", '
                               f'penwidth=3, color="red"];\n')
                    else:
                        f.write(f'    "{module_name}" [label="{label}", '
                               f'fillcolor="{color}", style="filled"];\n')
                
                f.write('  }\n\n')
            
            # Write edges
            for module_name, deps in self.analyzer.dependency_graph.items():
                for dep in deps:
                    # Highlight circular edges
                    if (module_name, dep) in circular_edges:
                        f.write(f'  "{module_name}" -> "{dep}" '
                               f'[color="red", penwidth=3, style="bold"];\n')
                    else:
                        f.write(f'  "{module_name}" -> "{dep}";\n')
            
            f.write('}\n')
        
        print(f"Enhanced DOT graph exported to: {output_file}")
    
    def dot_to_svg(self, dot_file: Path, svg_file: Optional[Path] = None) -> Optional[Path]:
        """
        Convert DOT file to SVG using Graphviz.
        
        Args:
            dot_file: Input DOT file
            svg_file: Output SVG file (optional, will use same name as dot_file)
            
        Returns:
            Path to SVG file if successful, None otherwise
        """
        if svg_file is None:
            svg_file = dot_file.with_suffix('.svg')
        
        try:
            # Check if graphviz is installed
            subprocess.run(
                ['dot', '-V'],
                capture_output=True,
                check=True
            )
            
            # Convert DOT to SVG
            subprocess.run(
                ['dot', '-Tsvg', str(dot_file), '-o', str(svg_file)],
                check=True,
                capture_output=True
            )
            
            print(f"✅ SVG generated: {svg_file}")
            return svg_file
            
        except FileNotFoundError:
            print("⚠️  Graphviz 'dot' command not found. Please install Graphviz:")
            print("   - Windows: choco install graphviz")
            print("   - Linux: apt-get install graphviz")
            print("   - macOS: brew install graphviz")
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Error converting DOT to SVG: {e}")
            return None
    
    def generate_html_visualization(
        self,
        output_file: Path,
        report: dict
    ) -> None:
        """
        Generate interactive HTML visualization.
        
        Args:
            output_file: Output HTML file path
            report: Dependency analysis report
        """
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dependency Analysis Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .error {{
            background: #fee;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 10px 0;
            border-radius: 3px;
        }}
        .warning {{
            background: #fef7e0;
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin: 10px 0;
            border-radius: 3px;
        }}
        .success {{
            background: #e8f8f5;
            border-left: 4px solid #27ae60;
            padding: 15px;
            margin: 10px 0;
            border-radius: 3px;
        }}
        .violation-list {{
            list-style: none;
            padding: 0;
        }}
        .violation-item {{
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #e74c3c;
        }}
        .cycle {{
            font-family: 'Courier New', monospace;
            background: #2c3e50;
            color: #ecf0f1;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .layer-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            margin: 0 5px;
        }}
        .router {{ background: #FF6B6B; color: white; }}
        .service {{ background: #4ECDC4; color: white; }}
        .model {{ background: #96CEB4; color: white; }}
        .schema {{ background: #FFEAA7; color: #333; }}
        .util {{ background: #DFE6E9; color: #333; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Dependency Analysis Report</h1>
        
        <div class="summary">
            <div class="metric">
                <div class="metric-value">{report['summary']['total_modules']}</div>
                <div class="metric-label">Total Modules</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report['summary']['total_dependencies']}</div>
                <div class="metric-label">Total Dependencies</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report['summary']['average_dependencies']}</div>
                <div class="metric-label">Avg. Dependencies</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report['summary']['circular_dependencies']}</div>
                <div class="metric-label">Circular Dependencies</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report['summary']['layer_violations']}</div>
                <div class="metric-label">Layer Violations</div>
            </div>
        </div>
        
        {'<div class="error"><h2>❌ Circular Dependencies Found</h2>' + self._render_circular_deps(report) + '</div>' if report['circular_dependencies'] else '<div class="success"><h2>✅ No Circular Dependencies</h2><p>Great! Your codebase has no circular dependencies.</p></div>'}
        
        {'<div class="warning"><h2>⚠️ Layer Violations</h2>' + self._render_layer_violations(report) + '</div>' if report['layer_violations'] else '<div class="success"><h2>✅ No Layer Violations</h2><p>All architectural boundaries are respected.</p></div>'}
        
        <h2>📊 Module Statistics</h2>
        <h3>Modules with Most Dependencies</h3>
        {self._render_module_table(report['modules_with_most_dependencies'])}
        
        <h3>Most Imported Modules</h3>
        {self._render_module_table(report['most_imported_modules'])}
        
        <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; text-align: center;">
            <p>Generated by SoulSense Dependency Analyzer</p>
        </footer>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ HTML visualization generated: {output_file}")
    
    def _render_circular_deps(self, report: dict) -> str:
        """Render circular dependencies as HTML."""
        html = '<ul class="violation-list">'
        for dep in report['circular_dependencies']:
            cycle_str = ' → '.join(dep['cycle'])
            html += f'<li class="violation-item"><div class="cycle">{cycle_str}</div></li>'
        html += '</ul>'
        return html
    
    def _render_layer_violations(self, report: dict) -> str:
        """Render layer violations as HTML."""
        html = '<ul class="violation-list">'
        for v in report['layer_violations'][:20]:  # Limit to 20
            html += f'''
            <li class="violation-item">
                <strong>{v['from']}</strong> → <strong>{v['to']}</strong><br>
                <small>{v['reason']}</small>
            </li>
            '''
        html += '</ul>'
        return html
    
    def _render_module_table(self, modules: list) -> str:
        """Render module statistics as HTML table."""
        html = '<table><thead><tr><th>Module</th><th>Count</th></tr></thead><tbody>'
        for item in modules:
            html += f"<tr><td>{item['module']}</td><td>{item['count']}</td></tr>"
        html += '</tbody></table>'
        return html


def main():
    """CLI for visualization."""
    import argparse
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path(__file__).parent))
    from dependency_analyzer import DependencyAnalyzer
    
    parser = argparse.ArgumentParser(description='Dependency Graph Visualization')
    parser.add_argument('path', nargs='?', default='backend', help='Path to analyze')
    parser.add_argument('--output', default='dependency_graph', help='Output file name')
    parser.add_argument('--format', choices=['svg', 'html', 'both'], default='both')
    
    args = parser.parse_args()
    
    # Analyze
    analyzer = DependencyAnalyzer(Path(args.path))
    analyzer.scan_directory()
    analyzer.build_graph()
    
    # Generate report
    report = analyzer.generate_report()
    circular_deps = analyzer.detect_circular_dependencies()
    
    # Visualize
    visualizer = DependencyVisualizer(analyzer)
    
    if args.format in ['svg', 'both']:
        dot_file = Path(f"{args.output}.dot")
        visualizer.generate_dot_with_highlights(dot_file, circular_deps)
        visualizer.dot_to_svg(dot_file)
    
    if args.format in ['html', 'both']:
        html_file = Path(f"{args.output}.html")
        visualizer.generate_html_visualization(html_file, report)


if __name__ == '__main__':
    main()
