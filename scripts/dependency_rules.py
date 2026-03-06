"""
Dependency Rules Configuration

Define architectural boundaries and allowed dependencies between layers.
"""

# Architectural Layer Hierarchy
# Lower layers (right) can be imported by higher layers (left)
LAYER_HIERARCHY = {
    'router': {
        'allowed': ['service', 'schema', 'exception', 'util'],
        'forbidden': ['router'],  # Routers should not import from other routers
        'description': 'API route handlers and endpoints'
    },
    'service': {
        'allowed': ['model', 'schema', 'exception', 'util', 'repository'],
        'forbidden': ['router', 'service'],  # Services should not import from routers or other services
        'description': 'Business logic layer'
    },
    'repository': {
        'allowed': ['model', 'exception', 'util'],
        'forbidden': ['router', 'service', 'schema'],
        'description': 'Data access layer'
    },
    'model': {
        'allowed': ['exception'],
        'forbidden': ['router', 'service', 'schema', 'util'],
        'description': 'Database models and entities'
    },
    'schema': {
        'allowed': ['exception', 'util'],
        'forbidden': ['router', 'service', 'model'],
        'description': 'Data validation and serialization schemas'
    },
    'util': {
        'allowed': ['exception'],
        'forbidden': ['router', 'service', 'model', 'schema', 'repository'],
        'description': 'Utility functions and helpers'
    },
    'exception': {
        'allowed': [],
        'forbidden': ['router', 'service', 'model', 'schema', 'util', 'repository'],
        'description': 'Custom exceptions and error definitions'
    },
    'middleware': {
        'allowed': ['exception', 'util', 'service'],
        'forbidden': ['router'],
        'description': 'Request/response middleware'
    },
    'config': {
        'allowed': ['exception'],
        'forbidden': ['router', 'service', 'model', 'schema', 'util', 'repository'],
        'description': 'Configuration and settings'
    }
}

# Module-specific rules
MODULE_RULES = {
    # Core modules that should not have many dependencies
    'core_modules': [
        'exception',
        'config',
        'constants'
    ],
    
    # Modules that should avoid circular dependencies at all costs
    'critical_modules': [
        'auth_service',
        'db_service',
        'user_service'
    ],
    
    # Maximum allowed dependencies per module
    'max_dependencies': {
        'default': 15,
        'service': 10,
        'router': 8,
        'util': 5,
        'exception': 0
    },
    
    # Minimum test coverage requirements by layer
    'test_coverage': {
        'service': 80,
        'router': 70,
        'util': 90,
        'default': 60
    }
}

# Patterns to exclude from dependency analysis
EXCLUDE_PATTERNS = [
    '__pycache__',
    '.venv',
    'venv',
    'env',
    'tests',
    'test_*',
    '*.pyc',
    '*.pyo',
    'migrations',
    'alembic',
    '.pytest_cache',
    'htmlcov',
    '*.egg-info'
]

# Patterns for dynamic imports that need special handling
DYNAMIC_IMPORT_PATTERNS = [
    r'importlib\.import_module\(["\'](.+?)["\']\)',
    r'__import__\(["\'](.+?)["\']\)',
    r'import_string\(["\'](.+?)["\']\)',
]

# Allowed external dependencies (won't trigger warnings)
ALLOWED_EXTERNAL_DEPS = {
    'standard_library': [
        'os', 'sys', 'typing', 'datetime', 'pathlib', 'json',
        'logging', 'collections', 'dataclasses', 'enum', 'abc',
        'asyncio', 're', 'time', 'uuid', 'hashlib', 'secrets'
    ],
    'third_party': [
        'fastapi', 'pydantic', 'sqlalchemy', 'alembic',
        'bcrypt', 'jwt', 'redis', 'celery',
        'pytest', 'httpx', 'starlette'
    ]
}

# CI/CD enforcement settings
CI_CONFIG = {
    'fail_on_circular': True,
    'fail_on_layer_violations': True,
    'fail_on_excessive_deps': True,
    'max_warnings': 10,
    'report_format': 'json',  # json, markdown, html
    'output_dir': 'reports/dependencies'
}

# Visualization settings
VISUALIZATION_CONFIG = {
    'max_nodes': 100,  # Limit for large graphs
    'group_by_layer': True,
    'show_external_deps': False,
    'highlight_circular': True,
    'color_scheme': {
        'router': '#FF6B6B',      # Red
        'service': '#4ECDC4',     # Turquoise
        'repository': '#45B7D1',  # Blue
        'model': '#96CEB4',       # Green
        'schema': '#FFEAA7',      # Yellow
        'util': '#DFE6E9',        # Gray
        'exception': '#FD79A8',   # Pink
        'middleware': '#A29BFE',  # Purple
        'config': '#74B9FF'       # Light Blue
    }
}
