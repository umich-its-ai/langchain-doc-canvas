from canvas_langchain.canvas import CanvasLoader

import logging
loader = CanvasLoader(
	api_url = "https://CANVAS_API_URL_GOES_HERE",
	api_key = "API_GOES_HERE",
	course_id = CANVAS_ID_GOES_HERE)
	log_level = logging.INFO
)

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