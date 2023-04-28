#!/bin/bash
cd python/legion_linux
python3 -m build --wheel --no-isolation
python -m installer dist/*.whl
python3 -m installer --destdir="/abc" dist/*.whl