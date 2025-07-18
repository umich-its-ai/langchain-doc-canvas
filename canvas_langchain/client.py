from canvasapi import Canvas
from canvasapi.exceptions import Forbidden
from canvasapi.course import Course
from urllib.parse import urljoin

from canvas_langchain.utils.logging import Logger
from canvas_langchain.sections.announcements import AnnouncementLoader
from canvas_langchain.sections.assignments import AssignmentLoader
from canvas_langchain.sections.files import FileLoader
from canvas_langchain.sections.modules import ModuleLoader
from canvas_langchain.sections.pages import PageLoader
from canvas_langchain.sections.syllabus import SyllabusLoader
from canvas_langchain.base import BaseSectionLoaderVars, BaseSectionLoader

from canvas_langchain.client_getters import CanvasClientGetters

class UnpublishedCourseException(Exception):
    def __init__(self, message):
        super().__init__(message)

class CanvasClient():
    def __init__(self, api_url: str, api_key: str, course_id: int):
        self._canvas = Canvas(api_url, api_key)
        self.api_url = api_url
        self._course = self.get_course(course_id)
        self.content_extractor = CanvasClientGetters(self._canvas, self._course)

    def get_course(self, course_id: int) -> Course:
        try:
            return self._canvas.get_course(course_id, include=[ "syllabus_body" ])
        except Forbidden:
            exception_message = (
                "User forbidden from accessing Canvas course. " 
                "Please check user permissions and course availability."
            )
            raise UnpublishedCourseException(message=exception_message)

    def get_available_tabs(self) -> list[str]:
        return [tab.label for tab in self._course.get_tabs()]

    def get_loaders(self, index_external_urls: bool, logger: Logger) -> dict[str, BaseSectionLoader]:
        base_vars = BaseSectionLoaderVars(canvas_client_extractor=self.content_extractor, indexed_items=set(), logger=logger)
        course_api = urljoin(self.api_url, f'courses/{self._course.id}/')
        
        assignment_loader = AssignmentLoader(baseSectionVars=base_vars)
        page_loader = PageLoader(baseSectionVars=base_vars, course_api=course_api)
        file_loader = FileLoader(baseSectionVars=base_vars, course_api=course_api, invalid_files=[])

        return {
            "Announcements": AnnouncementLoader(baseSectionVars=base_vars),
            "Assignments": assignment_loader,
            "Files": file_loader,
            "Modules": ModuleLoader(baseSectionVars=base_vars, index_external_urls=index_external_urls, 
                                    loaders={
                                        "Pages": page_loader,
                                        "Assignments": assignment_loader,
                                        "Files": file_loader
                                    }),
            "Pages": page_loader,
            "Syllabus": SyllabusLoader(baseSectionVars=base_vars, course_api=course_api)
        }
