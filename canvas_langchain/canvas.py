"""Loads Pages, Announcements, Assignments and Files from a Canvas Course site."""
import json
import logging
import os
import tempfile
from datetime import date, datetime
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytz
from LangChainKaltura import KalturaCaptionLoader
from LangChainKaltura.MiVideoAPI import MiVideoAPI
from bs4 import BeautifulSoup, PageElement, ResultSet
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain_community.document_loaders import UnstructuredURLLoader
from pydantic import BaseModel
from striprtf.striprtf import rtf_to_text
from typing import Any, List, Literal

logger = logging.getLogger(__name__)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class LogStatement(BaseModel):
    """
    INFO can be user-facing statements, non-technical and perhaps very high-level
    """
    message: Any
    level: Literal['INFO', 'DEBUG', 'WARNING']

    def __json__(self):
        return {
            'message': self.message,
            'level': self.level,
        }

class CanvasLoader(BaseLoader):
    """Loading logic for Canvas Pages, Announcements, Assignments and Files."""

    def __init__(self, api_url: str, api_key: str = "", course_id: int = 0, index_external_urls: bool = False):
        """Initialize with API URL and api_key.

        Args:
            api_url: The canvas API URL endpoint.
            api_key: API Key or token.
            course_id: Course ID we want to return documents from
            index_external_urls: Whether to try and index ExternalUrls in modules - defauls is false
        """
        self.canvas = None  # TODO: Initialize
        self.canvas_user_id = None  # TODO: Initialize
        self.api_url = api_url
        self.api_key = api_key
        self.course_id = course_id
        self.returned_course_id = 0
        self.index_external_urls = index_external_urls

        self.invalid_files = []
        self.indexed_items = []

        self.errors = []
        self.progress = []

    def _get_syllabus_url(self) -> str:
        return f"{self.api_url}/courses/{self.returned_course_id}/assignments/syllabus"

    def _get_page_url(self, page_url) -> str:
        return f"{self.api_url}/courses/{self.returned_course_id}/pages/{page_url}"

    def _get_file_url(self, file_id) -> str:
        return f"{self.api_url}/courses/{self.returned_course_id}/files/{file_id}"

    def load_pages(self, course) -> List[Document]:
        """Loads all published pages from a canvas course."""
        from canvasapi.exceptions import CanvasException

        page_documents = []

        try:
            pages = course.get_pages(
                published=True,
                include=[ "body" ]
            )

            for page in pages:
                if f"Page:{page.page_id}" not in self.indexed_items:
                    page_documents = page_documents + self.load_page(page)
                    self.indexed_items.append(f"Page:{page.page_id}")
        except CanvasException as error:
            self._error_logger(error=error, action="get_pages", entity_type="page", entity_id=page.page_id)

        return page_documents

    def logMessage(self, message, level):
        if level == 'INFO':
            logger.info(message)
        if level == 'DEBUG':
            logger.debug(message)
        if level == 'WARNING':
            logger.warning(message)

            self.errors.append(LogStatement(
                message = message,
                level = level
            ))

        self.progress.append(LogStatement(
            message = message,
            level = level
        ))

    def load_page(self, page) -> List[Document]:
        """Load a specific page."""
        try:
            if page.locked_for_user == True:
                # Page is locked
                self.logMessage(message=f"Page ({page.title}) locked - cannot index", level="DEBUG")
                return []

            if page.body:
                page_body_text = self._get_text_and_embed_urls(page.body)

                return [Document(
                    page_content=page_body_text.strip(),
                    metadata={ "filename": page.title, "source": self._get_page_url(page.url), "kind": "page", "page_id": page.page_id }
                )]
            else:
                # Page with no content - None
                return []
        except AttributeError as error:
            self._error_logger(error=error, action="load_page", entity_type="page", entity_id=page.page_id)
            return []

    def load_announcements(self, canvas, course) -> List[Document]:
        """Loads all announcements from a canvas course."""
        from canvasapi.exceptions import CanvasException

        announcement_documents = []

        try:
            announcements = canvas.get_announcements(
                context_codes=[ course ],
                start_date="2016-01-01",
                end_date=date.today().isoformat(),
            )

            for announcement in announcements:
                page_body_text = self._get_text_and_embed_urls(announcement.message)

                announcement_documents.append(Document(
                    page_content=page_body_text,
                    metadata={ "filename": announcement.title, "source": announcement.html_url, "kind": "announcement", "announcement_id": announcement.id }
                ))
        except CanvasException as error:
            self._error_logger(error=error, action="get_announcements", entity_type="announcement", entity_id=announcement.id)

        return announcement_documents

    def load_assignments(self, course) -> List[Document]:
        """Loads all assignments from a canvas course."""
        from canvasapi.exceptions import CanvasException

        assignment_documents = []

        try:
            assignments = course.get_assignments()

            for assignment in assignments:
                if f"Assignment:{assignment.id}" not in self.indexed_items:
                    assignment_documents = assignment_documents + self.load_assignment(assignment)
                    self.indexed_items.append(f"Assignment:{assignment.id}")
        except CanvasException as error:
            self._error_logger(error=error, action="get_assignments", entity_type="assignment", entity_id=assignment.id)

        return assignment_documents

    def load_assignment(self, assignment, module=None, locked=False, unlock_at_datetime=None) -> List[Document]:
        """Load a specific assignment."""
        if locked and unlock_at_datetime:
            friendly_time = unlock_at_datetime

            ny_timezone = pytz.timezone('America/New_York')
            ny_datetime = unlock_at_datetime.astimezone(ny_timezone)
            formatted_datetime = ny_datetime.strftime("%b %d, %Y at %I%p %Z").replace("PM", "pm").replace("AM", 'am')

            assignment_description = f"This assignment is part of the module {module.name}, which is locked until {formatted_datetime}."
        else:
            if assignment.description:
                assignment_description = self._get_text_and_embed_urls(assignment.description)
                assignment_description = f"Assignment Description: {assignment_description}\n\n"
            else:
                assignment_description = ""

        assignment_content=f"Assignment Name: {assignment.name} \n\n Assignment Due Date: {assignment.due_at} \n\n Assignment Points Possible: {assignment.points_possible} \n\n{assignment_description}"

        return [Document(
            page_content=assignment_content,
            metadata={ "filename": assignment.name, "source": assignment.html_url, "kind": "assignment", "assignment_id": assignment.id }
        )]

    def _get_uuid_canvas_iframe_url(self, url) -> str | None:
        """
        Get the resource link UUID from a Canvas iframe URL.

        If the URL has a query string with a `resource_link_lookup_uuid`
        parameter, return its value.  Otherwise, return None.

        :param url: Canvas iframe URL
        :type url: str
        :return: UUID from the URL
        :rtype: str|None
        """
        return parse_qs(urlparse(url).query
                        ).get('resource_link_lookup_uuid',
                              [None]).pop()

    def _get_embed_url_canvas_uuid(self, uuid: str) -> str | None:
        endpoint = (f'courses/{self.course_id}/lti_resource_links/'
                    f'lookup_uuid:{uuid}')

        response = self.canvas._Canvas__requester.request('GET', endpoint)

        return response.json().get('url')

    def _get_mivideo_media_id_url(self, url: str) -> str | None:
        """
        Get the media ID from a MiVideo URL.

        If the URL has a path with an `entryid` parameter, return its value.
        Otherwise, return None.

        :param url: MiVideo URL
        :type url: str
        :return: Media ID from the URL
        :rtype: str|None
        """
        parsed = urlparse(url)

        if parsed.netloc != 'aakaf.mivideo.it.umich.edu':
            return None

        path_parts = parsed.path.split('/')
        try:
            return path_parts[path_parts.index('entryid') + 1]
        except ValueError:
            return None

    def _get_text_and_embed_urls(self, html) -> (str, List[str]):
        """
        Extracts text and embedded URLs from HTML content.

        This function uses BeautifulSoup to parse the provided HTML content,
        extracts the text, and identifies any embedded URLs within iframe elements.
        It returns the extracted text and a list of embedded URLs.

        :param html: The HTML content to parse.
        :type html: str
        :return: A tuple containing the extracted text and a list of embedded URLs.
        :rtype: tuple(str, List[str])
        """

        bs = BeautifulSoup(html, 'lxml')

        doc_text = bs.text.strip()

        iframes:ResultSet[PageElement] = bs.find_all('iframe')
        iframe: PageElement
        for iframe in iframes:
            iframe_src_url = iframe.get('src')

            if (embedded_media_uuid :=
            self._get_uuid_canvas_iframe_url(iframe_src_url)):

                embed_urls.append(self._get_embed_url_canvas_uuid(
                    embedded_media_uuid))

                # mivideo_media_id = self._get_mivideo_media_id_url(
                #     mivideo_embed_url)
                # doc_text += f"MiVideo media ID: {mivideo_media_id} "

            # mivideo_documents = self.load_mivideo(
            #     self.returned_course_id,
            #     self.canvas_user_id)

        return (doc_text, embed_urls)

    def _load_text_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=False)

        return [Document(
            page_content=file_contents.strip(),
            metadata={ "filename": file.filename, "source": file.url, "kind": "file", "file_id": file.id }
        )]

    def _load_html_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=False)

        return [Document(
            page_content=self._get_text_and_embed_urls(file_contents),
            metadata={ "filename": file.filename, "source": file.url, "kind": "file", "file_id": file.id }
        )]

    def _load_rtf_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=False)

        return [Document(
            page_content=rtf_to_text(file_contents).strip(),
            metadata={ "filename": file.filename, "source": file.url, "kind": "file", "file_id": file.id }
        )]

    def _load_pdf_file(self, file) -> List[Document]:
        try:
            # Import PDF parser class
            from PyPDF2 import PdfReader
            from PyPDF2 import errors
            from binascii import Error as binasciiError
        except ImportError as exc:
            raise ImportError(
                "Could not import PyPDF2 python package. "
                "Please install it with `pip install PyPDF2`."
            ) from exc

        file_contents = file.get_contents(binary=True)

        docs = []

        try:
            pdf_reader = PdfReader(BytesIO(file_contents))

            for i, page in enumerate(pdf_reader.pages):
                docs.append(Document(
                    page_content=page.extract_text(),
                    metadata={ "filename": file.filename, "source": self._get_file_url(file.id), "kind": "file", "file_id": file.id, "page": i+1 }
                ))
        except errors.FileNotDecryptedError:
            self._error_logger(error=f"PyPDF2.errors.FileNotDecryptedError: File has not been decrypted ({file.filename})", action="read_pdf", entity_type="file", entity_id=file.id)
            self.logMessage(message = { "message": { 'filename': f"{file.filename}", 'reason': 'not_indexed' } }, level = 'INFO')
        except binasciiError as err:
            self._error_logger(error=f"{str(err)} ({file.filename})", action="read_pdf", entity_type="file", entity_id=file.id)
            self.logMessage(message = { "message": { 'filename': f"{file.filename}", 'reason': 'not_indexed' } }, level = 'INFO')
        except Exception as err:
            self._error_logger(error=f"{str(err)} ({file.filename})", action="read_pdf", entity_type="file", entity_id=file.id)
            self.logMessage(message = { "message": { 'filename': f"{file.filename}", 'reason': 'not_indexed' } }, level = 'INFO')

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

            for i, doc in enumerate(docs):
                docs[i].metadata["filename"] = file.filename
                docs[i].metadata["source"] = self._get_file_url(file.id)

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

            for i, doc in enumerate(docs):
                docs[i].metadata["filename"] = file.filename
                docs[i].metadata["source"] = self._get_file_url(file.id)

        return docs

    def _load_pptx_file(self, file) -> List[Document]:
        file_contents = file.get_contents(binary=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = f"{temp_dir}/{file.filename}"

            with open(file_path, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(file_contents)

            loader = UnstructuredPowerPointLoader(file_path)
            docs = loader.load()

            for i, doc in enumerate(docs):
                docs[i].metadata["filename"] = file.filename
                docs[i].metadata["source"] = self._get_file_url(file.id)

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

            for i, doc in enumerate(docs):
                docs[i].metadata["filename"] = file.filename
                docs[i].metadata["source"] = self._get_file_url(file.id)

        return docs

    def _error_logger(self, error, action, entity_type, entity_id) -> None:
        if isinstance(error, str):
            self.logMessage(message = { "message": error, "action": action, "entity_type": entity_type, "entity_id": entity_id }, level = 'WARNING')
        elif isinstance(error.message, str):
            message_json = json.loads(error.message)
            self.logMessage(message = { "message": message_json["errors"][0]["message"], "action": action, "entity_type": entity_type, "entity_id": entity_id }, level = 'WARNING')
        else:
            self.logMessage(message = { "message": error.message[0]["message"], "action": action, "entity_type": entity_type, "entity_id": entity_id }, level = 'WARNING')

    def load_files(self, course) -> List[Document]:
        """Loads all files from a canvas course."""
        from canvasapi.exceptions import CanvasException, ResourceDoesNotExist

        file_documents = []

        try:
            files = course.get_files()

            for file in files:
                try:
                    if f"File:{file.id}" not in self.indexed_items:
                        file_documents = file_documents + self.load_file(file)
                        self.indexed_items.append(f"File:{file.id}")
                except ResourceDoesNotExist:
                    # This will happen when the file is part of a module that is hidden
                    file_content_type = getattr(file, "content-type")
                    self.invalid_files.append(f"{file.filename} ({file_content_type})")
        except CanvasException as error:
            self._error_logger(error=error, action="get_files", entity_type="course", entity_id=course.id)

        return file_documents

    def load_file(self, file) -> List[Document]:
        """Load a specific file."""
        file_documents = []

        filename = getattr(file, "filename")
        file_content_type = getattr(file, "content-type")

        if file_content_type == "application/vnd.ms-excel":
            _, extension = os.path.splitext(filename)
            if extension == ".csv":
                file_content_type = "text/csv"

        allowed_content_types = [
            "text/markdown", # md
            "text/html", # htm, html
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # docx
            "application/vnd.ms-excel", # xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # xlsx
            "application/vnd.openxmlformats-officedocument.presentationml.presentation", # pptx
            "application/pdf", # pdf
            "text/rtf", # rtf
            "text/plain", # txt
        ]

        if file_content_type in allowed_content_types:
            self.logMessage(message=f"Processing file: {repr(file.filename)} ({file.mime_class})", level="DEBUG")

            if file_content_type == "text/plain":
                file_documents = file_documents + self._load_text_file(file)

            if file_content_type == "text/html":
                file_documents = file_documents + self._load_html_file(file)

            elif file_content_type == "application/pdf":
                file_documents = file_documents + self._load_pdf_file(file)

            elif file_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                file_documents = file_documents + self._load_docx_file(file)

            elif file_content_type in [ "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel" ]:
                file_documents = file_documents + self._load_excel_file(file)

            elif file_content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                file_documents = file_documents + self._load_pptx_file(file)

            elif file_content_type == "text/markdown":
                file_documents = file_documents + self._load_md_file(file)

            elif file_content_type == "text/rtf":
                file_documents = file_documents + self._load_rtf_file(file)
        else:
            self.invalid_files.append(f"{file.filename} ({file_content_type})")

        return file_documents

    def load_url(self, url) -> List[Document]:
        """Load a url."""
        loader = UnstructuredURLLoader(urls=[ url ])
        url_docs = loader.load()

        return url_docs

    def load_syllabus(self, course) -> List[Document]:
        try:
            syllabus_body = course.syllabus_body

            if not syllabus_body:
                return []

            page_body_text = self._get_text_and_embed_urls(course.syllabus_body)

            if len(page_body_text) == 0:
                return []

            return [Document(
                page_content=page_body_text,
                metadata={"filename": "Course Syllabus",
                          "source": self._get_syllabus_url(),
                          "kind": "syllabus"}
            )]
        except AttributeError:
            return []

        return []

    def load_modules(self, course) -> List[Document]:
        """Loads all modules from a canvas course."""
        from canvasapi.exceptions import CanvasException, ResourceDoesNotExist

        module_documents = []

        try:
            modules = course.get_modules()

            for module in modules:
                locked = False
                unlock_at_datetime = None

                if module.unlock_at:
                    unlock_at_datetime = datetime.strptime(module.unlock_at, '%Y-%m-%dT%H:%M:%SZ')
                    unlock_at_datetime = unlock_at_datetime.replace(tzinfo=pytz.UTC)
                    epoch_time = int(unlock_at_datetime.timestamp())
                    current_epoch_time = int(datetime.now().timestamp())

                    if current_epoch_time < epoch_time:
                        locked = True

                module_items = module.get_module_items(include=["content_details"])

                for module_item in module_items:
                    if module_item.type == "Page":
                        if f"Page:{module_item.page_url}" not in self.indexed_items:
                            if locked:
                                self.logMessage(message=f"Page ({module_item.title}) locked - cannot index", level="DEBUG")
                                # Don't try indexing page
                                continue

                            self.logMessage(message=f"Indexing page: {repr(module_item.title)} ({module_item.page_url})", level="DEBUG")

                            try:
                                page = course.get_page(module_item.page_url)
                                module_documents = module_documents + self.load_page(page)
                                self.indexed_items.append(f"Page:{module_item.page_url}")
                            except CanvasException as error:
                                self._error_logger(error=error, action="get_page", entity_type="page", entity_id=module_item.page_url)
                    elif module_item.type == "Assignment":
                        self.logMessage(message=f"Indexing assignment {module_item.title} ({module_item.content_id})", level="DEBUG")
                        if f"Assignment:{module_item.content_id}" not in self.indexed_items:
                            try:
                                assignment = course.get_assignment(module_item.content_id)
                                module_documents = module_documents + self.load_assignment(assignment, module, locked, unlock_at_datetime)
                                self.indexed_items.append(f"Assignment:{module_item.content_id}")
                            except CanvasException as error:
                                self._error_logger(error=error, action="get_assignment", entity_type="assignment", entity_id=module_item.content_id)
                    elif module_item.type == "File":
                        self.logMessage(message=f"Indexing file {repr(module_item.title)} ({module_item.content_id})", level="DEBUG")
                        if f"File:{module_item.content_id}" not in self.indexed_items:
                            try:
                                file = course.get_file(module_item.content_id)
                                module_documents = module_documents + self.load_file(file)
                                self.indexed_items.append(f"File:{module_item.content_id}")
                            except ResourceDoesNotExist:
                                # This will happen when the file is part of a module that is hidden
                                file_content_type = getattr(file, "content-type")
                                self.invalid_files.append(f"{file.filename} ({file_content_type})")
                            except CanvasException as error:
                                self._error_logger(error=error, action="get_file", entity_type="file", entity_id=module_item.content_id)
                    elif module_item.type == "ExternalUrl" and self.index_external_urls is True:
                        if locked:
                            self.logMessage(message=f"External URL locked - cannot index", level="DEBUG")
                            # Don't try indexing external URL
                            continue

                        self.logMessage(message=f"Indexing file {repr(module_item.title)} ({module_item.external_url})", level="DEBUG")

                        if f"ExternalUrl:{module_item.external_url}" not in self.indexed_items:
                            try:
                                module_documents = module_documents + self.load_url(url=module_item.external_url)
                                self.indexed_items.append(f"ExternalUrl:{module_item.external_url}")
                            except CanvasException as error:
                                self._error_logger(error=error, action="load_url", entity_type="externalurl", entity_id=module_item.external_url)
                    else:
                        self.logMessage(message=f"Module Item {module_item.title} is an unsupported type ({module_item.type})", level="DEBUG")

        except CanvasException as error:
            self._error_logger(error=error, action="get_modules", entity_type="course", entity_id=course.id)

        return module_documents

    def load_mivideo(self, course_id: int, user_id: int, media_id: str=None) -> List[Document]:
        """
        Load MiVideo media captions from Media Gallery LTI.

        :param course_id: Canvas course ID
        :type course_id: int
        :param user_id: Canvas user ID
        :type user_id: int
        :return: List of LangChain Document objects containing media captions
        :rtype: List[Document]
        """

        mivideo_documents = []

        try:
            api = MiVideoAPI(
                host=os.getenv('MIVIDEO_API_HOST'),
                authId=os.getenv('MIVIDEO_API_AUTH_ID'),
                authSecret=os.getenv('MIVIDEO_API_AUTH_SECRET'))

            languages = os.getenv('MIVIDEO_LANGUAGE_CODES_CSV')
            if not languages:
                languages = KalturaCaptionLoader.LANGUAGES_DEFAULT
            else:
                languages = set(languages.split(','))

            caption_loader = KalturaCaptionLoader(
                apiClient=api,
                courseId=str(int(course_id)),
                userId=str(int(user_id)),
                languages=languages,
                urlTemplate=os.getenv('MIVIDEO_SOURCE_URL_TEMPLATE'),
                chunkSeconds=int(
                    os.getenv('MIVIDEO_CHUNK_SECONDS') or
                    KalturaCaptionLoader.CHUNK_SECONDS_DEFAULT))

            if media_id is None:
            mivideo_documents = caption_loader.load()
            else:
                mivideo_documents = caption_loader.fetchMediaCaption({
                    'id': media_id,
                    'name': 'FUBAR',
                })

            course_url_template = os.getenv('CANVAS_COURSE_URL_TEMPLATE')

            # set `course_context` metadata field with course URL
            if course_url_template:
                def update_metadata(doc):
                    doc.metadata['course_context'] = (
                        course_url_template.format(courseId=course_id))
                    return doc

                mivideo_documents = list(
                    map(update_metadata, mivideo_documents))

            # Add indexed items to list
            self.indexed_items.extend(
                set('MiVideo:' + doc.metadata['media_id'] for doc in
                    mivideo_documents))
        except Exception as ex:
            self.logMessage(
                message=f'Error loading MiVideo Media Gallery captions: {ex}',
                level='INFO')

        return mivideo_documents

    def load(self) -> List[Document]:
        """Load documents."""

        docs = []

        try:
            # Initialize a new Canvas object
            canvas = Canvas(self.api_url, self.api_key)
            self.canvas = canvas

            # Allow overriding user ID in development
            self.canvas_user_id = os.getenv('CANVAS_USER_ID_OVERRIDE_DEV_ONLY',
                                            canvas.get_current_user().id)

            course = canvas.get_course(self.course_id, include=[ "syllabus_body" ])

            # Access the course's name
            self.logMessage(message=f"Indexing: {course.name} ({course.id})", level="INFO")

            self.returned_course_id = course.id

            # add syllabus
            self.logMessage(message="Load syllabus", level="DEBUG")
            docs = docs + self.load_syllabus(course=course)

            # Checking to see which tools are available?
            tabs = course.get_tabs()

            available_tabs = []
            # Canvas Tab labels are the names shown in the UI
            # Useful because LTIs all have IDs like 'external_tool'
            available_tabs_labels = [t.label for t in tabs]

            # Load MiVideo media captions from Media Gallery LTI
            if 'Media Gallery' in available_tabs_labels:
                self.logMessage(
                    'Loading MiVideo Media Gallery captions',
                    'DEBUG')
                mivideo_documents = self.load_mivideo(
                    self.returned_course_id,
                    # Allow overriding user ID in development
                    os.getenv('CANVAS_USER_ID_OVERRIDE_DEV_ONLY',
                              canvas.get_current_user().id))
                docs.extend(mivideo_documents)
                self.logMessage(
                    f'Loaded MiVideo Media Gallery captions: {len(mivideo_documents)}',
                    'DEBUG')

            for tab in tabs:
                available_tabs.append(tab.id)

            # Load modules
            if "modules" in available_tabs:
                self.logMessage(message="Load modules", level="DEBUG")
                module_documents = self.load_modules(course=course)
                docs = docs + module_documents

            # Load pages
            if "pages" in available_tabs:
                self.logMessage(message="Load pages", level="DEBUG")
                page_documents = self.load_pages(course=course)
                docs = docs + page_documents

            # Load announcements
            if "announcements" in available_tabs:
                self.logMessage(message="Load announcements", level="DEBUG")
                announcement_documents = self.load_announcements(canvas=canvas, course=course)
                docs = docs + announcement_documents

            # Load assignments
            if "assignments" in available_tabs:
                self.logMessage(message="Load assignments", level="DEBUG")
                assignment_documents = self.load_assignments(course=course)
                docs = docs + assignment_documents

            # Load files
            if "files" in available_tabs:
                self.logMessage(message="Load files", level="DEBUG")
                file_documents = self.load_files(course=course)
                docs = docs + file_documents

            # Replace null character with space
            for doc in docs:
                doc.page_content = doc.page_content.replace('\x00', ' ')

            if len(self.errors) > 0:
                self.logMessage(message=f"{len(self.errors)} file(s) were unable to be indexed.", level="INFO")

            return docs
        except CanvasException as error:
            self._error_logger(error=error, action="get_course", entity_type="course", entity_id=self.course_id)

        return docs

    def _filtered_statements_by_level(self, level) -> List:
        return [statement for statement in self.progress if statement.level == level]

    def get_details(self, level='INFO') -> List:
        if level == 'INFO':
            return self._filtered_statements_by_level(level), self.errors
        return self.progress, self.errors
