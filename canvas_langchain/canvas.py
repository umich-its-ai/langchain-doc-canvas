from typing import Any, List, Literal
from canvasapi import Canvas
from urllib.parse import urljoin
from langchain.document_loaders.base import BaseLoader
from langchain.docstore.document import Document
from canvasapi.exceptions import Forbidden
from pydantic import BaseModel

from canvas_langchain.utils.logging import Logger
from canvas_langchain.sections.announcements import AnnouncementLoader
from canvas_langchain.sections.assignments import AssignmentLoader
from canvas_langchain.sections.files import FileLoader
from canvas_langchain.sections.modules import ModuleLoader
from canvas_langchain.sections.pages import PageLoader
from canvas_langchain.sections.syllabus import SyllabusLoader
from canvas_langchain.base import BaseSectionLoaderVars, BaseSectionLoader

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

        self.docs = self.invalid_files = []
        self.indexed_items = set()

        # content loaders
        self.baseSectionVars = BaseSectionLoaderVars(self.canvas, 
                                                     self.course, 
                                                     self.indexed_items, 
                                                     self.logger)


    def _get_loaders(self) -> dict[str, BaseSectionLoader]:
        """Returns a dictionary of section loaders"""
        file_loader = FileLoader(self.baseSectionVars, self.course_api, self.invalid_files)
        assignment_loader = AssignmentLoader(self.baseSectionVars)
        page_loader = PageLoader(self.baseSectionVars, self.course_api)
        
        module_loader = ModuleLoader(self.baseSectionVars, {
            "Files": file_loader,
            "Assignments": assignment_loader,
            "Pages": page_loader,
        })
        
        return {
            "Files": file_loader,
            "Assignments": assignment_loader,
            "Pages": page_loader,
            "Modules": module_loader,
            "Syllabus": SyllabusLoader(self.baseSectionVars),
            "Announcements": AnnouncementLoader(self.baseSectionVars),
        }

    def load(self) -> List[Document]:
        """Loads all available content from Canvas course"""
        self.logger.logStatement(message="Starting document loading process. \n", level="INFO")
        try:
            # get available course navigation tabs
            available_tabs = [tab.label for tab in self.course.get_tabs()]
            loaders = self._get_loaders()
            for tab_name in available_tabs:
                if tab_name in loaders:
                    self.docs.extend(loaders[tab_name].load_section())

        except Exception as err:
                self.logger.logStatement(message=f"Error loading Canvas materials {err}", level="WARNING")
        self.logger.logStatement(message="Canvas course processing finished.", level="INFO")
        return self.docs


    def get_details(self, level='INFO') -> List:
        if level == 'INFO':
            return self.logger._filtered_statements_by_level(level=level)
        return self.logger.progress, self.logger.errors
