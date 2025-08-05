from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from canvasapi.assignment import Assignment
from canvasapi.exceptions import CanvasException
from langchain.docstore.document import Document


class AssignmentLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        super().__init__(baseSectionVars)

    def load_section(self) -> list[Document]:
        """Load all assignments for a Canvas course"""
        self.logger.logStatement(message="Loading assignments...\n", level="INFO")

        assignment_documents = []
        try:
            assignments = self.canvas_client_extractor.get_assignments()
            for assignment in assignments:
                if f"Assignment:{assignment.id}" not in self.indexed_items:
                    self.indexed_items.add(f"Assignment:{assignment.id}")
                    assignment_documents.extend(self._load_item(assignment, None))

        except CanvasException as error:
            self.logger.logStatement(
                message=f"Canvas exception loading assignments {error}", level="WARNING"
            )

        return assignment_documents

    def _load_item(
        self, assignment: Assignment, description: str | None
    ) -> list[Document]:
        """Load and format one assignment"""
        assignment_description = ""
        embed_urls = []
        self.logger.logStatement(
            message=f"Loading assignment: {assignment.name}", level="DEBUG"
        )

        # Custom description from locked module
        if description is not None:
            assignment_description = description

        elif assignment.description:
            assignment_description, embed_urls = self.parse_html(assignment.description)

        assignment_content = (
            f"Name: {assignment.name}\n"
            f"Due Date: {assignment.due_at}\n"
            f"Points Possible: {assignment.points_possible}\n"
            f"Description: {assignment_description}\n"
        )

        metadata = {
            "content": assignment_content,
            "data": {
                "filename": assignment.name,
                "source": assignment.html_url,
                "kind": "assignment",
                "id": assignment.id,
            },
        }

        return self.process_data(metadata=metadata, embed_urls=embed_urls)

    def load_from_module(
        self,
        item: Assignment,
        module_name: str,
        locked: bool,
        formatted_datetime: str | None,
    ) -> list[Document]:
        """Loads assignment from module item"""
        self.logger.logStatement(
            message=f"Loading assignment {item.content_id} from module.", level="DEBUG"
        )
        assignment = self.canvas_client_extractor.get_assignment(
            assignment_id=item.content_id
        )
        description = None
        if locked and formatted_datetime:
            description = f"Assignment is part of module {module_name}, which is locked until {formatted_datetime}"
        return self._load_item(assignment, description)
