# 📁 processing/import_pdf_to_db.py

import fitz  # PyMuPDF
from docx import Document  # type: ignore  # python-docx (Pylance stubs incomplete)
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Source
from datetime import datetime
import logging
from typing import List
import re

class DocumentsToDatabase:
    """Import academic documents (PDF, DOC, DOCX) to database with text extraction and validation"""

    def __init__(self):
        self.db = DBConnector()
        self.session = self.db.get_session()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for import tracking"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('document_import_log.txt'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file"""
        try:
            doc = fitz.open(pdf_path)
            text = ""

            # Extract text from all pages
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()  # type: ignore  # PyMuPDF Page.get_text() stubs incomplete
                text += page_text + "\n"

            doc.close()
            return text.strip()

        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""

    def extract_text_from_docx(self, doc_path: str) -> str:
        """Extract text content from DOCX/DOC file"""
        try:
            doc = Document(doc_path)
            text = ""

            # Extract text from all paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"

            # Also extract from tables if present
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text += cell.text + "\n"

            return text.strip()

        except Exception as e:
            self.logger.error(f"Error extracting text from DOCX/DOC {doc_path}: {e}")
            return ""

    def extract_text_from_document(self, file_path: str) -> str:
        """Route to appropriate extraction method based on file extension"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        else:
            self.logger.warning(f"Unsupported file format: {file_ext}")
            return ""

    def extract_metadata_from_filename(self, filename: str) -> dict:
        """Extract metadata from document filename"""
        metadata = {
            'title': '',
            'author': '',
            'year': None,
            'type': 'academic_paper'
        }

        # Remove extension and _data suffix
        name = Path(filename).stem.replace('_data', '')

        # Try to extract year
        year_match = re.search(r'_(\d{4})_', filename)
        if year_match:
            metadata['year'] = int(year_match.group(1))

        # Try to extract author
        if '_' in name:
            parts = name.split('_')
            if len(parts) >= 2:
                metadata['author'] = parts[0].replace('_', ' ').title()

        # Create title from filename
        title = name.replace('_', ' ').replace('data', '').strip()
        if metadata['year']:
            title = title.replace(f" {metadata['year']}", '').replace(f"_{metadata['year']}", '')

        # Clean up title
        title = re.sub(r'\s+', ' ', title).strip()
        if not title:
            title = Path(filename).stem

        metadata['title'] = title

        return metadata

    def validate_document_content(self, text: str, file_path: str) -> List[str]:
        """Validate extracted document content"""
        errors = []

        if not text or len(text.strip()) < 100:
            errors.append("Extracted text too short or empty")

        # Check for Czech/religious content keywords
        czech_keywords = ['sekta', 'hnutí', 'církev', 'náboženství', 'duchovní', 'religiozní']
        has_relevant_content = any(keyword in text.lower() for keyword in czech_keywords)

        if not has_relevant_content:
            errors.append("Content doesn't appear to be relevant (missing Czech/religious keywords)")

        return errors

    def create_source_from_document(self, file_path: str) -> bool:
        """Process single document file and create Source record"""
        try:
            doc_file = Path(file_path)
            filename = doc_file.name

            # Extract text
            self.logger.info(f"Extracting text from: {filename}")
            text = self.extract_text_from_document(file_path)

            if not text:
                self.logger.warning(f"No text extracted from {filename}")
                return False

            # Validate content
            validation_errors = self.validate_document_content(text, file_path)
            if validation_errors:
                self.logger.warning(f"Validation failed for {filename}: {', '.join(validation_errors)}")
                # Continue anyway, but log warnings

            # Extract metadata
            metadata = self.extract_metadata_from_filename(filename)

            # Determine document type from extension
            file_ext = doc_file.suffix.lower()
            source_type = "academic_doc" if file_ext in ['.doc', '.docx'] else "academic_pdf"

            # Create source record
            source = Source(
                movement_id=1,  # Default movement "Náboženské hnutí (obecně)"
                source_name=metadata['title'],
                source_type=source_type,
                author=metadata.get('author'),
                url=f"file://{file_path}",  # Local file URL
                content_full=text,
                content_excerpt=text[:500] + "..." if len(text) > 500 else text,
                publication_date=datetime.now(),
                language="cs"  # Assume Czech
            )

            # Check for duplicates
            existing = self.session.query(Source).filter(Source.url == source.url).first()
            if existing:
                self.logger.info(f"Document already exists in database: {filename}")
                return False

            self.session.add(source)
            self.session.commit()

            self.logger.info(f"✅ Successfully imported document: {filename}")
            return True

        except IntegrityError as e:
            self.session.rollback()
            self.logger.error(f"Database integrity error for {file_path}: {e}")
            return False
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing document {file_path}: {e}")
            return False

    def load_documents_to_sources(self, documents_directory: str) -> dict:
        """Load all documents (PDF, DOC, DOCX) from directory to database"""
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        docs_dir = Path(documents_directory)
        if not docs_dir.exists():
            self.logger.error(f"Documents directory does not exist: {documents_directory}")
            return stats

        # Find all supported document types
        supported_files = []
        supported_files.extend(docs_dir.glob("*.pdf"))
        supported_files.extend(docs_dir.glob("*.docx"))
        supported_files.extend(docs_dir.glob("*.doc"))

        if not supported_files:
            self.logger.warning(f"No supported document files found in {documents_directory}")
            return stats

        self.logger.info(f"Found {len(supported_files)} document files to process")

        for doc_file in supported_files:
            stats['processed'] += 1
            doc_path = str(doc_file)

            try:
                if self.create_source_from_document(doc_path):
                    stats['successful'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['failed'] += 1
                self.logger.error(f"Failed to process {doc_file.name}: {e}")
                continue

        self.session.close()
        return stats


# Backward compatibility alias
class PDFtoDatabaseLoader(DocumentsToDatabase):
    """Backward compatibility wrapper for old class name"""
    
    def load_pdfs_to_sources(self, pdf_directory: str) -> dict:
        """Backward compatibility method"""
        return self.load_documents_to_sources(pdf_directory)
