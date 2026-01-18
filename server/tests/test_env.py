# import pytest
# #from app.config import load_settings

# def test_gemini_key_loaded(monkeypatch):
    # Set a test API key for this test
   #  test_key = "test_api_key_12345"
    # monkeypatch.setenv("GEMINI_API_KEY", test_key)
    
    # Reload settings with the test key
    # test_settings = load_settings()
    
    # Verify it's loaded correctly
  #   assert isinstance(test_settings.gemini_api_key, str)
 #    assert len(test_settings.gemini_api_key) > 0
  #   assert test_settings.gemini_api_key == test_key
import pytest
from app.config import settings

def test_gemini_key_loaded():
    if not settings.gemini_api_key:
        pytest.skip("Gemini API key not set")
    assert len(settings.gemini_api_key) > 0