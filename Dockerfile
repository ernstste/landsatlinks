# Dockerfile for landsatlinks
# Copyright (C) 2021 David Frantz

from python

COPY . src

RUN python -m pip install --use-feature=in-tree-build src/

CMD ["landsatlinks"]
