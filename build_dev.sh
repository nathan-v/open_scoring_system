#!/usr/bin/env bash

docker build . -f dev.dockerfile -t cbaxter1988/scoring_server:dev

docker push cbaxter1988/scoring_server:dev