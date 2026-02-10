"""Tests for enhanced PDF document import functionality"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from processing.import_pdf_to_db import DocumentsToDatabase


class TestTextPreprocessing:
    """Test text preprocessing functionality"""
    
    def test_preprocess_text_removes_page_numbers(self):
        """Should remove page numbers from text"""
        importer = DocumentsToDatabase()
        text = "First paragraph\n- 5 -\nSecond paragraph"
        result = importer.preprocess_text(text)
        assert "- 5 -" not in result
        assert "First paragraph" in result
        assert "Second paragraph" in result

    def test_preprocess_text_removes_hyphenated_line_breaks(self):
        """Should join hyphenated words broken across lines"""
        importer = DocumentsToDatabase()
        text = "This is a hypo-\nthetical example"
        result = importer.preprocess_text(text)
        # The regex removes the hyphen and newline, joining into 'hypothetical'
        assert "hypothetical" in result

    def test_preprocess_text_normalizes_whitespace(self):
        """Should collapse multiple spaces into single space"""
        importer = DocumentsToDatabase()
        text = "Multiple   spaces    and\n\nnewlines"
        result = importer.preprocess_text(text)
        assert "   " not in result  # Multiple spaces removed
        assert result.count(' ') < text.count(' ')

    def test_preprocess_text_strips_edges(self):
        """Should strip leading and trailing whitespace"""
        importer = DocumentsToDatabase()
        text = "   Some text   \n\n"
        result = importer.preprocess_text(text)
        assert result == result.strip()


class TestContentHashing:
    """Test content hashing for duplicate detection"""
    
    def test_calculate_content_hash_produces_consistent_hash(self):
        """Same text should produce same hash"""
        importer = DocumentsToDatabase()
        text = "This is test content about sekta"
        hash1 = importer.calculate_content_hash(text)
        hash2 = importer.calculate_content_hash(text)
        assert hash1 == hash2

    def test_calculate_content_hash_different_for_different_text(self):
        """Different text should produce different hash"""
        importer = DocumentsToDatabase()
        hash1 = importer.calculate_content_hash("Text A")
        hash2 = importer.calculate_content_hash("Text B")
        assert hash1 != hash2

    def test_calculate_content_hash_is_sha256(self):
        """Hash should be SHA256 format (64 hex chars)"""
        importer = DocumentsToDatabase()
        hash_result = importer.calculate_content_hash("test")
        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result)


class TestWordCount:
    """Test word counting functionality"""
    
    def test_calculate_word_count_basic(self):
        """Should count words correctly"""
        importer = DocumentsToDatabase()
        text = "one two three"
        assert importer.calculate_word_count(text) == 3

    def test_calculate_word_count_with_punctuation(self):
        """Should count words with punctuation"""
        importer = DocumentsToDatabase()
        text = "one, two. three!"
        assert importer.calculate_word_count(text) == 3

    def test_calculate_word_count_empty_string(self):
        """Should return 0 for empty string"""
        importer = DocumentsToDatabase()
        assert importer.calculate_word_count("") == 0


class TestReadingTime:
    """Test reading time calculation"""
    
    def test_calculate_reading_time_basic(self):
        """Should calculate reading time at ~200 words per minute"""
        importer = DocumentsToDatabase()
        # 200 words = 1 minute
        assert importer.calculate_reading_time(200) == 1
        # 400 words = 2 minutes
        assert importer.calculate_reading_time(400) == 2

    def test_calculate_reading_time_minimum_one_minute(self):
        """Should always return at least 1 minute"""
        importer = DocumentsToDatabase()
        assert importer.calculate_reading_time(0) == 1
        assert importer.calculate_reading_time(50) == 1


class TestContentValidation:
    """Test document content validation"""
    
    def test_validate_document_content_rejects_empty_text(self):
        """Should reject empty or very short text"""
        importer = DocumentsToDatabase()
        is_valid, errors = importer.validate_document_content("", "test.pdf")
        assert not is_valid
        assert any("too short" in err.lower() for err in errors)

    def test_validate_document_content_rejects_no_keywords(self):
        """Should reject content without religious keywords"""
        importer = DocumentsToDatabase()
        text = "This is about cooking recipes and sports" * 20  # Make it long enough
        is_valid, errors = importer.validate_document_content(text, "test.pdf")
        assert not is_valid
        assert any("relevant" in err.lower() for err in errors)

    def test_validate_document_content_accepts_valid_content(self):
        """Should accept content with religious keywords"""
        importer = DocumentsToDatabase()
        text = "This is about sekta and church and náboženství" * 20  # Long + keywords
        is_valid, errors = importer.validate_document_content(text, "test.pdf")
        assert is_valid


class TestMetadataExtraction:
    """Test metadata extraction from filenames"""
    
    def test_extract_metadata_from_filename_basic(self):
        """Should extract basic metadata from filename"""
        importer = DocumentsToDatabase()
        metadata = importer.extract_metadata_from_filename("Smith_2022_Religious_Movements.pdf")
        assert metadata['author'] == "Smith"
        assert metadata['year'] == 2022

    def test_extract_metadata_from_filename_no_year(self):
        """Should handle filename without year"""
        importer = DocumentsToDatabase()
        metadata = importer.extract_metadata_from_filename("Smith_Religious_Study.pdf")
        assert metadata['author'] == "Smith"
        assert metadata['year'] is None

    def test_extract_metadata_creates_title_from_filename(self):
        """Should create title from filename"""
        importer = DocumentsToDatabase()
        metadata = importer.extract_metadata_from_filename("John_Doe_2020_Religious_Movements_Study.pdf")
        assert "Religious" in metadata['title'] or "religious" in metadata['title'].lower()


@patch('processing.import_pdf_to_db.fitz')
def test_extract_pdf_metadata(mock_fitz):
    """Should extract PDF document properties"""
    importer = DocumentsToDatabase()
    
    # Mock PyMuPDF
    mock_doc = MagicMock()
    mock_doc.metadata = {
        'title': 'Test Document',
        'author': 'Test Author',
        'subject': 'Religious Movement'
    }
    mock_fitz.open.return_value = mock_doc
    
    metadata = importer.extract_pdf_metadata("test.pdf")
    assert metadata['title'] == 'Test Document'
    assert metadata['author'] == 'Test Author'


class TestMatchMovement:
    """Test movement matching by content"""
    
    @pytest.mark.skip(reason="Requires complex database mocking; tested in integration tests")
    @patch('processing.import_pdf_to_db.DBConnector')
    def test_match_movement_from_text(self, mock_db_class):
        """Should match movement based on content"""
        importer = DocumentsToDatabase()
        
        # This test is complex because it requires mocking the entire
        # Movement model with proper SQLAlchemy attributes
        # Skipping in favor of integration tests
        pass

    @patch('processing.import_pdf_to_db.DBConnector')
    def test_match_movement_returns_none_on_error(self, mock_db_class):
        """Should return None if matching fails"""
        importer = DocumentsToDatabase()
        mock_db_class.side_effect = Exception("DB error")
        
        result = importer.match_movement("some text")
        assert result is None


class TestLoadDocumentsIntegration:
    """Integration tests for loading documents"""
    
    def test_load_documents_with_empty_directory(self):
        """Should handle empty directory gracefully"""
        importer = DocumentsToDatabase()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            stats = importer.load_documents_to_sources(tmpdir)
            
            assert stats['processed'] == 0
            assert stats['successful'] == 0
            assert stats['skipped'] == 0

    def test_load_documents_with_nonexistent_directory(self):
        """Should handle nonexistent directory gracefully"""
        importer = DocumentsToDatabase()
        stats = importer.load_documents_to_sources("/nonexistent/path")
        
        assert stats['processed'] == 0
        assert 'successful' in stats


class TestPDFBackwardCompatibility:
    """Test backward compatibility wrapper"""
    
    def test_pdftodatabaseloader_alias_exists(self):
        """PDFtoDatabaseLoader class should exist for backward compatibility"""
        from processing.import_pdf_to_db import PDFtoDatabaseLoader
        loader = PDFtoDatabaseLoader()
        assert hasattr(loader, 'load_pdfs_to_sources')

    def test_pdftodatabaseloader_delegates_to_new_method(self):
        """PDFtoDatabaseLoader.load_pdfs_to_sources should delegate"""
        from processing.import_pdf_to_db import PDFtoDatabaseLoader
        loader = PDFtoDatabaseLoader()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise
            stats = loader.load_pdfs_to_sources(tmpdir)
            assert isinstance(stats, dict)
