# Canvas LangChain document loader

## Features

Indexes Canvas Modules, Pages, Announcements, Assignments, and Files

The following file types are supported:
`md` `htm` `html` `docx` `xls` `xlsx` `pptx` `pdf` `rtf` `txt` `csv`

(`doc` support would require libreoffice, so has not been implemented in this library)

If a course has a MiVideo "Media Gallery" available, the loader will
also index the captions of the media in the gallery. At this time, the loader
does not index captions of media embedded in Canvas Pages or other content.

## Running locally (development)

You can build/run the provided Dockerfile, or install dependencies as described below

### Configure Environment

This environment may be used with Docker or without.

Create a `.env` file in the root of the project by copying the `.env.example`
file.

```bash
cp .env.example .env
```

Edit the new `.env` file to fill in the correct values. Refer to the comments
in the `.env` file for more information.

> #### 🔔 Important
> Do not set the `CANVAS_USER_ID_OVERRIDE_DEV_ONLY` variable in a production
> environment or other shared environment. It is only for development purposes.

### Running with Docker

The following command builds a Docker image named `ldc_dev` containing Python,
all the required dependencies, and the project code, then runs it.

```bash
docker build -t ldc_dev . && docker run -it ldc_dev
```

### Running with Python Virtual Environment

#### Create a Python Virtual Environment

```bash
python -mvenv .venv
. .venv/bin/activate
```

#### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### Run

```bash
python canvas-test.py
```

## Usage example

> #### 💡 Note
> See the `canvas-test.py` file for a more complete example.

```python
from canvas_langchain.canvas import CanvasLoader

loader = CanvasLoader(
	api_url="https://CANVAS_API_URL_GOES_HERE",
	api_key="CANVAS_API_KEY_GOES_HERE",
	course_id=int(CANVAS_COURSE_ID_GOES_HERE),
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
