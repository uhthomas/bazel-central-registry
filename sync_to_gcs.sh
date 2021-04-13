#!/bin/sh
set -x
set -e

BUCKET_NAME=bcr.bazel.build
gsutil cp ./bazel_registry.json gs://${BUCKET_NAME}/
gsutil cp ./module_list gs://${BUCKET_NAME}/
gsutil rsync -d -r ./modules gs://${BUCKET_NAME}/modules


