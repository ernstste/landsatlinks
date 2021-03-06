# landsatlinks


##### Creating download urls for Landsat Collection 2 Level 1 product bundles using the USGS/EROS Machine-to-Machine API
![Python Version](https://img.shields.io/badge/python-%3E=v3.6-blue)
![License](https://img.shields.io/badge/license-MIT-brightgreen) 

landsatlinks offers a simple command line interface to retrieve download links for Landsat Collection 2 Level 1 product bundles through the USGS/EROS machine-to-machine API.

Features include:
  - an extensive set of filtering methods
  - 'resuming' when links have expired - including a filesystem check for finished downloads


### Requirements
User credentials to login to the USGS EarthExplorer interface are required. The user account needs to have access to the machine-to-machine API, which can be requested through the user profile [here](https://ers.cr.usgs.gov/profile/access).\
Python >= 3.6 is required.


### Installation
Simply install using pip:
```
python -m pip install git+https://github.com/ernstste/landsatlinks.git
```

### Usage
There are three mandatory arguments required to run the tool and several optional arguments that allow a more detailed search for scenes. Scroll down for a quick explanation of every argument. A call may look like this:

![CLI first run](https://raw.githubusercontent.com/ernstste/landsatlinks/master/demo/first_run.gif)


__required arguments:__
- results\
  Provide a path to a file containing the search results created by landsatlinks. This will be created during the first run, or opened in consecutive runs when new links need to be created because the old ones expired. The file containing download links will be created in the same directory, using the name _urls\_landsat\_[sensor]\_c2\_l1\_[timestamp].txt_
- sensor\
  The sensor that scenes are requested for.\
  choices = 'TM', 'ETM', 'OLI' (Landsat 4/5, Landsat 7, Landsat 8)
- pathrowlist\
  Text file containing allowed pathrows combinations\
  The list of allowed paths/rows must contain __one path/row per line__.\
  Format: PPPRRR (Keep padding zeroes!). Good: 194023, bad: 19432

__optional arguments:__
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

__A note on 'resuming':__\
Links are only valid for a certain time and then expire. If there is a large number of downloads, it's likely that not all files could be downloaded before the links expired. landsatlinks will check the filesystem (the directory where the 'results' file is stored and it's subdirectories) for downloaded products and only generate download links for scenes that weren't found in the file system. This should also work if the .tar archives have already been extracted. __Note__ that this does not include a check to see if archives are broken or only partially downloaded.

![CLI second run](https://raw.githubusercontent.com/ernstste/landsatlinks/master/demo/consecutive_run.gif)


### Limitations
Unfortunately, the API access is not always 100% reliable. Timeouts have been observed on and off, particularly when the size of the response grows. The requests are split into chunks of 1000 elements to mitigate issues. On a normal day this should work fine. It should be mentioned though that we've also seen days where this had to be reduced drastically or where it was simply not possible to get responses. Good luck :)


### Hints
To keep things lightweight, this tool only allows a list of footprints (path/row) to define the area of interest. Don't know which footprints (path/row) you need? You can download the Landsat WRS-2 shapefile [here](https://www.usgs.gov/media/files/landsat-wrs-2-descending-path-row-shapefile) or use the [EOLab EO Grids Web Feature Service (WFS)](https://ows.geo.hu-berlin.de/services/eo-grids/).

### License
MIT