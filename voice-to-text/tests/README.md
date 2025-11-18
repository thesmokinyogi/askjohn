# Tests Directory

This directory contains test scripts for the voice-to-text application.

## Structure

- **Root level**: Production-ready test scripts (e.g., `test_end_to_end.py`, `test_dynamic_config.py`)
- **observation/**: Observation and exploration scripts used during development

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run end-to-end test
python tests/test_end_to_end.py

# Run dynamic config test
python tests/test_dynamic_config.py
```

## Observation Scripts

Scripts in `observation/` were used during development to understand API behavior and are kept for reference:
- `debug_metadata_discovery.py`: Initial metadata discovery exploration
- `test_rest_api_approach.py`: REST API approach validation
- `test_sdk_locations.py`: SDK location discovery testing
- `test_resource_manager_locations.py`: Resource Manager API testing
- `test_cache_structure.py`: Cache structure examination
- `observe_proto_plus.py`: Protobuf conversion observation

