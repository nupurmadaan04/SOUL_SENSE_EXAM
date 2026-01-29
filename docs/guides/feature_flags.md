# Feature Flags Guide

This guide explains how to use the feature flag system in SoulSense to enable/disable experimental features safely.

## Overview

Feature flags allow you to enable or disable experimental features without code changes. This is useful for:

- **Gradual rollouts**: Enable features for specific users or environments
- **A/B testing**: Compare different implementations
- **Safe deployments**: Disable problematic features quickly
- **Development workflow**: Enable experimental features during development

## Configuration Sources

Feature flags can be configured from three sources (in order of priority):

### 1. Environment Variables (Highest Priority)

Set environment variables with the prefix `SOULSENSE_FF_`:

```bash
# Enable AI journal suggestions
export SOULSENSE_FF_AI_JOURNAL_SUGGESTIONS=true

# Disable advanced analytics
export SOULSENSE_FF_ADVANCED_ANALYTICS=false

# Enable multiple flags
export SOULSENSE_FF_BETA_UI_COMPONENTS=true
export SOULSENSE_FF_ML_EMOTION_DETECTION=true
```

### 2. Configuration File

Edit `config.json` in the `experimental` section:

```json
{
  "experimental": {
    "ai_journal_suggestions": false,
    "advanced_analytics": false,
    "beta_ui_components": false,
    "ml_emotion_detection": false,
    "data_export_v2": false
  }
}
```

### 3. Default Values (Lowest Priority)

Each flag has a default value defined in the code (typically `false` for experimental features).

## Available Feature Flags

### AI Features

- **`ai_journal_suggestions`**: Enable AI-powered suggestions in the journal feature
- **`ml_emotion_detection`**: Enable ML-based emotion detection from text entries

### Analytics Features

- **`advanced_analytics`**: Enable advanced analytics dashboard with predictive insights

### UI Features

- **`beta_ui_components`**: Enable beta UI components and experimental layouts

### Data Features

- **`data_export_v2`**: Enable new data export formats (PDF, enhanced CSV)

## Usage in Code

### Basic Flag Checking

```python
from app.feature_flags import feature_flags

# Check if a feature is enabled
if feature_flags.is_enabled("ai_journal_suggestions"):
    # Show AI suggestions UI
    show_ai_suggestions()

# Check if a feature is disabled (convenience method)
if feature_flags.is_disabled("advanced_analytics"):
    # Show basic analytics instead
    show_basic_analytics()
```

### Using Decorators

#### `@feature_gated` Decorator

Silently disables functionality when the flag is off:

```python
from app.feature_flags import feature_gated

@feature_gated("ai_journal_suggestions")
def get_ai_suggestions(text: str) -> List[str]:
    """Get AI-powered suggestions for journal entries."""
    # This code only runs if the flag is enabled
    return ai_model.generate_suggestions(text)

@feature_gated("ml_emotion_detection", fallback=[])
def analyze_emotions(text: str) -> List[str]:
    """Analyze emotions in text. Returns empty list if disabled."""
    return emotion_model.analyze(text)
```

#### `@require_feature` Decorator

Raises an error if the feature is disabled (for critical features):

```python
from app.feature_flags import require_feature

@require_feature("data_export_v2")
def export_data_pdf(data: Dict) -> bytes:
    """Export data to PDF format. Requires the feature to be enabled."""
    return pdf_exporter.export(data)
```

## Adding New Feature Flags

### 1. Define the Flag

Add your flag to `EXPERIMENTAL_FLAGS` in `app/feature_flags.py`:

```python
"new_feature_name": FeatureFlag(
    name="new_feature_name",
    default=False,
    description="Description of what this feature does",
    experimental=True,
    category="appropriate_category"  # ai, analytics, ui, data, etc.
),
```

### 2. Use the Flag in Code

```python
# In your module
from app.feature_flags import feature_flags

def some_function():
    if feature_flags.is_enabled("new_feature_name"):
        # New feature implementation
        pass
    else:
        # Fallback implementation
        pass
```

### 3. Update Configuration

Add the flag to `config.json`:

```json
{
  "experimental": {
    "new_feature_name": false
  }
}
```

## Best Practices

### 1. Naming Conventions

- Use lowercase with underscores: `ai_journal_suggestions`
- Be descriptive but concise
- Include the feature area: `ai_`, `ml_`, `ui_`, etc.

### 2. Default Values

- Experimental features should default to `False`
- Production-ready features can default to `True`
- Consider backward compatibility when changing defaults

### 3. Categories

- Group related features: `ai`, `analytics`, `ui`, `data`
- Use consistent categories across your application

### 4. Documentation

- Always provide clear descriptions
- Document what the feature does and any prerequisites
- Update this guide when adding new flags

### 5. Testing

- Test both enabled and disabled states
- Use environment variables in tests to override flags
- Consider feature flag state in integration tests

### 6. Cleanup

- Remove flags when features become stable
- Deprecate flags before removal with warnings
- Update configuration files when removing flags

## Runtime Management

### Checking Flag Status

```python
from app.feature_flags import feature_flags

# Get detailed status of all flags
status = feature_flags.get_flag_status()
for name, info in status.items():
    print(f"{name}: {info['enabled']} (source: {info['source']})")

# Get only enabled flags
enabled = feature_flags.get_enabled_flags()

# Get flags by category
ai_flags = feature_flags.get_flags_by_category("ai")
```

### Runtime Overrides (for testing/admin)

```python
from app.feature_flags import feature_flags

# Temporarily enable a feature
feature_flags.set_override("beta_ui_components", True)

# Clear the override
feature_flags.clear_override("beta_ui_components")

# Clear all overrides
feature_flags.clear_all_overrides()
```

## UI Integration

The settings UI automatically displays all feature flags. Users can see which flags are enabled/disabled and get descriptions.

## Environment-Specific Configuration

### Development

Enable experimental features for testing:

```bash
export SOULSENSE_FF_AI_JOURNAL_SUGGESTIONS=true
export SOULSENSE_FF_BETA_UI_COMPONENTS=true
```

### Staging

Enable some features for broader testing:

```bash
export SOULSENSE_FF_ADVANCED_ANALYTICS=true
```

### Production

Keep experimental features disabled by default, enable gradually:

```bash
# Initially disable all experimental features
export SOULSENSE_FF_AI_JOURNAL_SUGGESTIONS=false
export SOULSENSE_FF_ADVANCED_ANALYTICS=false
# ... etc
```

## Troubleshooting

### Flag Not Working

1. Check environment variables: `echo $SOULSENSE_FF_FLAG_NAME`
2. Check config.json experimental section
3. Verify flag name matches exactly (case-sensitive)
4. Check application logs for warnings about unknown flags

### Configuration Priority

Remember the priority order:
1. Environment variables (highest)
2. config.json
3. Default values (lowest)

Environment variables always override config file settings.

### Performance Considerations

- Flag checks are fast (in-memory operations)
- Avoid checking flags in tight loops
- Cache flag values if needed for performance-critical code

## Examples

### Conditional UI Elements

```python
def build_main_window(self):
    # Always show basic features
    self.add_journal_tab()

    if feature_flags.is_enabled("advanced_analytics"):
        self.add_analytics_tab()

    if feature_flags.is_enabled("beta_ui_components"):
        self.enable_experimental_layout()
```

### Feature-Gated API Endpoints

```python
@feature_gated("ai_journal_suggestions")
def api_get_suggestions(request):
    """API endpoint for AI suggestions."""
    text = request.json.get('text', '')
    return {'suggestions': ai_model.suggest(text)}
```

### Database Schema Changes

```python
def initialize_database():
    # Always create core tables
    create_core_tables()

    if feature_flags.is_enabled("ml_emotion_detection"):
        # Create emotion analysis tables
        create_emotion_tables()
```</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\docs\guides\feature_flags.md