"""Loads Pages, Announcements, Assignments and Files from a Canvas Course site."""

import tempfile
from io import BytesIO
from typing import List
from datetime import date

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from langchain.document_loaders.word_document import Docx2txtLoader
from langchain.document_loaders.excel import UnstructuredExcelLoader
from striprtf.striprtf import rtf_to_text
from langchain.document_loaders.markdown import UnstructuredMarkdownLoader

class CanvasLoader(BaseLoader):
    """Loading logic for Canvas Pages, Announcements, Assignments and Files."""

    def __init__(self, api_url: str, api_key: str = "", course_id: int = 0):
        """Initialize with API URL and api_key.

        Args:
            api_url: The canvas API URL endpoint.
            api_key: API Key or token.
        """
        self.api_url = api_url
        self.api_key = api_key
        self.course_id = course_id
        self.invalid_files = []

    def load_pages(self, course) -> List[Document]:
        from canvasapi.exceptions import CanvasException

        page_documents = []

        try:
            pages = course.get_pages(
                published=True,
                include=[ "body" ]
            )

            for page in pages:
                page_body_text = self._get_html_as_string(page.body)

                page_documents.append(Document(
                    page_content=page_body_text.strip(),
                    metadata={ "title": page.title, "kind": "page", "page_id": page.page_id }
                ))
        except CanvasException as e:
            print(e)

        return page_documents

    def load_announcements(self, canvas, course) -> List[Document]:
        from canvasapi.exceptions import CanvasException

        announcement_documents = []

        try:
            announcements = canvas.get_announcements(
                context_codes=[ course ],
                start_date="2016-01-01",
                end_date=date.today().isoformat(),
            )

            for announcement in announcements:
                page_body_text = self._get_html_as_string(announcement.message)

                announcement_documents.append(Document(
                    page_content=page_body_text,
                    metadata={ "title": announcement.title, "kind": "announcement", "announcement_id": announcement.id }
                ))
        except CanvasException as e:
            print(e)

        return announcement_documents

    def load_assignments(self, course) -> List[Document]:
        from canvasapi.exceptions import CanvasException

        assignment_documents = []

        try:
            assignments = course.get_assignments()

            for assignment in assignments:
                if assignment.description:
                    assignment_description = self._get_html_as_string(assignment.description)
                    assignment_description = f" Assignment Description: {assignment_description}\n\n"
                else:
                    assignment_description = ""

                assignment_content=f"Assignment Name: {assignment.name} \n\n Assignment Due Date: {assignment.due_at} \n\n{assignment_description}"

                assignment_documents.append(Document(
                    page_content=assignment_content,
                    metadata={ "name": assignment.name, "kind": "assignment", "assignment_id": assignment.id }
                ))
        except CanvasException as e:
            print(e)

        return assignment_documents

    def _get_html_as_string(self, html) -> str:

        try:
            # Import the html parser class
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "Could not import beautifulsoup4 python package. "
                "Please install it with `pip install beautifulsoup4`."
            )

        html_string = BeautifulSoup(html, "lxml").text.strip()

        return html_string

    def _load_text_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=False)

        return [Document(
            page_content=file_contents.strip(),
            metadata={ "filename": file.filename, "kind": "file", "file_id": file.id }
        )]

    def _load_html_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=False)

        return [Document(
            page_content=self._get_html_as_string(file_contents),
            metadata={ "filename": file.filename, "kind": "file", "file_id": file.id }
        )]

    def _load_rtf_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=False)

        return[Document(
            page_content=rtf_to_text(file_contents).strip(),
            metadata={ "filename": file.filename, "kind": "file", "file_id": file.id }
        )]

    def _load_pdf_file(self, file) -> List[Document]:
        try:
            # Import PDF parser class
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError(
                "Could not import PyPDF2 python package. "
                "Please install it with `pip install PyPDF2`."
            )

        file_contents = file.get_contents(binary=True)
        pdf_reader = PdfReader(BytesIO(file_contents))

        docs = []

        for i, page in enumerate(pdf_reader.pages):
            docs.append(Document(
                page_content=page.extract_text(),
                metadata={ "filename": file.filename, "kind": "file", "file_id": file.id, "page": i }
            ))

        return docs

    def _load_docx_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = f"{temp_dir}/{file.filename}"

            with open(file_path, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(file_contents)

            loader = Docx2txtLoader(file_path)
            docs = loader.load()

        return docs

    def _load_excel_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = f"{temp_dir}/{file.filename}"

            with open(file_path, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(file_contents)

            loader = UnstructuredExcelLoader(file_path)
            docs = loader.load()

        return docs

    def _load_md_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = f"{temp_dir}/{file.filename}"

            with open(file_path, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(file_contents)

            loader = UnstructuredMarkdownLoader(file_path)
            docs = loader.load()

        return docs

    def load_files(self, course) -> List[Document]:
        from canvasapi.exceptions import CanvasException

        file_documents = []

        allowed_content_types = [
            "text/markdown", # md
            "text/html", # htm, html
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # docx
            "application/vnd.ms-excel", # xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # xlsx
            "application/pdf", # pdf
            "text/rtf", # rtf
            "text/plain", # txt
        ]

        try:
            files = course.get_files()

            # TODO: break this up into smaller functions - also reuse with other load_AAAAAAAAA functions
            for file in files:
                file_content_type = getattr(file, "content-type")

                # print(f"New file:  {file.filename} ({file_content_type}) ({file.mime_class})")

                if file_content_type in allowed_content_types:
                    # print(f"Processing {file.filename} {file.mime_class}")

                    if file_content_type == "text/plain":
                        file_documents = file_documents + self._load_text_file(file)

                    if file_content_type == "text/html":
                        file_documents = file_documents + self._load_html_file(file)

                    elif file_content_type == "application/pdf":
                        file_documents = file_documents + self._load_pdf_file(file)

                    elif file_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        file_documents = file_documents + self._load_docx_file(file)

                    elif file_content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or file_content_type == "application/vnd.ms-excel":
                        file_documents = file_documents + self._load_excel_file(file)

                    elif file_content_type == "text/markdown":
                        file_documents = file_documents + self._load_md_file(file)

                    elif file_content_type == "text/rtf":
                        file_documents = file_documents + self._load_rtf_file(file)
                else:
                    self.invalid_files.append(f"{file.filename} ({file_content_type})")
        except CanvasException as e:
            print(e)

        return file_documents

    def load(self) -> List[Document]:
        """Load documents."""
        try:
            # Import the Canvas class
            from canvasapi import Canvas
            from canvasapi.exceptions import CanvasException
        except ImportError:
            raise ImportError(
                "Could not import canvasapi python package. "
                "Please install it with `pip install canvasapi`."
            )

        try:
            # Initialize a new Canvas object
            canvas = Canvas(self.api_url, self.api_key)

            course = canvas.get_course(self.course_id)

            # Access the course's name
            print(f"Indexing: {course.name}")
            print("")

            # Load pages
            page_documents = self.load_pages(course=course)

            # load announcements
            announcement_documents = self.load_announcements(canvas=canvas, course=course)

            # load assignments
            assignment_documents = self.load_assignments(course=course)

            # load files
            file_documents = self.load_files(course=course)

            return page_documents + announcement_documents + assignment_documents + file_documents
        except CanvasException as e:
            print(e)

        return []