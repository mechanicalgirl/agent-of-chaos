#!/bin/bash

DOCKERFILES=("Dockerfile.ancient" "Dockerfile.modern")
CHOSEN="${DOCKERFILES[$RANDOM % ${#DOCKERFILES[@]}]}"

CHAOS_LEVEL=${1:-medium}
echo "Building with $CHOSEN..."
docker build -f $CHOSEN \
    --no-cache \
    --build-arg CHAOS_LEVEL=$CHAOS_LEVEL \
    -t mail-test .
docker stop mail-test 2>/dev/null
docker rm mail-test 2>/dev/null
docker run -d -p 2222:22 --name mail-test mail-test
echo "Container ready! Chaos level: $CHAOS_LEVEL"
