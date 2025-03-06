import os
import platform
import re
import shutil
import sys
import time
from datetime import datetime
from math import floor, log
from pathlib import Path

PRODUCT_ID_REGEX = re.compile('(L[CET]0[45789]_L1[A-Z]{2}_[0-9]{6}_[0-9]{8}_[0-9]{8}_0[12]_T1|T2|RT)')
PROG_NAME = os.path.basename(sys.argv[0])


def countdown(seconds: int):
    while seconds:
        mins, secs = divmod(seconds, 60)
        timer = f'{mins:02d}:{secs:02d}'
        print(timer, end="\r")
        time.sleep(1)
        seconds -= 1
    print('...resuming')


def find_files(search_path: str, search_type: str,
               recursive: bool = True, no_partial_dls: bool = True) -> list:
    """
    Returns a list of names of tar(.gz) archives and folders, or logs, that are Landsat Level 1 products.
    :param no_partial_dls: If True, do not return product names if they are accompanied by aria2 temp files, to
    make sure partially downloaded files are going to be downloaded again.
    """

    path = Path(search_path)
    if recursive:
        glob_pattern = '**/*'
    else:
        glob_pattern = '*'
    file_paths = list(path.glob(glob_pattern))

    # match Landsat 5/7/8/9 Collection 1/2 Level 1 folders and archives (.tar/.tar.gz)
    if search_type == 'product':
        regex_pattern_string = \
            '^L[C-T]0[45789]_L1[A-Z]{2}_[0-9]{6}_[0-9]{8}_[0-9]{8}_0[12]_(RT|T1|T2)(.tar){0,1}(.gz){0,1}$'
        if no_partial_dls:
            regex_pattern_aria = re.compile(regex_pattern_string.replace('$', '.aria2$'))
            aria_tempfiles = [re.sub('\.tar\.aria2$', '', file_path.name) for file_path in file_paths
                              if re.match(regex_pattern_aria, file_path.name)]

    elif search_type == 'log':
        regex_pattern_string = \
            '^L[C-T]0[45789]_L1[A-Z]{2}_[0-9]{6}_[0-9]{8}_[0-9]{8}_0[12]_(RT|T1|T2)(.tar){0,1}(.log)$'
    else:
        raise ValueError(f'Error: invalid search_type specified. Received {search_type}, expected "product" or "log".')

    regex_pattern = re.compile(regex_pattern_string)

    scene_names = []
    for filepath in file_paths:
        filename = filepath.name
        if regex_pattern.match(filename):
            suffixes = ''.join(filepath.suffixes)
            filename = str(filename).replace(suffixes, '')
            if no_partial_dls and search_type == 'product':
                if filename not in aria_tempfiles:
                    scene_names.append(filename)
            else:
                scene_names.append(filename)

    return scene_names


def check_date_validity(dates: list, name: str) -> None:
    for date in dates:
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            print(f'Error: {name} dates not provided in format YYYYMMDD,YYYYMMDD or date is invalid.\ndate')
            exit(1)


def check_tile_validity(tile_list: list) -> bool:
    regex_pattern = re.compile('^[0-2][0-9]{2}[0-2][0-9]{2}$')
    tiles_valid = True
    for path_row in tile_list:
        if not regex_pattern.match(path_row):
            tiles_valid = False
            break
        if 1 > int(path_row[0:3]) > 233 or 1 > int(path_row[3:6]) > 248:
            tiles_valid = False
            break
    return tiles_valid


def load_tile_list(file_path: str) -> list:
    full_path = os.path.realpath(file_path)
    validate_file_paths(full_path, 'tile list', file=True, write=False)
    with open(file_path) as file:
        tile_list = [line.rstrip() for line in file]
    if not check_tile_validity(tile_list):
        print("Invalid tile list. Make sure the file contains one path/row per line in the format PPPRRR. Exiting.")
        exit(1)
    return tile_list


def filter_results_by_pr(scene_response: list, pr_list: list) -> list:
    filtered_scene_response = []
    for result in scene_response:
        if result['displayId'][10:16] in pr_list:
            filtered_scene_response.append(result)
    return filtered_scene_response


def load_secret(file_path: str) -> list:
    full_path = os.path.realpath(file_path)
    validate_file_paths(full_path, 'secrets', file=True, write=False)
    with open(file_path) as file:
        secret = file.read().strip().split()
        # remove whitespaces
        secret = [s.strip() for s in secret]
    if (
            len(secret) not in [2, 3] or
            len(secret) == 2 and secret[0] == 'app-token' or
            len(secret) == 3 and secret[0] != 'app-token'
    ):
        print(
            "Invalid secrets file. Expecting\n"
            "a) 1st line: user, 2nd line: password - deprecated by the USGS M2M API from February 2025\n"
            "b) 1st line: 'app-token', 2nd line: user, 3rd line: token"
        )
        exit(1)
    return secret


def validate_file_paths(path: str, name: str, file: bool = True, write: bool = False) -> str:
    path = os.path.realpath(path)
    if write:
        rw = os.W_OK
        rw_string = 'writeable'
    else:
        rw = os.R_OK
        rw_string = 'readable'
    if file:
        f_d = 'file'
    else:
        f_d = 'directory'

    if file:
        if not os.path.isfile(path):
            print(
                f'Error: The specified {name} file path does not seem to be a file.\n'
                f'{path}\n'
                f'Make sure to provide a path to a file, not a directory. Exiting.'
            )
            exit(1)
    else:
        if not os.path.isdir(path):
            print(
                f'Error: The specified {name} directory does not seem to be a directory.\n'
                f'{path}\n'
                f'Make sure to provide a path to a directory, not a file. Exiting.'
            )
            exit(1)
    if not os.access(path, rw):
        print(f"Error: {name.capitalize()} {f_d} does not exist or is not {rw_string}:\n{path}")
        exit(1)


def bytes_to_humanreadable(size):
    power = 0 if size <= 0 else floor(log(size, 1024))
    units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB']
    return f"{round(size / 1024 ** power, 2)} {units[int(power)]}"


def check_os():
    if platform.system() != 'Linux':
        print('Error: Downloading product bundles is only implemented for Linux.\n'
              'Please use the -n/--no-download option to download products manually. Exiting.')
        exit(1)


def check_dependencies(dependencies: list):
    for dependency in dependencies:
        if not shutil.which(dependency):
            print(f'Error: {dependency} does not seem to be installed.\n'
                  f'Please install or use the -n/--no-download option to download products manually. Exiting.')
            exit(1)
