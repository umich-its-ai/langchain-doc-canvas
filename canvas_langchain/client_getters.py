from canvasapi.assignment import Assignment
from canvasapi.file import File
from canvasapi.page import Page
from canvasapi.paginated_list import PaginatedList
from canvasapi.course import Course
from datetime import date

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
