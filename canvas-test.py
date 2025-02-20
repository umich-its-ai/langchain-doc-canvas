import os

from canvas_langchain.canvas import CanvasLoader

try:
    from dotenv import load_dotenv  # pip install python-dotenv

    # Load environment variables from `.env` file
    env_loaded = load_dotenv()
    if env_loaded:
        print('Loaded environment variables from ".env" file.')
    else:
        print('".env" file is missing, empty, or invalid.')
except ImportError:
    print(
        'Unable to import the "dotenv" module.  Please install it with '
        '`pip install python-dotenv` to load environment variables from '
        'a ".env" file.  Otherwise, set them in the environment manually.  '
        'See ".env.example" for more information.')

loader = CanvasLoader(
    api_url=os.getenv('TEST_CANVAS_API_URL', 'https://umich.instructure.com'),
    api_key=os.getenv('TEST_CANVAS_API_KEY'),
    course_id=int(os.getenv('TEST_CANVAS_COURSE_ID')),
)

try:
    documents = loader.load()

    print("\nDocuments:\n")
    print('\n\n'.join(map(repr, documents)))

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
    print('\n'.join(
        [f'{m.level} — {m.message}' for m in loader.get_details('DEBUG')[0]]))
    print("")

except Exception as ex:
    print(loader.get_details('DEBUG'))
    print(ex)
