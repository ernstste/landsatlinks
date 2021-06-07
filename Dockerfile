# Dockerfile for landsatlinks
# Copyright (C) 2021 David Frantz

from python

RUN python -m pip install git+https://github.com/ernstste/landsatlinks.git

CMD ["landsatlinks"]
