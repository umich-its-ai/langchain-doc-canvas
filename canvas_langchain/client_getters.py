from datetime import date

from canvas_langchain.utils.logging import Logger
from canvasapi.assignment import Assignment
from canvasapi.course import Course
from canvasapi.exceptions import CanvasException
from canvasapi.file import File
from canvasapi.page import Page
from canvasapi.paginated_list import PaginatedList


class CanvasClientGetters:
    def __init__(self, canvas, course: Course, logger: Logger):
        self._canvas = canvas
        self._course = course
        self.logger = logger

    def get_announcements(self) -> PaginatedList:
        return self._canvas.get_announcements(
            context_codes=[self._course],
            start_date="2016-01-01",
            end_date=date.today().isoformat(),
        )

    def get_assignments(self) -> PaginatedList:
        return self._course.get_assignments()

    def get_assignment(self, assignment_id) -> Assignment:
        return self._course.get_assignment(assignment_id)

    def get_files(self) -> PaginatedList:
        return self._course.get_files()

    def get_file(self, file_id) -> File:
        return self._course.get_file(file_id)

    def get_modules(self) -> PaginatedList:
        return self._course.get_modules()

    def get_pages(self) -> PaginatedList:
        return self._course.get_pages(published=True, include=["body"])

    def get_page(self, url) -> Page:
        return self._course.get_page(url)

    def get_syllabus(self) -> str:
        return self._course.syllabus_body

    def get_url_from_canvas(self, uuid: str) -> str:
        endpoint = f"courses/{self._course.id}/lti_resource_links/lookup_uuid:{uuid}"
        url = None
        try:
            # Get embed URL via UUID
            response = self._canvas._Canvas__requester.request("GET", endpoint)
            url = response.json().get("url")
        except CanvasException as e:
            self.logger.logStatement(
                message=f"Error retrieving URL from Canvas for UUID {uuid}: {e}",
                level="ERROR",
            )
        return url

    def get_user_id(self) -> int:
        return self._canvas.get_current_user().id

    def get_course_id(self) -> int:
        return self._course.id
