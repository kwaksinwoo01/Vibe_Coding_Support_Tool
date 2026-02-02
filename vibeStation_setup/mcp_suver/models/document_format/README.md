# Document Format Module Guide

This directory contains all modules related to document formatting, templating, and validation for the 6-tier task orchestration system.

## Overview

The `document_format` module consolidates all format-related functionality into a single, well-organized location. This makes it easier to locate, understand, and customize template-related code.

## Module Structure

### Key Modules

#### 1. `templates.py`
Defines WPD template structures for all grades (L0-L3).

**Responsibilities:**
- Define required sections for each WPD grade
- Provide section descriptions for template generation
- Maintain template registry for easy access

**Classes:**
- `wpd_0_template`: L0 (Main Work Plan Document) template
- `wpd_1_template`: L1 (Executive Level) template
- `wpd_2_template`: L2 (Phase Level) template
- `wpd_3_template`: L3 (Subphase Level) template

**Functions:**
- `get_template_for_grade(grade)`: Get template class for a specific grade
- `get_required_sections(grade)`: Get required sections for a specific grade

#### 2. `template_renderer.py`
Renders templates into Markdown content with data injection.

**Responsibilities:**
- Render WPD templates with TierAState data
- Generate template structure from template classes
- Format metadata and sections

**Functions:**
- `render_wpd_template(grade, tier_a_state)`: Main rendering function
- `generate_template_structure(template_class, state)`: Generate basic structure

#### 3. `template_validators.py`
Validates template structure and ensures required sections are present.

**Responsibilities:**
- Validate template structure compliance
- Check for required sections
- Report validation errors

**Functions:**
- `validate_template_structure(content, grade)`: Validate overall structure
- `validate_required_sections(content, grade)`: Check required sections
- `get_required_sections_for_grade(grade)`: Get required sections for validation

#### 4. `document_serializer.py`
Serializes and deserializes WPDDocument objects.

**Responsibilities:**
- Convert WPDDocument to/from dictionary format
- Handle JSON serialization
- Preserve document metadata and hierarchy

#### 5. `document_converters.py`
Converts between WPDDocument and tier state representations.

**Responsibilities:**
- Convert TierAState to WPDDocument
- Convert WPDDocument to TierEState
- Handle state transitions

#### 6. `document_builder.py`
Builds WPDDocument instances with validation.

**Responsibilities:**
- Construct WPDDocument objects
- Validate document metadata
- Build document hierarchy

#### 7. `template_builder.py`
Builds template instances for specific use cases.

**Responsibilities:**
- Create template instances
- Apply customizations
- Return ready-to-use templates

## Customizing Templates

### How to Customize Templates

To customize WPD templates for your specific needs:

1. **Edit Template Structure** (`templates.py`):
   ```python
   # Example: Add a new required section to L1 template
   class wpd_1_template:
       REQUIRED_SECTIONS = [
           "## 📋 Executive Summary",
           "## 🎯 Goals and Success Criteria",
           "## Execution Plan",
           "## 📝 Risk Assessment",  # New section
           "## References",
       ]
       
       SECTION_DESCRIPTIONS = {
           ...
           "## 📝 Risk Assessment": "Identify and assess project risks",
       }
   ```

2. **Test Validation** (`template_validators.py`):
   ```python
   # Run validation to ensure compliance
   errors = validate_template_structure(content, "L1")
   if errors:
       print("Validation errors:", errors)
   ```

3. **Test Rendering** (`template_renderer.py`):
   ```python
   # Render template with your changes
   content = render_wpd_template("L1", tier_a_state)
   print(content)
   ```

4. **Update Tests**:
   - Run existing tests to ensure no regressions
   - Add new tests for custom sections if needed

### Common Customization Scenarios

#### Scenario 1: Add a New Section
```python
# In templates.py, modify REQUIRED_SECTIONS and SECTION_DESCRIPTIONS
REQUIRED_SECTIONS = [..., "## New Section"]
SECTION_DESCRIPTIONS = {..., "## New Section": "Description"}
```

#### Scenario 2: Modify Section Descriptions
```python
# Update SECTION_DESCRIPTIONS only
SECTION_DESCRIPTIONS = {
    "## 📋 Executive Summary": "Updated description here",
    ...
}
```

#### Scenario 3: Add a New Template Grade
```python
# In templates.py, create new template class
class wpd_4_template:
    GRADE = "L4"
    REQUIRED_SECTIONS = [...]
    SECTION_DESCRIPTIONS = {...}

# Add to registry
WPD_TEMPLATES["L4"] = wpd_4_template
```

## Field Addition Rules

When adding new fields to templates or documents, follow these **non-overlapping guidelines** to maintain code clarity and prevent redundancy:

### Rules

#### Rule 1: Prohibit Overlapping Fields with Same Value, Different Destinations
**Do NOT** create multiple fields that store the same value but serve different purposes.

❌ **Bad Example:**
```python
class BadExample:
    user_id_for_auth = "user123"      # Same value
    user_id_for_logging = "user123"   # Different purpose
```

✅ **Good Example:**
```python
class GoodExample:
    user_id = "user123"  # Single field, multiple uses
```

#### Rule 2: Consolidate Same-Destination, Different-Type Fields into Lists
For the same destination but different value types, use a **single list field**.

❌ **Bad Example:**
```python
class BadExample:
    error_code_int = 404
    error_code_str = "NOT_FOUND"
    error_code_enum = ErrorType.NOT_FOUND
```

✅ **Good Example:**
```python
class GoodExample:
    error_codes = [404, "NOT_FOUND", ErrorType.NOT_FOUND]  # List of different types
```

#### Rule 3: Use Single Field for Message-Type Data
For message-type data, use a **single field** with type differentiation (not overlapping, allow detailed distinction).

❌ **Bad Example:**
```python
class BadExample:
    info_message = "Info"
    warning_message = "Warning"
    error_message = "Error"
```

✅ **Good Example:**
```python
class GoodExample:
    message = {"type": "error", "text": "Error occurred"}
```

#### Rule 4: Fields in Different Classes Are Not Overlapping
Fields with the same name/type in different classes are **not considered overlapping**.

✅ **Allowed:**
```python
class ClassA:
    file_id = "abc123"

class ClassB:
    file_id = "xyz789"  # OK - different class
```

### Field Count Limits

- **Minimum**: 1 field (e.g., `auto_resolve_flag`)
- **Maximum**: 10 fields per class/template
- **Ensure**: No role overlap with existing fields

### Field Naming Conventions

- Use **snake_case** for field names
- Be **descriptive** and **specific**
- Avoid **abbreviations** unless widely understood
- Use **consistent naming** across similar fields

Examples:
- ✅ `document_title`, `wpd_grade`, `creation_timestamp`
- ❌ `doc_ttl`, `grade`, `ts`

## Testing

### Running Tests

```bash
# From the tool directory
cd .github/agents/tool

# Run all tests
python -m pytest tests/

# Run specific tests for document format
python -m pytest tests/ -k "template or document"
```

### Test Coverage

Ensure the following are tested:
- Template structure validation
- Template rendering with various states
- Document serialization/deserialization
- Document conversion between states
- Field validation and overlap detection

## Strategy Pattern Compliance

All modules follow the **Strategy Pattern** for extensibility:

- **Template Rendering**: Different rendering strategies for different grades
- **Validation**: Pluggable validation strategies
- **Conversion**: Extensible converters for different state types

### Example: Adding a New Rendering Strategy

```python
# In template_renderer.py
class CustomRenderingStrategy:
    def render(self, template_class, state):
        # Custom rendering logic
        pass

# Register strategy
RENDERING_STRATEGIES["custom"] = CustomRenderingStrategy()
```

## Migration from Old Structure

If you have code importing from the old locations, update as follows:

```python
# OLD
from models.core.templates import wpd_1_template
from models.formatters.template_renderer import render_wpd_template
from models.validators.template_validators import validate_template_structure

# NEW
from models.document_format.templates import wpd_1_template
from models.document_format.template_renderer import render_wpd_template
from models.document_format.template_validators import validate_template_structure

# OR use convenience imports
from models.document_format import (
    wpd_1_template,
    render_wpd_template,
    validate_template_structure,
)
```

## Best Practices

1. **Single Responsibility**: Each module has one clear purpose
2. **Open/Closed Principle**: Extend functionality without modifying existing code
3. **DRY (Don't Repeat Yourself)**: Reuse common logic across modules
4. **Clear Naming**: Use descriptive names for functions and classes
5. **Comprehensive Documentation**: Document all public APIs
6. **Test Coverage**: Maintain high test coverage for all modules

## Troubleshooting

### Issue: Template validation fails after customization

**Solution**: Check that all required sections are present and correctly formatted. Use `validate_template_structure()` to identify missing sections.

### Issue: Rendering produces incorrect output

**Solution**: Verify that the template class has correct `REQUIRED_SECTIONS` and `SECTION_DESCRIPTIONS`. Check that TierAState has the expected metadata.

### Issue: Import errors after refactoring

**Solution**: Update all import statements to use the new `models.document_format` path. Use the `__init__.py` convenience imports when possible.

## Contributing

When contributing to this module:

1. Follow the field addition rules strictly
2. Maintain Strategy Pattern compliance
3. Add tests for new functionality
4. Update this README with new features
5. Ensure backward compatibility or document breaking changes

## Support

For questions or issues:
1. Check this README first
2. Review module docstrings
3. Check test files for usage examples
4. Consult the main project documentation

---

**Last Updated**: 2026-01-18
**Module Version**: 1.0.0
**Maintainer**: Dropbox Automation Team
