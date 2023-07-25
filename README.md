# Canvas langchain document loader

Features:

Indexes Canvas Pages, Announcements, Assignments and Files

The following file types are supported:
  `md` `htm` `html` `docx` `xls` `xlsx` `pdf` `rtf` `txt`

(`doc` support would require libreoffice)

## Running locally

You can do the install as described below, or build/run the provider dockerfile.

## Docker

Edit canvas-test.py, fill in the correct api_url, api_key, and course_id.

Run (this also builds docker):

```bash
docker run -it $(docker build -q .)
```

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage example:

```python
from canvas import CanvasLoader

loader = CanvasLoader(
	api_url = "https://canvas.instructure.com",
	api_key = "API_KEY_GOES_HERE",
	course_id = 123456789
)

documents = loader.load()

print("\nDocuments:\n")
print(documents)

print("\nInvalid files:\n")
print(loader.invalid_files)
print("")
```