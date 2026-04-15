# data/__init__.py
# Device profile data module
# Re-exports ProfileManager for backward compatibility with core/config_loader.py
try:
    from data.mock_results import ProfileManager
except ImportError:
    ProfileManager = None
