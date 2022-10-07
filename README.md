# landsatlinks


##### Creating download urls for Landsat Collection 2 Level 1 product bundles using the USGS/EROS Machine-to-Machine API
![Python Version](https://img.shields.io/badge/python-%3E=v3.6-blue)
![License](https://img.shields.io/badge/license-MIT-brightgreen) 

landsatlinks offers a simple command line interface to retrieve download links for Landsat Collection 2 Level 1 product bundles through the USGS/EROS machine-to-machine API.



### Requirements
User credentials to log in to the USGS EarthExplorer interface are required. Your user account needs to have access to the machine-to-machine API, which can be requested through the user profile page [here](https://ers.cr.usgs.gov/profile/access).\
Python >= 3.6 is required. \
aria2c is required to download product bundles (Linux only). You can still create links and download them manually if aria2c is not available.


### Installation
Install using pip:
```
python -m pip install git+https://github.com/ernstste/landsatlinks.git
```
or download the Docker image (recommended):
```
docker pull ernstste/landsatlinks:latest
```

### Usage
Landsatlink provides two sub-programs available: __search__ and __download__ \
__search__ retrieves the download links for a given search query and can download the product bundles right away.\
__download__ will download product bundles from a list of download links that were created with __search__ before.

__landsatlinks search__ \
There are two mandatory arguments required to run the tool and several optional arguments that allow a more detailed filtering of search results. A call may look like this:

![search demo](https://github.com/ernstste/landsatlinks/raw/download/demo/landsatlinks_search_demo.gif)





_required arguments:_
- aoi\
  The area of interest. Can be\
  a) .txt - text file containing one tile per line in the format PPPRRR (P = path, R = row) \
  Keep padding zeroes! Good: 194023, bad: 19432\
  b) .shp, .gpkg, .geojson - vector file containing point, line, or polygon geometries.
- output-dir\
  The directory where the file containing the download urls (and product bundles) will be stored.

_optional arguments:_
- -s | --sensor\
  Restrict results to specific sensor(s).\
  choices = 'TM', 'ETM', 'OLI' (Landsat 4/5, Landsat 7, Landsat 8/9)\
  Default: All sensors
- -d | --daterange\
  Start date and end date = date range to be considered.\
  Format: YYYY-MM-DD,YYYY-MM-DD\
  Default: full archive until today.
- -c | --cloudcover\
  Percent (land) cloud cover range to be considered.\
  Default: 0,100
- -m | --months\
  Seasonal filter: define the months to be considered.\
  Default: 1,2,3,4,5,6,7,8,9,10,11,12
- -t | --tier\
  Landsat collection tier level.\
  Valid tiers: T1,T2,RT\
  Default: T1
- -l | --level\
  Landsat level of processing.\
  Valid levels: L1TP,L1GT,L1GS\
  Default: L1TP 


- --download\
  Download the product bundles directly after creating the download links.
- -n | --no-action\
  Only search for product bundles and print info about search results without generating links or downloading.
- -f | --forcelogs\
  Path to FORCE log file directory (Level-2 processing logs)\
  Links will only be generated for products that haven't been processed by FORCE yet.
- -q | --queue-file\
  Path to FORCE queue file.\
  Downloaded product bundle file paths will be appended to the queue.
- -s | --secret\
  Path to the file containing the username and password for M2MApi access (EarthExplorer login).\
  Avoids having to enter credentials every time the tool is run.\
  First line: user, second line: password

Example:
```
landsatlinks search /home/aoi.shp /home/landsatlinks/ -s ETM,OLI -d 2019-01-01,2021-12-31 -c 0,70 -m 5,6,7,8 --no-action

Sensor(s): ETM, OLI
Tile(s): 192023,192024,193023,193024
Date range: 2019-01-01 to 2021-12-31
Included months: 5,6,7,8
Cloud cover: 0% to 70%

116 Landsat Level 1 scenes matching criteria found
50.02 GB data volume found
```

__landatlinks download__

- url-file\
  Path to the file containing the download links.
- output-dir\
  The directory where the product bundles will be stored.
- -q | --queue-file\
  Path to FORCE queue file. Downloaded product bundle file paths will be appended to the queue.

Example:
```
landsatlinks download /home/landsatlinks/urls_landsat_TM_ETM_OLI_20221001T174038.txt /home/landsatlinks/

Loading urls from /home/landsatlinks/test/urls_landsat_TM_ETM_OLI_20221001T174038.txt

6 product bundles found in filesystem, 110 left to download.

Downloading: 5%|===>                                    | 6/110 [08:36<2:29:13, 100.97s/pproduct bundle/s]
```

The output directory will be checked for existing product bundles and only the missing ones are downloaded. Partial downloads (product bundles that are accompanied by .aria2 files) will be continued.

The M2M API is rate limited to 15,000 requests/15min. If you exceed this limit, the tool will wait for 15 and continue.

### License
MIT