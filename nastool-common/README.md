# nastool-common

Shared utilities for NASTool project.

## Contents

- `config.py` - Configuration management
- `logger.py` - Logging utilities
- `exceptions.py` - Custom exception classes
- `messages.py` - Message templates
- `constants.py` - Shared constants
- `utils/` - Utility functions

## Installation

```bash
pip install -e .
```

## Usage

```python
from nastool_common import Config, get_logger, msg

# Load configuration
config = Config.load()

# Get logger
logger = get_logger(__name__)

# Use message templates
print(msg("check_passed", check_name="CPU"))
```

## License

MIT
