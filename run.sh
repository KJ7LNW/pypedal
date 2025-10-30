#!/bin/sh

cd $(dirname $0)

sudo chrt -f 10 python -m pypedal -c example.conf
