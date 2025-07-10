from canvasapi.exceptions import CanvasException
from langchain.docstore.document import Document
from canvasapi.discussion_topic import DiscussionTopic
from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars

class AnnouncementLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars):
        super().__init__(baseSectionVars)

    def load_section(self) -> list[Document]:
        """Load all announcements for a Canvas course"""
        self.logger.logStatement(message='Loading announcements...\n', level="INFO")

        announcement_documents = embed_urls = []
        try:
            announcements = self.canvas_client_extractor.get_announcements()

            for announcement in announcements:
                announcement_documents.extend(self._load_item(announcement=announcement))

        except CanvasException as error:
            self.logger.logStatement(message=f"Canvas exception loading announcements {error}",
                                     level="WARNING")

        return announcement_documents

    def _load_item(self, announcement: DiscussionTopic) -> list[Document]:
        """Loads a single announcement"""
        self.logger.logStatement(message=f"Loading announcement: {announcement.title}", level="DEBUG")
        announcement_text, embed_urls = self.parse_html(html=announcement.message)
        metadata={"content": announcement_text,
        "data": {"filename": announcement.title,
                 "source": announcement.html_url,
                 "kind": "announcement",
                 "id": announcement.id}
        }
        return self.process_data(metadata=metadata, embed_urls=embed_urls)
