from typing import List
from canvasapi.paginated_list import PaginatedList
from canvasapi.exceptions import CanvasException
from canvas_langchain.base import BaseSectionLoader
from langchain.docstore.document import Document

class AssignmentLoader(BaseSectionLoader):
    def load(self) -> List[Document]:
        """Load all assignments for a Canvas course"""
        self.logger.logStatement(message='Loading assignments...\n', level="INFO")

        assignment_documents = []
        try:
            assignments = self.course.get_assignments()
            for assignment in assignments:
                if f"Assignment:{assignment.id}" not in self.indexed_items:
                    self.indexed_items.add(f"Assignment:{assignment.id}")
                    assignment_documents.extend(self.load_assignment(assignment, None))

        except CanvasException as error:
            self.logger.logStatement(message=f"Canvas exception loading assignments {error}",
                                    level="WARNING")

        return assignment_documents


    def load_assignment(self, assignment: PaginatedList, description: str | None) -> List[Document]:
        """Load and format given assignment"""
        assignment_description = ""
        self.logger.logStatement(message=f"Loading assignment: {assignment.name}", level="DEBUG")

        # Custom description from locked module
        if description is not None:
            assignment_description = description

        elif assignment.description:
            assignment_description = self.parse_html(assignment.description)
                                                              
        assignment_content = (
            f"Name: {assignment.name}\n"
            f"Due Date: {assignment.due_at}\n"
            f"Points Possible: {assignment.points_possible}\n"
            f"Description: {assignment_description}\n"
        )

        metadata={"content":assignment_content,
                  "data": {"filename": assignment.name,
                           "source": assignment.html_url,
                           "kind": "assignment",
                           "id": assignment.id}
                    }

        return self.process_data(metadata=metadata)
