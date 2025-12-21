# 📁 processing/import_pdf_to_db.py

import fitz  # PyMuPDF
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Source
from datetime import datetime
import logging
from typing import Union, List
import re

class PDFtoDatabaseLoader:
    """Safe import of PDF academic papers to database with text extraction and validation"""

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
                logging.FileHandler('pdf_import_log.txt'),
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
                page_text = page.get_text()
                text += page_text + "\n"

            doc.close()
            return text.strip()

        except Exception as e:
            self.logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def extract_metadata_from_filename(self, filename: str) -> dict:
        """Extract metadata from PDF filename"""
        metadata = {
            'title': '',
            'author': '',
            'year': None,
            'type': 'academic_paper'
        }

        # Remove extension
        name = filename.replace('.pdf', '').replace('_data', '')

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
            title = filename.replace('.pdf', '')

        metadata['title'] = title

        return metadata

    def validate_pdf_content(self, text: str, pdf_path: str) -> List[str]:
        """Validate extracted PDF content"""
        errors = []

        if not text or len(text.strip()) < 100:
            errors.append("Extracted text too short or empty")

        # Check for Czech/religious content keywords
        czech_keywords = ['sekta', 'hnutí', 'církev', 'náboženství', 'duchovní', 'religiozní']
        has_relevant_content = any(keyword in text.lower() for keyword in czech_keywords)

        if not has_relevant_content:
            errors.append("Content doesn't appear to be relevant (missing Czech/religious keywords)")

        return errors

    def create_source_from_pdf(self, pdf_path: str) -> bool:
        """Process single PDF file and create Source record"""
        try:
            pdf_file = Path(pdf_path)
            filename = pdf_file.name

            # Extract text
            self.logger.info(f"Extracting text from: {filename}")
            text = self.extract_text_from_pdf(pdf_path)

            if not text:
                self.logger.warning(f"No text extracted from {filename}")
                return False

            # Validate content
            validation_errors = self.validate_pdf_content(text, pdf_path)
            if validation_errors:
                self.logger.warning(f"Validation failed for {filename}: {', '.join(validation_errors)}")
                # Continue anyway, but log warnings

            # Extract metadata
            metadata = self.extract_metadata_from_filename(filename)

            # Create source record
            source = Source(
                movement_id=1,  # Default movement "Náboženské hnutí (obecně)"
                source_name=metadata['title'],
                source_type="academic_pdf",
                author=metadata.get('author'),
                url=f"file://{pdf_path}",  # Local file URL
                content_full=text,
                content_excerpt=text[:500] + "..." if len(text) > 500 else text,
                publication_date=datetime.now(),
                language="cs"  # Assume Czech
            )

            # Check for duplicates
            existing = self.session.query(Source).filter(Source.url == source.url).first()
            if existing:
                self.logger.info(f"PDF already exists in database: {filename}")
                return False

            self.session.add(source)
            self.session.commit()

            self.logger.info(f"✅ Successfully imported PDF: {filename}")
            return True

        except IntegrityError as e:
            self.session.rollback()
            self.logger.error(f"Database integrity error for {pdf_path}: {e}")
            return False
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing PDF {pdf_path}: {e}")
            return False

    def load_pdfs_to_sources(self, pdf_directory: str) -> dict:
        """Load all PDF files from directory to database"""
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        pdf_dir = Path(pdf_directory)
        if not pdf_dir.exists():
            self.logger.error(f"PDF directory does not exist: {pdf_directory}")
            return stats

        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            self.logger.warning(f"No PDF files found in {pdf_directory}")
            return stats

        self.logger.info(f"Found {len(pdf_files)} PDF files to process")

        for pdf_file in pdf_files:
            stats['processed'] += 1
            pdf_path = str(pdf_file)

            try:
                if self.create_source_from_pdf(pdf_path):
                    stats['successful'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['failed'] += 1
                self.logger.error(f"Failed to process {pdf_file.name}: {e}")
                continue

        self.session.close()
        return stats
