import tempfile
from io import BytesIO
from urllib.parse import urljoin

from canvas_langchain.base import BaseSectionLoader, BaseSectionLoaderVars
from canvasapi.exceptions import CanvasException, ResourceDoesNotExist
from canvasapi.file import File
from langchain.docstore.document import Document
from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
)
from PyPDF2 import PdfReader, errors


class FileLoader(BaseSectionLoader):
    def __init__(self, baseSectionVars: BaseSectionLoaderVars, course_api: str):
        super().__init__(baseSectionVars)
        self.course_api = course_api
        self.type_match = {
            "text/md": "md",
            "text/csv": "csv",
            "application/vnd.ms-excel": "excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        }

    def load_section(self) -> list[Document]:
        """Loads and formats all files from Canvas course"""
        self.logger.logStatement(message="Loading files...\n", level="INFO")

        file_documents = []
        try:
            files = self.canvas_client_extractor.get_files()
            for file in files:
                file_documents.extend(self._load_item(file))

        except CanvasException as error:
            self.logger.logStatement(
                message=f"Canvas exception loading files {error}", level="WARNING"
            )
        return file_documents

    def _load_item(self, file: File) -> list[Document]:
        """Loads given file based on extension"""
        if f"File:{file.id}" not in self.indexed_items:
            self.indexed_items.add(f"File:{file.id}")
            try:
                content_type = getattr(file, "content-type")
                self.logger.logStatement(
                    message=f"Loading file: {file.filename}", level="DEBUG"
                )

                if content_type in ["text/plain", "text/rtf"]:
                    return self._load_rtf_or_text_file(file)
                elif content_type == "text/html":
                    return self._load_html_file(file)
                elif content_type == "application/pdf":
                    return self._load_pdf_file(file)
                elif content_type in self.type_match:
                    return self._load_file_general(file, self.type_match[content_type])

            # exception occurs when file is in a hidden module
            except ResourceDoesNotExist as err:
                self.logger.logStatement(
                    message=f"File {file.filename} does not exist - likely in hidden module {err}",
                    level="DEBUG",
                )

            except Exception as ex:
                self.logger.logStatement(
                    message=f"Exception while loading file {file.filename}: {ex}",
                    level="DEBUG",
                )

        return []

    def load_from_module(self, item: File, **kwargs):
        """Loads file from module item"""
        self.logger.logStatement(
            message=f"Loading file {item.content_id} from module.", level="DEBUG"
        )
        file = self.canvas_client_extractor.get_file(file_id=item.content_id)
        return self._load_item(file)

    def _load_rtf_or_text_file(self, file: File) -> list[Document]:
        """Loads and formats text and rtf file data"""
        file_contents = file.get_contents(binary=False)
        metadata = {
            "content": file_contents,
            "data": {
                "filename": file.filename,
                "source": file.url,
                "kind": "file",
                "id": file.id,
            },
        }
        return self.process_data(metadata=metadata)

    def _load_html_file(self, file: File) -> list[Document]:
        """Loads and formats html file data"""
        file_contents = file.get_contents(binary=False)
        file_text, embed_urls = self.parse_html(html=file_contents)
        metadata = {
            "content": file_text,
            "data": {
                "name": file.filename,
                "source": file.url,
                "kind": "file",
                "id": file.id,
            },
        }
        return self.process_data(metadata=metadata, embed_urls=embed_urls)

    def _load_pdf_file(self, file: File) -> list[Document]:
        """Loads given pdf file by page"""
        file_contents = file.get_contents(binary=True)
        docs = []
        try:
            pdf_reader = PdfReader(BytesIO(file_contents))
            # extract info by page
            for i, page in enumerate(pdf_reader.pages):
                metadata = {
                    "content": page.extract_text(),
                    "data": {
                        "filename": file.filename,
                        "source": urljoin(self.course_api, f"files/{file.id}"),
                        "kind": "file",
                        "page": i + 1,
                    },
                }
                docs.extend(self.process_data(metadata=metadata))
        except errors.FileNotDecryptedError:
            self.logger.logStatement(
                message=f"Error: pdf {file.filename} is encrypted.", level="WARNING"
            )
        except Exception as err:
            self.logger.logStatement(
                message=f"Error loading pdf {file.filename}. Err: {err}",
                level="WARNING",
            )
        return docs

    def _load_file_general(self, file: File, file_type: str) -> list[Document]:
        """Loads docx, excel, pptx, and md files"""
        file_contents = file.get_contents(binary=True)
        docs = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = f"{temp_dir}/{file.filename}"

                with open(file_path, "wb") as binary_file:
                    # Write bytes to file
                    binary_file.write(file_contents)

                match file_type:
                    case "csv":
                        loader = CSVLoader(file_path)
                    case "excel":
                        loader = UnstructuredExcelLoader(file_path)
                    case "docx":
                        loader = Docx2txtLoader(file_path)
                    case "md":
                        loader = UnstructuredMarkdownLoader(file_path)
                    case "pptx":
                        loader = UnstructuredPowerPointLoader(file_path)
                if loader:
                    docs = loader.load()
                    for i, _ in enumerate(docs):
                        docs[i].page_content = self._remove_null_bytes(
                            docs[i].page_content
                        )
                        docs[i].metadata["filename"] = file.filename
                        docs[i].metadata["source"] = urljoin(
                            self.course_api, f"files/{file.id}"
                        )
        except Exception:
            self.logger.logStatement(
                message=f"Error loading {file.filename}", level="WARNING"
            )
        return docs
