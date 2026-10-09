#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
DIR=$(dirname "$SCRIPT_DIR")
WORK_DIR=$(dirname "$DIR")

WORK_DIR="$WORK_DIR" \
	DOCKER_UID="$(id -u)" \
	DOCKER_GID="$(id -g)" \
	mutagen-compose -f $DIR/environment/docker-compose.yml -f $DIR/environment/docker-compose.mutagen.yml up -d --remove-orphans
