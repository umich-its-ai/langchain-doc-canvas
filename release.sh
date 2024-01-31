rm -fr ./build
rm -fr ./dist
rm -fr canvas_langchain.egg-info
pylint canvas_langchain
python3 -m build
twine check dist/*
twine upload dist/*
