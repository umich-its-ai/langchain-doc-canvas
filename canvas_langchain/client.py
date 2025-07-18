from canvasapi import Canvas
from canvasapi.exceptions import Forbidden
from canvasapi.course import Course
from canvasapi.paginated_list import PaginatedList
from urllib.parse import urljoin
from datetime import date

from canvas_langchain.utils.logging import Logger
from canvas_langchain.sections.announcements import AnnouncementLoader
from canvas_langchain.sections.assignments import AssignmentLoader
from canvas_langchain.sections.files import FileLoader
from canvas_langchain.sections.modules import ModuleLoader
from canvas_langchain.sections.pages import PageLoader
from canvas_langchain.sections.syllabus import SyllabusLoader
from canvas_langchain.base import BaseSectionLoaderVars, BaseSectionLoader

from canvasapi.assignment import Assignment
from canvasapi.file import File
from canvasapi.page import Page

class UnpublishedCourseException(Exception):
    def __init__(self, message):
        super().__init__(message)

class CanvasClient():
    def __init__(self, api_url: str, api_key: str):
        self._canvas = Canvas(api_url, api_key)
        self.api_url = api_url
        self._course = self.get_course()
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
        base_vars = BaseSectionLoaderVars(canvas_content_extractor=self.content_extractor, indexed_items=set(), logger=logger)
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
    

class CanvasClientGetters():
    def __init__(self, canvas, course: Course):
        self._canvas = canvas
        self._course = course

    def get_announcements(self) -> PaginatedList:
        return self.canvas.get_announcements(context_codes=[self._course],
                                                            start_date="2016-01-01",
                                                            end_date=date.today().isoformat())
    
    def get_assignments(self) -> PaginatedList:
        return self._course.get_assignments()
    
    def get_assignment(self, assignment_id) -> Assignment:
        self._course.get_assignment(assignment_id)
    
    def get_files(self) -> PaginatedList:
        return self._course.get_files()
    
    def get_file(self, file_id) -> File:
        return self._course.get_file(file_id)

    def get_modules(self) -> PaginatedList:
        return self._course.get_modules()
    
    def get_pages(self) -> PaginatedList:
        return self._course.get_pages(published=True,
                                     include=['body'])
    
    def get_page(self, url) -> Page:
        return self._course.get_page(url)
    
    def get_syllabus(self) -> PaginatedList:
        return self._course.syllabus_body
