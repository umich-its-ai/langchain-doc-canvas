from urllib.parse import urljoin

from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from langchain.docstore.document import Document


class SyllabusLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars, course_api: str):
        super().__init__(baseSectionVars)
        self.course_api = course_api

    def load_section(self) -> list[Document]:
        self.logger.logStatement(message="Loading syllabus...\n", level="INFO")
        try:
            syllabus_body = self.canvas_client_extractor.get_syllabus()
            if syllabus_body:
                syllabus_text = self.parse_html(syllabus_body)
                syllabus_url = urljoin(self.course_api, "assignments/syllabus")

                metadata = {
                    "content": syllabus_text,
                    "data": {
                        "filename": "Course Syllabus",
                        "source": syllabus_url,
                        "kind": "syllabus",
                    },
                }
                return self.process_data(metadata=metadata, embed_urls=embed_urls)

        except AttributeError as err:
            self.logger.logStatement(
                message=f"Attribute error loading syllabus: {err}", level="WARNING"
            )

        except Exception as err:
            self.logger.logStatement(
                message=f"Error loading syllabus: {err}", level="WARNING"
            )

        return []
