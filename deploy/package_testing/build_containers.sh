#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${DIR}
sudo docker compose build --no-cache
