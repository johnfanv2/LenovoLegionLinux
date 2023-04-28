#!/bin/bash
cd python/legion_linux
python3 -m build --wheel --no-isolation
python3 -m installer --destdir="/" dist/*.whl