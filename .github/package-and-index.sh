#!/bin/bash
set -eo pipefail

CHART_DIR="$(pwd)/charts"
SOURCE_DIR="$(pwd)/helm"

if [ ! -d "$CHART_DIR" ]
then
  echo "Missing chart directory $CHART_DIR. This seems wrong. Aborting!"
  exit 1
fi

if [ ! -d "$SOURCE_DIR" ]
then
  echo "Missing chart source directory $SOURCE_DIR. This seems wrong. Aborting!"
  exit 1
fi

cd "$(mktemp -d)"
helm package "$SOURCE_DIR"
GENERATED_FILE_NAME="$(basename ./*.tgz)"
if [ -f "$CHART_DIR/$GENERATED_FILE_NAME" ]
then
  echo "Release $GENERATED_FILE_NAME already exists, refusing to run!"
  exit 1
fi

echo "Adding release $GENERATED_FILE_NAME"
mv "./$GENERATED_FILE_NAME" "$CHART_DIR/$GENERATED_FILE_NAME"
helm repo index "$CHART_DIR" --url https://notepass.github.io/external-db-user-provider/charts/

if [ "$GHA" == "true" ]
then
  echo "changes_present=true" >> "$GITHUB_OUTPUT"
fi