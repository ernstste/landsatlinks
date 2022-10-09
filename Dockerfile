from osgeo/gdal:alpine-normal-3.5.2
RUN apk add --update aria2 py3-pip

COPY . src

RUN python -m pip install src/

CMD ["landsatlinks"]
