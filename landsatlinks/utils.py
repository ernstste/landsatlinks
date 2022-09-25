from math import floor, log
from pathlib import Path
import platform
import os
import re
import shutil
import time


def countdown(seconds: int):
    while seconds:
        mins, secs = divmod(seconds, 60)
        timer = f'{mins:02d}:{secs:02d}'
        print(timer, end="\r")
        time.sleep(1)
        seconds -= 1
    print('...resuming')


def create_meta_dict(filter_id: str, filter_type: str, **kwargs) -> dict:
    meta_dict = {'filterId': filter_id, 'filterType': filter_type}
    for name, value in kwargs.items():
        meta_dict[name] = value
    return meta_dict


def create_child_filters(**kwargs) -> list:
    # use .get method to get value for key in position 1, use default value in 2 if key doesn't exist in dict
    data_type_l1 = kwargs.get('data_type_l1', 'L1TP')
    tier = kwargs.get('tier', 'T1')
    day_night = kwargs.get('day_night', 'DAY')

    filters = []

    if data_type_l1:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14fcf660794',
                filter_type='value',
                value=data_type_l1
            )
        )
    if tier:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14fff5055a3',
                filter_type='value',
                value=tier
            )
        )
    if day_night:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14f61bda7c4',
                filter_type='value',
                value=day_night
            )
        )
    if 'max_cc' in kwargs and kwargs['max_cc']:
        filters.append(
            create_meta_dict(
                '5f6aa1a4e0985d4c',
                filter_type='between',
                firstValue=0,
                secondValue=kwargs['max_cc']
            )
        )
    if 'path_min' in kwargs and 'path_max' in kwargs:
        filters.append(
            create_meta_dict(
                '5e81f14f8faf8048',
                filter_type='between',
                firstValue=kwargs['path_min'],
                secondValue=kwargs['path_max']
            )
        )
    if 'row_min' in kwargs and 'row_max' in kwargs:
        filters.append(
            create_meta_dict(
                '5e81f14f8d2a7c24',
                filter_type='between',
                firstValue=kwargs['row_min'],
                secondValue=kwargs['row_max']
            )
        )
    if 'sensor' in kwargs and kwargs['sensor']:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14f85d499dc',
                filter_type='value',
                value=kwargs['sensor']
            )
        )
    if 'nadir' in kwargs and kwargs['nadir']:
        filters.append(
            create_meta_dict(
                filter_id='5e81f150e42bc489',
                filter_type='value',
                value='NADIR'
            )
        )

    return filters


def filter_pathrow(scene_ids: list, pr_list: list) -> list:
    filtered_scenes = []
    for sceneName in scene_ids:
        if int(sceneName[10:16]) in pr_list:
            filtered_scenes.extend(sceneName)

    return filtered_scenes


def find_files(search_path: str, search_type: str, recursive: bool = True, no_suffix: bool = True) -> list:
    # match Landsat 5/7/8/9 Collection 1/2 Level 1 folders and archives (.tar/.tar.gz)
    if search_type == 'product':
        regex_pattern = re.compile(
            '^L[C-T]0[45789]_L1[A-Z]{2}_[0-9]{6}_[0-9]{8}_[0-9]{8}_0[12]_(RT|T1|T2)(.tar){0,1}(.gz){0,1}$')

    elif search_type == 'log':
        regex_pattern = re.compile(
            '^L[C-T]0[45789]_L1[A-Z]{2}_[0-9]{6}_[0-9]{8}_[0-9]{8}_0[12]_(RT|T1|T2)(.tar){0,1}(.log)$')
    else:
        raise ValueError(f'Error: invalid search_type specified. Received {search_type}, expected "product" or "log".')

    path = Path(search_path)
    if recursive:
        glob_pattern = '**/*'
    else:
        glob_pattern = '*'
    file_paths = list(path.glob(glob_pattern))

    scene_names = []
    for filepath in file_paths:
        filename = filepath.name
        if regex_pattern.match(filename):
            if no_suffix:
                suffixes = ''.join(filepath.suffixes)
                scene_names.append(str(filename).replace(suffixes, ''))
            else:
                scene_names.append(filename)
    return scene_names


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
    with open(file_path) as file:
        tile_list = [line.rstrip() for line in file]
    if not check_tile_validity(tile_list):
        print("Invalid tile list. Make sure the file contains one path/row per line in the format PPPRRR. Exiting.")
        exit(1)
    return tile_list


def load_secret(file_path: str) -> list:
    with open(file_path) as file:
        secret = [line.rstrip() for line in file]
    if len(secret) != 2:
        print("Invalid secrets file. Make sure the file only has two lines with the first line being the username "
              "and the second line being the password. Exiting.")
        exit(1)
    return secret


def filter_results_by_pr(scene_response: list, pr_list: list) -> list:
    filtered_scene_response = []
    for result in scene_response:
        if result['displayId'][10:16] in pr_list:
            filtered_scene_response.append(result)
    return filtered_scene_response


def check_file_paths(path: str, name: str, file: bool = True):
    if file:
        if not os.path.splitext(path)[1]:
            print(
                f'Error: The specified {name} file does not seem to have a file ending.\n'
                f'{path}\n'
                f'Make sure to provide a path to a file, not a directory. Exiting.'
            )
            exit(1)
    else:
        if os.path.splitext(path)[1]:
            print(
                f'Error: The specified {name} directory does not seem to be a directory.\n'
                f'{path}'
                f'Make sure to provide a path to a directory, not a file. Exiting.'
            )
            exit(1)
    if not os.access(os.path.dirname(path), os.W_OK):
        print(
            f'Error: Directory where {name} are supposed to be stored does not exists or is not writeable:\n'
            f'{path}\nExiting.'
        )
        exit(1)


def bytes_to_humanreadable(size):
    power = 0 if size <= 0 else floor(log(size, 1024))
    units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB']
    return f"{round(size / 1024 ** power, 2)} {units[int(power)]}"


def check_dependencies(dependencies: list):
    for dependency in dependencies:
        if not shutil.which(dependency):
            print(f'Error: {dependency} does not seem to be installed.\n'
                  f'Please install or use the -n/--no-download option to download products manually. Exiting.')
            exit(1)


def check_os():
    if platform.system() != 'Linux':
        print('Error: Downloading product bundles is only implemented for Linux.\n'
              'Please use the -n/--no-download option to download products manually. Exiting.')
        exit(1)
