#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
DIR=$(dirname "$SCRIPT_DIR")

if [ -z "$1" ] 
then
	mutagen-compose -f $DIR/environment/docker-compose.yml -f $DIR/environment/docker-compose.mutagen.yml down
else
	mutagen-compose -f $DIR/environment/docker-compose.yml -f $DIR/environment/docker-compose.mutagen.yml rm -fs $@
fi