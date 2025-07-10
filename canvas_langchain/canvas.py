from typing import Any, List, Literal
from canvasapi import Canvas
from urllib.parse import urljoin
from langchain.document_loaders.base import BaseLoader
from langchain.docstore.document import Document
from canvasapi.exceptions import CanvasException, Forbidden
from langchain_community.document_loaders import UnstructuredURLLoader
from pydantic import BaseModel

from canvas_langchain.utils.logging import Logger
from canvas_langchain.utils.process_data import get_module_metadata
from canvas_langchain.sections.announcements import AnnouncementLoader
from canvas_langchain.sections.assignments import AssignmentLoader
from canvas_langchain.sections.files import FileLoader
from canvas_langchain.sections.pages import PageLoader
from canvas_langchain.sections.syllabus import SyllabusLoader
from canvas_langchain.base import BaseSectionLoaderVars

class UnpublishedCourseException(Exception):
    def __init__(self, message):
        super().__init__(message)

# Prevents conflicts with other classes in UMGPT - Happy to refactor as needed
class LogStatement(BaseModel):
    """INFO can be user-facing statements, non-technical and perhaps very high-level"""
    message: Any
    level: Literal['INFO', 'DEBUG', 'WARNING']

    def __json__(self):
        return {
            'message': self.message,
            'level': self.level,
        }

class CanvasLoader(BaseLoader):
    def __init__(self,
                 api_url: str,
                 api_key: str,
                 course_id: int, 
                 index_external_urls: bool=False):
        self.logger = Logger()
        self.index_external_urls = index_external_urls

        self.canvas = Canvas(api_url, api_key)
        try:
            self.course = self.canvas.get_course(course_id, include=[ "syllabus_body" ])
        except Forbidden:
            exception_message = (
                "User forbidden from accessing Canvas course. " 
                "Please check user permissions and course availability."
            )
            raise UnpublishedCourseException(message=exception_message)

        self.course_api = urljoin(api_url, f'/courses/{self.course.id}/')

        self.docs = []
        self.indexed_items = set()
        self.invalid_files = [] 

        # content loaders
        self.baseSectionVars = BaseSectionLoaderVars(self.canvas, 
                                                     self.course, 
                                                     self.indexed_items, 
                                                     self.logger)

        self.file_loader = FileLoader(self.baseSectionVars, self.course_api, self.invalid_files)
        self.syllabus_loader = SyllabusLoader(self.baseSectionVars)
        self.announcement_loader = AnnouncementLoader(self.baseSectionVars)
        self.assignment_loader = AssignmentLoader(self.baseSectionVars)
        self.page_loader = PageLoader(self.baseSectionVars, self.course_api)

    def load(self) -> List[Document]:
        """Loads all available content from Canvas course"""
        self.logger.logStatement(message="Starting document loading process. \n", level="INFO")
        try:
            # load syllabus
            self.docs.extend(self.syllabus_loader.load())

            # get available course navigation tabs
            available_tabs = [tab.label for tab in self.course.get_tabs()]

            for tab_name in available_tabs:
                match tab_name:
                    case 'Announcements':
                        self.docs.extend(self.announcement_loader.load())
                    case 'Assignments':
                        self.docs.extend(self.assignment_loader.load())
                    case 'Modules':
                        self.docs.extend(self.load_modules())
                    case 'Pages': 
                        self.docs.extend(self.page_loader.load_pages())
                    case 'Files':
                        self.docs.extend(self.file_loader.load_files())
        except Exception as err:
                self.logger.logStatement(message=f"Error loading Canvas materials {err}", level="WARNING")
        self.logger.logStatement(message="Canvas course processing finished.", level="INFO")
        return self.docs
    

    def load_modules(self) -> List[Document]:
        """Loads content from all unlocked modules in course"""
        self.logger.logStatement(message='Loading modules...\n', level="INFO")
        module_documents = []
        try:
            modules = self.course.get_modules()
            for module in modules:
                module_documents.extend(self.load_module(module))

        except CanvasException as ex:
            self.logger.logStatement(message=f"Canvas exception loading modules. Error: {ex}", level="WARNING")

        return module_documents


    def load_module(self, module) -> List[Document]:
        """Loads all content in module by type"""
        locked, formatted_datetime = get_module_metadata(module.unlock_at)
        module_items = module.get_module_items(include=["content_details"])
        module_docs = []
        for item in module_items:
            try:
                if item.type == "Page" and not locked:
                    self.logger.logStatement(message=f"Loading page {item.page_url} from module.", 
                                             level="DEBUG")
                    page = self.course.get_page(item.page_url)
                    module_docs.extend(self.page_loader.load_page(page))

                # assignment metadata can be gathered, even if module is locked
                elif item.type == "Assignment":
                    self.logger.logStatement(message=f"Loading assignment {item.content_id} from module.", 
                                             level="DEBUG")
                    assignment = self.course.get_assignment(item.content_id)
                    description=None
                    if locked and formatted_datetime:
                        description=f"Assignment is part of module {module.name}, which is locked until {formatted_datetime}"
                    module_docs.extend(self.assignment_loader.load_assignment(assignment, description))

                elif item.type=="File":
                    self.logger.logStatement(message=f"Loading file {item.content_id} from module.", 
                                             level="DEBUG")
                    file = self.course.get_file(item.content_id)
                    module_docs.extend(self.file_loader.load_file(file))

                elif item.type=="ExternalUrl" and self.index_external_urls and \
                    not locked and f"ExtUrl:{item.external_url}" not in self.indexed_items:

                    self.logger.logStatement(message=f"Loading external url {item.external_url} from module.", 
                                             level="DEBUG")
                    # load URL
                    url_loader = UnstructuredURLLoader(urls = [item.external_url])
                    module_docs.extend(url_loader.load())
                    self.indexed_items.add(f"ExtUrl:{item.external_url}")

            except CanvasException as ex:
                self.logger.logStatement(message=f"Unable to load {item} in module {module.name}. Error: {ex}",
                                         level="WARNING")

        return module_docs


    def get_details(self, level='INFO') -> List:
        if level == 'INFO':
            return self.logger._filtered_statements_by_level(level=level)
        return self.logger.progress, self.logger.errors
