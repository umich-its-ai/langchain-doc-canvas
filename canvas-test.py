import os

from canvas_langchain.canvas import CanvasLoader

loader = CanvasLoader(
    api_url=os.getenv('TEST_CANVAS_API_URL', 'https://umich.instructure.com'),
    api_key=os.getenv('TEST_CANVAS_API_KEY', 'default_key_here'),
    course_id=os.getenv('TEST_CANVAS_COURSE_ID', 'default_course_ID_here'),
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
    print('\n'.join([f'{m.level} — {m.message}' for m in loader.get_details('DEBUG')[0]]))
	print("")

except Exception as ex:
    print(loader.get_details('DEBUG'))
    print(ex)
