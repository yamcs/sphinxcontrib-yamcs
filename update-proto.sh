#!/bin/bash

# Compiles the Yamcs API annotations into a descriptor set. This is
# loaded at runtime by annotations.py into a private descriptor pool.

cd src/sphinxcontrib/yamcs

protoc --proto_path=../../../proto --descriptor_set_out=annotations.binpb annotations.proto
