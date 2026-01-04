# ===----------------------------------------------------------------------=== #
#
# This source file is part of the S.O.K open source project
#
# Copyright (c) 2026 S.O.K Team
# Licensed under the MIT License
#
# See LICENSE for license information
#
# ===----------------------------------------------------------------------=== #
"""
File operations for electronic books.

This module handles:
- Detection and extraction of information from ebook file names
- Reading metadata (EPUB, MOBI, PDF)
- Automatic renaming
- Organization by author/series
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from sok.core.interfaces import FileOperations, MediaItem
from sok.core.utils import format_name
from sok.file_operations.base_operations import FileParsingMixin, FileValidationMixin
import zipfile
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class BookFileOperations(FileOperations, FileParsingMixin, FileValidationMixin):
    """File operations for electronic books.

    Provides methods to extract metadata from ebook filenames,
    read embedded metadata (EPUB, MOBI, PDF), organize by
    author/series, and rename according to book conventions.
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported ebook file extensions.

        Returns:
            List of lowercase extensions including epub, mobi, pdf, etc.
        """
        return [
            ".epub",
            ".mobi",
            ".azw",
            ".azw3",
            ".pdf",
            ".djvu",
            ".fb2",
            ".cbz",
            ".cbr",
            ".lit",
            ".pdb",
            ".txt",
            ".rtf",
            ".doc",
            ".docx",
        ]

    def extract_info_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extract information from an ebook filename.

        Supports formats:
        - 'Author - Title.epub'
        - 'Author - [Series 01] - Title.epub'
        - 'Title - Author.epub'
        - 'Author - Title (2023).epub'

        Args:
            filename: File name to parse.

        Returns:
            Dictionary with extracted information.
        """
        info: Dict[str, Any] = {
            "original_filename": filename,
            "extension": os.path.splitext(filename)[1].lower(),
            "author": None,
            "title": None,
            "series": None,
            "series_number": None,
            "year": None,
            "publisher": None,
            "isbn": None,
            "language": None,
        }

        name_without_ext = os.path.splitext(filename)[0]

        pattern_series = r"^(?P<author>[^-\[]+)\s*-\s*\[(?P<series>[^\]]+?)\s+(?P<number>\d+)\]\s*-\s*(?P<title>.+)$"
        match = re.match(pattern_series, name_without_ext)

        if match:
            info["author"] = match.group("author").strip()
            info["series"] = match.group("series").strip()
            info["series_number"] = int(match.group("number"))
            info["title"] = match.group("title").strip()
            return info

        pattern_year = r"^(?P<author>[^-]+)\s*-\s*(?P<title>.+?)\s*\((?P<year>\d{4})\)$"
        match = re.match(pattern_year, name_without_ext)

        if match:
            info["author"] = match.group("author").strip()
            info["title"] = match.group("title").strip()
            info["year"] = int(match.group("year"))
            return info

        pattern_standard = r"^(?P<author>[^-]+)\s*-\s*(?P<title>.+)$"
        match = re.match(pattern_standard, name_without_ext)

        if match:
            parts = [p.strip() for p in name_without_ext.split("-", 1)]
            if len(parts) == 2:
                if self._looks_like_author(parts[0]):
                    info["author"] = parts[0]
                    info["title"] = parts[1]
                else:
                    info["title"] = parts[0]
                    info["author"] = parts[1]
            return info

        info["title"] = name_without_ext.strip()

        return info

    def _looks_like_author(self, text: str) -> bool:
        """Determines if text looks like an author name"""
        words = text.split()
        if len(words) < 2 or len(words) > 4:
            return False

        return all(word[0].isupper() for word in words if word)

    def read_metadata(self, file_path: str) -> Dict[str, Any]:
        """Read metadata from an ebook file.

        Args:
            file_path: Ebook file path.

        Returns:
            Dictionary with read metadata.
        """
        metadata: Dict[str, Any] = {
            "title": None,
            "author": None,
            "authors": [],
            "publisher": None,
            "published_date": None,
            "year": None,
            "language": None,
            "isbn": None,
            "description": None,
            "series": None,
            "series_number": None,
            "page_count": None,
        }

        extension = os.path.splitext(file_path)[1].lower()

        try:
            if extension == ".epub":
                metadata.update(self._read_epub_metadata(file_path))
            elif extension == ".pdf":
                metadata.update(self._read_pdf_metadata(file_path))
            elif extension in [".mobi", ".azw", ".azw3"]:
                pass
        except (OSError, ValueError) as e:
            logger.exception("Metadata reading error %s", file_path, exc_info=e)

        return metadata

    def _read_epub_metadata(self, file_path: str) -> Dict[str, Any]:
        """Reads metadata from an EPUB file"""
        metadata: Dict[str, Any] = {}

        try:
            with zipfile.ZipFile(file_path, "r") as epub:
                # Find the content.opf file
                for name in epub.namelist():
                    if name.endswith(".opf") or "content.opf" in name:
                        opf_content = epub.read(name)

                        # Parse the XML
                        root = ET.fromstring(opf_content)

                        ns = {
                            "dc": "http://purl.org/dc/elements/1.1/",
                            "opf": "http://www.idpf.org/2007/opf",
                        }

                        title_elem = root.find(".//dc:title", ns)
                        if title_elem is not None:
                            metadata["title"] = title_elem.text

                        authors = root.findall(".//dc:creator", ns)
                        if authors:
                            metadata["authors"] = [
                                a.text for a in authors if a is not None and a.text
                            ]
                            metadata["author"] = (
                                metadata["authors"][0] if metadata["authors"] else None
                            )

                        publisher_elem = root.find(".//dc:publisher", ns)
                        if publisher_elem is not None:
                            metadata["publisher"] = publisher_elem.text

                        date_elem = root.find(".//dc:date", ns)
                        if date_elem is not None and date_elem.text:
                            metadata["published_date"] = date_elem.text
                            year_match = re.search(r"\d{4}", date_elem.text)
                            if year_match:
                                metadata["year"] = int(year_match.group())

                        lang_elem = root.find(".//dc:language", ns)
                        if lang_elem is not None:
                            metadata["language"] = lang_elem.text

                        identifiers = root.findall(".//dc:identifier", ns)
                        for ident in identifiers:
                            if ident.text and (
                                "isbn" in ident.text.lower()
                                or (
                                    ident.get("{http://www.idpf.org/2007/opf}scheme")
                                    or ""
                                ).lower()
                                == "isbn"
                            ):
                                metadata["isbn"] = re.sub(
                                    r"[^0-9X]", "", ident.text.upper()
                                )

                        desc_elem = root.find(".//dc:description", ns)
                        if desc_elem is not None:
                            metadata["description"] = desc_elem.text

                        break

        except ImportError:
            return metadata
        except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as e:
            logger.exception("Erreur lecture EPUB %s", file_path, exc_info=e)

        return metadata

    def _read_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Reads metadata from a PDF file"""
        metadata: Dict[str, Any] = {}

        try:
            # Utilise PyPDF2 ou pdfplumber si disponible
            try:
                reader = PdfReader(file_path)
                info = reader.metadata

                if info:
                    if info.title:
                        metadata["title"] = info.title
                    if info.author:
                        metadata["author"] = info.author
                        metadata["authors"] = [info.author]
                    if info.subject:
                        metadata["description"] = info.subject

                    # Page count
                    metadata["page_count"] = len(reader.pages)

            except ImportError:
                # PyPDF2 is not installed
                return metadata

        except (OSError, ValueError) as e:
            logger.exception("Error reading PDF %s", file_path, exc_info=e)

        return metadata

    def generate_new_filename(
        self, media_item: Optional[MediaItem], original_filename: str
    ) -> str:
        """Generate a new filename for a book.

        Format: 'Author - Title.epub' or 'Author - [Series 01] - Title.epub'

        Args:
            media_item: The media item (Book).
            original_filename: Original filename.

        Returns:
            New filename.
        """
        info = self.extract_info_from_filename(original_filename)
        extension = info["extension"]

        if not info["author"] or not info["title"]:
            return original_filename

        author = format_name(info["author"])
        title = format_name(info["title"])

        if info["series"] and info["series_number"]:
            series = format_name(info["series"])
            num = str(info["series_number"]).zfill(2)
            return f"{author} - [{series} {num}] - {title}{extension}"
        elif info["year"]:
            return f"{author} - {title} ({info['year']}){extension}"
        else:
            return f"{author} - {title}{extension}"

    def organize_by_author(
        self,
        source_path: str,
        dest_path: str,
        use_metadata: bool = True,
        group_series: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Organize ebook files by Author (and optionally by series).

        Created structure:
        - Author/Book.epub (if no series)
        - Author/Series/Book.epub (if series)

        Args:
            source_path: Source folder.
            dest_path: Destination folder.
            use_metadata: Use file metadata.
            group_series: Group books from the same series.
            dry_run: Simulation mode.

        Returns:
            Organization report.
        """
        report: Dict[str, Any] = {
            "moved": [],
            "errors": [],
            "total_files": 0,
            "total_moved": 0,
            "authors": set(),
            "series": set(),
        }

        for root, dirs, files in os.walk(source_path):
            for file in files:
                if not any(
                    file.lower().endswith(ext) for ext in self.supported_extensions
                ):
                    continue

                report["total_files"] += 1
                source_file = os.path.join(root, file)

                # Determine author and series
                author = "Unknown Author"
                series = None

                if use_metadata:
                    metadata = self.read_metadata(source_file)
                    if metadata.get("author"):
                        author = metadata["author"]
                    if group_series and metadata.get("series"):
                        series = metadata["series"]
                else:
                    # Use filename
                    info = self.extract_info_from_filename(file)
                    if info["author"]:
                        author = info["author"]
                    if group_series and info["series"]:
                        series = info["series"]

                # Create destination path
                author_folder = format_name(author)

                if series:
                    series_folder = format_name(series)
                    dest_folder = os.path.join(dest_path, author_folder, series_folder)
                    report["series"].add(f"{author} - {series}")
                else:
                    dest_folder = os.path.join(dest_path, author_folder)

                # Generate new filename
                new_filename = self.generate_new_filename(None, file)
                dest_file = os.path.join(dest_folder, new_filename)

                # Move the file
                if not dry_run:
                    try:
                        os.makedirs(dest_folder, exist_ok=True)
                        os.rename(source_file, dest_file)
                        report["moved"].append({"from": source_file, "to": dest_file})
                        report["total_moved"] += 1
                        report["authors"].add(author)
                    except OSError as e:
                        logger.exception(
                            "Book organize move failed for %s", source_file, exc_info=e
                        )
                        report["errors"].append({"file": source_file, "error": str(e)})
                else:
                    report["moved"].append({"from": source_file, "to": dest_file})
                    report["total_moved"] += 1
                    report["authors"].add(author)

        # Convert sets to lists
        report["authors"] = sorted(list(report["authors"]))
        report["series"] = sorted(list(report["series"]))

        return report

    def find_book_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Find all ebook files in a directory.

        Args:
            directory: Directory to scan.
            recursive: Enable recursive search.

        Returns:
            List of ebook file paths.
        """
        return self.get_files_by_extension(
            directory, self.supported_extensions, recursive
        )

    def find_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Unified alias for find_book_files."""
        return self.find_book_files(directory, recursive)
