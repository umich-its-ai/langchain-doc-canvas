rm -fr ./build
rm -fr canvas_langchain.egg-info
pylint canvas_langchain
python3 -m build --sdist
python3 -m build --wheel
twine check dist/*
twine upload dist/*
