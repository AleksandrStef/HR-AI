"""
Unit tests for HR AI document parser.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Add src to path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hr_ai.parsers.document_parser import DocumentParser, DocumentParseError

class TestDocumentParser:
    """Test cases for DocumentParser."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.parser = DocumentParser(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_employee_name(self):
        """Test employee name extraction from filename."""
        test_cases = [
            ("Иван Петров - Employee development plan.docx", "Иван Петров"),
            ("John Smith - План развития сотрудника.docx", "John Smith"),
            ("Darina Lebedeva - Employee development plan.docx", "Darina Lebedeva"),
            ("test.docx", "test")
        ]
        
        for filename, expected in test_cases:
            result = self.parser._extract_employee_name(filename)
            assert result == expected, f"Expected {expected}, got {result}"
    
    def test_detect_section_header(self):
        """Test section header detection."""
        test_cases = [
            ("Plans before the Performance review", "plans_before_review"),
            ("Performance Review - 08/06/2025", "performance_review"),
            ("Quarterly Check-Point", "quarterly_checkpoint"),
            ("Планы до ревью", "plans_before_review"),
            ("Random text", None)
        ]
        
        for text, expected in test_cases:
            result = self.parser._detect_section_header(text)
            assert result == expected, f"Expected {expected}, got {result}"
    
    def test_extract_dates(self):
        """Test date extraction from text."""
        test_lines = [
            "Meeting scheduled for 25.12.2024",
            "Performance review on 2025-01-15",
            "Next checkpoint: 15 января 2025",
            "No dates here"
        ]
        
        dates = self.parser._extract_dates(test_lines)
        assert len(dates) >= 2, "Should find at least 2 dates"
        
        # Check that dates contain required fields
        for date_info in dates:
            assert 'date_string' in date_info
            assert 'context' in date_info
    
    def test_scan_directory_empty(self):
        """Test scanning empty directory."""
        files_info = self.parser.scan_directory()
        assert files_info == [], "Empty directory should return empty list"
    
    def test_unsupported_file_extension(self):
        """Test handling of unsupported file extensions."""
        # Create a text file in temp directory
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("This is a text file")
        
        with pytest.raises(DocumentParseError):
            self.parser.parse_document(str(test_file))
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        fake_file = Path(self.temp_dir) / "nonexistent.docx"
        
        with pytest.raises(DocumentParseError):
            self.parser.parse_document(str(fake_file))
    
    def test_get_recently_modified_files(self):
        """Test getting recently modified files."""
        # This test would need actual files to be meaningful
        recent_files = self.parser.get_recently_modified_files(days=1)
        assert isinstance(recent_files, list)

if __name__ == "__main__":
    pytest.main([__file__])