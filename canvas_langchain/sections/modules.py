from datetime import datetime, timezone
from typing import Tuple
from canvasapi.exceptions import CanvasException
from canvasapi.module import ModuleItem
from langchain_community.document_loaders import UnstructuredURLLoader
from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from langchain.docstore.document import Document

class ModuleLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars, index_external_urls: bool, loaders: dict[str, BaseSectionLoader]):
        super().__init__(baseSectionVars)
        self.loaders = loaders
        self.index_external_urls = index_external_urls

    def load_section(self) -> list[Document]:
        """Loads content from all unlocked modules in course"""
        self.logger.logStatement(message='Loading modules...\n', level="INFO")
        module_documents = []
        try:
            modules = self.canvas_client.get_modules()
            for module in modules:
                module_documents.extend(self._load_item(module))

        except CanvasException as ex:
            self.logger.logStatement(message=f"Canvas exception loading modules. Error: {ex}", level="WARNING")

        return module_documents
    
    def _load_item(self, module: ModuleItem) -> list[Document]:
        """Loads content from a single module"""
        locked, formatted_datetime = self._get_module_metadata(module.unlock_at)
        module_items = module.get_module_items()
        module_docs = []
        try:
            for item in module_items:
                if (item.type == "Page" and not locked) or (item.type == "File"):
                    module_docs.extend(self.loaders[f"{item.type}s"].load_from_module(item=item))
                elif item.type == "Assignment":
                    module_docs.extend(self.loaders["Assignments"].load_from_module(item=item,
                                                                                    module_name=module.name,
                                                                                    locked=locked,
                                                                                    formatted_datetime=formatted_datetime))
                elif item.type == "ExternalUrl" and self.index_external_urls:
                    module_docs.extend(self._load_external_url(item))
            return module_docs
        except CanvasException as ex:
            self.logger.logStatement(message=f"Canvas exception loading module items. Error: {ex}", level="WARNING")
            return []

    def _get_module_metadata(self, unlock_time: str) -> Tuple[bool, str]:
        """Returns if module is locked and corresponding unlock time ("" if unlocked)"""
        locked=False
        formatted_datetime=""
        if unlock_time:
            # get formatted unlock time
            formatted_datetime = datetime.strptime(unlock_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            current_time = datetime.now(timezone.utc)
            # determine if locked
            locked = current_time < formatted_datetime

        return locked, formatted_datetime

    def _load_external_url(self, item: ModuleItem) -> list[Document]:
        """Loads external URL from module item"""
        if item.external_url and f"ExtUrl:{item.external_url}" not in self.indexed_items:
            self.logger.logStatement(message=f"Loading external url {item.external_url} from module.", 
                                    level="DEBUG")
            url_loader = UnstructuredURLLoader(urls = [item.external_url])
            docs = url_loader.load()
            if docs:
                self.indexed_items.add(f"ExtUrl:{item.external_url}")
                return docs
        return []
