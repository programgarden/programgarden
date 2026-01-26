lsof -ti:8766 | xargs kill -9
poetry run python examples/python_server/server.py