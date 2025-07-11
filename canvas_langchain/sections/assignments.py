from typing import List
from canvasapi.paginated_list import PaginatedList
from canvasapi.exceptions import CanvasException
from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from langchain.docstore.document import Document

class AssignmentLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        super().__init__(baseSectionVars)

    def load_section(self) -> List[Document]:
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

    def _load_item(self, assignment: PaginatedList, description: str | None) -> List[Document]:
        """Load and format one assignment"""
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

    def load_from_module(self, item, module_docs, locked: bool = False, formatted_datetime: str | None = None):
        self.logger.logStatement(message=f"Loading assignment {item.content_id} from module.", level="DEBUG")
        assignment = self.course.get_assignment(item.content_id)
        description=None
        if locked and formatted_datetime:
            description=f"Assignment is part of module {module.name}, which is locked until {formatted_datetime}"
        module_docs.extend(self.assignment_loader._load_assignment(assignment, description))
