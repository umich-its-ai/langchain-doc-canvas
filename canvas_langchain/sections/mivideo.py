from typing import List

from langchain.docstore.document import Document
from LangChainKaltura.KalturaCaptionLoader import KalturaCaptionLoader
from LangChainKaltura.MiVideoAPI import MiVideoAPI
from requests import HTTPError

# compatible with isolated and integrated testing
try:
    from django.conf import settings

except ImportError:
    import settings


class MiVideoLoader:
    def __init__(self, canvas_content_extractor, indexed_items, logger):
        self.canvas_content_extractor = canvas_content_extractor
        self.indexed_items = indexed_items
        self.logger = logger
        self.caption_loader = None
        self.mivideo_api = MiVideoAPI(
            host=settings.MIVIDEO_API_HOST,
            authId=settings.MIVIDEO_API_AUTH_ID,
            authSecret=settings.MIVIDEO_API_AUTH_SECRET,
        )
        self.mivideo_authorized = True

    def load_section(self, mivideo_id: str | None = None) -> List[Document]:
        """Load MiVideo media captions"""
        mivideo_documents = []
        self.logger.logStatement(
            message="Loading MiVideo Media Gallery\n", level="INFO"
        )
        if not self.mivideo_authorized:
            self.logger.logStatement(
                message="MiVideo API prior request unauthorized; skipping caption load",
                level="INFO",
            )
            return []
        if not self.caption_loader:
            self.caption_loader = self._get_caption_loader()
        try:
            if mivideo_id is None:
                mivideo_documents = self._load_gallery()
            else:
                mivideo_documents = self._load_video(mivideo_id)

            mivideo_documents = self._format_document_urls(mivideo_documents)

        # don't attempt to load MiVideo again if user is unauthorized
        except HTTPError as ex:
            self.logger.logStatement(
                message=f"HTTP {ex.response.status_code} error loading MiVideo captions: {ex}",
                level="INFO",
            )
            if ex.response.status_code == 401:
                self.mivideo_authorized = False
                self.logger.logStatement(
                    message="MiVideo caption request unauthorized. Skipping subsequent requests.",
                    level="INFO",
                )
        except Exception as e:
            self.logger.logStatement(
                message=f"Error loading MiVideo content: {e}", level="WARNING"
            )

        return mivideo_documents

    def _get_caption_loader(self) -> KalturaCaptionLoader:
        try:
            languages = KalturaCaptionLoader.LANGUAGES_DEFAULT
            caption_loader = KalturaCaptionLoader(
                apiClient=self.mivideo_api,
                courseId=str(int(self.canvas_content_extractor.get_course_id())),
                userId=str(
                    int(
                        getattr(
                            settings,
                            "CANVAS_USER_ID_OVERRIDE_DEV_ONLY",
                            self.canvas_content_extractor.get_user_id(),
                        )
                    )
                ),
                languages=languages,
                urlTemplate=getattr(settings, "MIVIDEO_SOURCE_URL_TEMPLATE"),
                chunkSeconds=int(
                    getattr(
                        settings,
                        "MIVIDEO_CHUNK_SECONDS",
                        KalturaCaptionLoader.CHUNK_SECONDS_DEFAULT,
                    )
                ),
            )
        except Exception as e:
            self.logger.logStatement(
                message=f"Error initializing Kaltura Caption Loader: {e}",
                level="WARNING",
            )
        return caption_loader

    def _load_gallery(self) -> List[Document]:
        """Load all media in the gallery"""
        self.logger.logStatement(
            message="Loading MiVideo Media Gallery\n", level="INFO"
        )
        return self.caption_loader.load()

    def _load_video(self, mivideo_id: str) -> List[Document]:
        """Load a single media post by ID if not already indexed"""
        if f"MiVideo:{mivideo_id}" in self.indexed_items:
            return []
        self.logger.logStatement(message=f"Loading MiVideo: {mivideo_id}", level="INFO")
        return self.caption_loader.fetchMediaCaption(
            {"id": mivideo_id, "name": "unidentified embedded media"}
        )

    def _format_document_urls(
        self, mivideo_docuements: List[Document]
    ) -> List[Document]:
        course_url_template = settings.CANVAS_COURSE_URL_TEMPLATE
        for doc in mivideo_docuements:
            # add formatted course source url for this video
            if course_url_template:
                doc.metadata["course_context"] = course_url_template.format(
                    courseId=self.canvas_content_extractor.get_course_id()
                )

            self.indexed_items.add("MiVideo:" + doc.metadata["media_id"])
        return mivideo_docuements
