#!/bin/sh

cd $(dirname $0)

sudo chrt -f 10 python -m pypedal --debug -c examples/example.conf -c examples/koolertron-custom.conf

