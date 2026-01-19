
import pytest
import os
import tempfile
from app.utils.file_validation import validate_file_path, sanitize_filename
from app.exceptions import ValidationError

class TestFileValidation:
    
    def test_sanitize_filename_basics(self):
        assert sanitize_filename("safe_file.txt") == "safe_file.txt"
        assert sanitize_filename("File Name with Spaces.pdf") == "File Name with Spaces.pdf"
        assert sanitize_filename("invalid/slashes.txt") == "invalidslashes.txt"
        assert sanitize_filename("weird:chars?.txt") == "weirdchars.txt"
    
    def test_sanitize_filename_reserved_windows(self):
        assert sanitize_filename("CON.txt") == "_CON.txt"
        assert sanitize_filename("prn") == "_prn"
        assert sanitize_filename("Aux.json") == "_Aux.json"
        
    def test_sanitize_filename_empty(self):
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename("   ") == "unnamed_file"
        assert sanitize_filename("///") == "unnamed_file"

    def test_validate_path_extensions(self):
        # Valid
        assert validate_file_path("test.json", allowed_extensions=[".json"])
        assert validate_file_path("test.JSON", allowed_extensions=[".json"])
        
        # Invalid
        with pytest.raises(ValidationError, match="Invalid file extension"):
            validate_file_path("test.txt", allowed_extensions=[".json"])

    def test_validate_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_dir = os.path.join(tmpdir, "safe")
            os.makedirs(safe_dir)
            
            # Safe path
            valid_path = os.path.join(safe_dir, "file.txt")
            assert validate_file_path(valid_path, base_dir=safe_dir) == os.path.realpath(valid_path)
            
            # Traversal attempt
            outside_path = os.path.join(tmpdir, "secret.txt")
            with pytest.raises(ValidationError, match="Access denied"):
                validate_file_path(outside_path, base_dir=safe_dir)
                
            # Relative traversal attempt
            relative_traversal = os.path.join(safe_dir, "..", "secret.txt")
            with pytest.raises(ValidationError, match="Access denied"):
                validate_file_path(relative_traversal, base_dir=safe_dir)

    def test_validate_path_existence(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            path = tf.name
        
        try:
            # Should pass
            validate_file_path(path, must_exist=True)
            
            # Should fail
            with pytest.raises(ValidationError, match="File not found"):
                validate_file_path(path + ".missing", must_exist=True)
        finally:
            if os.path.exists(path):
                os.remove(path)
