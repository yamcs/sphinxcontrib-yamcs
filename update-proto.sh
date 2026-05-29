#!/bin/bash

cd src/sphinxcontrib/yamcs

protoc --proto_path=../../../proto --python_out=. annotations.proto
