# Canvas langchain document loader

Features:

Indexes Canvas Modules, Pages, Announcements, Assignments and Files

The following file types are supported:
  `md` `htm` `html` `docx` `xls` `xlsx` `pptx` `pdf` `rtf` `txt`

(`doc` support would require libreoffice, so has not been implemented in this library)

## Running locally (development)

You can build/run the provided Dockerfile, or install dependencies as described below

### Environment Variables

Create a `.env` file in the root of the project by copying the `.env.example`
file.

```bash
cp .env.example .env
```

Edit the new `.env` file to fill in the correct values. Refer to the comments
in the `.env` file for more information.

> #### 🔔 Important
> Do not set the `CANVAS_ALT_USER_ID_DEV_ONLY` variable in a production
> environment or other shared environment. It is only for development purposes.

### Docker

Edit `canvas-test.py`, fill in the correct `api_url`, `api_key`, and `course_id`.

Run (this also builds docker):

```bash
docker run -it $(docker build -q .)
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage example:

```python
from canvas_langchain.canvas import CanvasLoader

loader = CanvasLoader(
	api_url = "https://CANVAS_API_URL_GOES_HERE",
	course_id = CANVAS_ID_GOES_HERE,
	api_key = "API_KEY_GOES_HERE"
)

try:
	documents = loader.load()

	print("\nDocuments:\n")
	print(documents)

	print("\nInvalid files:\n")
	print(loader.invalid_files)
	print("")

	print("\nErrors:\n")
	print(loader.errors)
	print("")

	print("\nIndexed:\n")
	print(loader.indexed_items)
	print("")

	print("\nProgress:\n")
	print(loader.get_details('DEBUG'))
	print("")
except Exception:
	details = loader.get_details('DEBUG')
```

If errors are present, `loader.errors` will contain one list element per error. It will consist of an error message (key named `message`) and if the error pertains to a specific item within canvas, it will list the `entity_type` and the `entity_id` of the resource where the exception occurred.
