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
    print('\n'.join([f'{m.level} — {m.message}' for m in loader.get_details('DEBUG')[0]]))
	print("")

except Exception as ex:
    print(loader.get_details('DEBUG'))
    print(ex)
