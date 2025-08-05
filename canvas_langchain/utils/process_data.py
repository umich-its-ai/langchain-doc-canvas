"""Utility functions to load and format embedded urls, extract module metadata"""

from urllib.parse import urlparse

from canvas_langchain.sections.mivideo import MiVideoLoader
from canvas_langchain.utils.logging import Logger
from langchain.docstore.document import Document

# compatible with isolated and integrated testing
try:
    from django.conf import settings
except ImportError:
    import settings


def load_embed_urls(
    metadata: dict, embed_urls: list, mivideo_loader: MiVideoLoader
) -> list[Document]:
    """Load MiVideo content from embed urls"""
    docs = []
    for url in embed_urls:
        mivideo_loader.logger.logStatement(
            message=f"Loading embed url {url}", level="DEBUG"
        )
        # extract media_id from each url + load captions
        if mivideo_media_id := get_media_id(url, logger=mivideo_loader.logger):
            docs.extend(mivideo_loader.load_section(mivideo_id=mivideo_media_id))

    for doc in docs:
        doc.metadata.update(
            {
                "filename": str(metadata["data"]["filename"]),
                "course_context": str(metadata["data"]["source"]),
            }
        )
    return docs


def get_media_id(url: str, logger: Logger) -> str | None:
    """Extracts unique media id from each URL to load mivideo"""
    parsed = urlparse(url)
    if parsed.netloc == getattr(
        settings, "MIVIDEO_KAF_HOSTNAME", "aakaf.mivideo.it.umich.edu"
    ):
        path_parts = parsed.path.split("/")
        try:
            return path_parts[path_parts.index("entryid") + 1]
        except ValueError:
            logger.logStatement(
                message=f"Embed URL for {url} is not MiVideo", level="WARNING"
            )
    return None
