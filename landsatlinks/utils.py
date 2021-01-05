
def create_meta_dict(filter_id, filter_type, **kwargs):
    meta_dict = {'filterId': filter_id, 'filterType': filter_type}
    for name, value in kwargs.items():
        meta_dict[name] = value
    return meta_dict


def create_child_filters(dataset_name, **kwargs):
    # use .get method to get value for key in position 1, use default value in 2 if key doesn't exist in dict
    data_type = kwargs.get('data_type', 'L1TP')
    tier = kwargs.get('tier', 'T1')
    day_night = kwargs.get('day_night', 'DAY')

    filters = []

    if data_type:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14fcf660794',
                filter_type='value',
                value=data_type
            ))
    if tier:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14fff5055a3',
                filter_type='value',
                value=tier
            ))
    if day_night:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14f61bda7c4',
                filter_type='value',
                value=day_night
            ))
    if 'max_cc' in kwargs and kwargs['max_cc']:
        filters.append(
            create_meta_dict(
                '5f6aa1a4e0985d4c',
                filter_type='between',
                firstValue=0,
                secondValue=kwargs['max_cc']
            ))
    if 'path_min' in kwargs and 'path_max' in kwargs:
        filters.append(
            create_meta_dict(
                '5e81f14f8faf8048',
                filter_type='between',
                firstValue=kwargs['path_min'],
                secondValue=kwargs['path_max']
            ))
    if 'row_min' in kwargs and 'row_max' in kwargs:
        filters.append(
            create_meta_dict(
                '5e81f14f8d2a7c24',
                filter_type='between',
                firstValue=kwargs['row_min'],
                secondValue=kwargs['row_max']
            ))
    if 'sensor' in kwargs and kwargs['sensor']:
        filters.append(
            create_meta_dict(
                filter_id='5e81f14f85d499dc',
                filter_type='value',
                value=kwargs['sensor']
            ))
    if 'nadir' in kwargs and kwargs['nadir']:
        filters.append(
            create_meta_dict(
                filter_id='5e81f150e42bc489',
                filter_type='value',
                value='NADIR'
            ))

    return filters


def filter_pathrow(scene_ids, pr_list):
    filtered_scenes = []
    for sceneName in scene_ids:
        if int(sceneName[10:16]) in pr_list:
            filtered_scenes.extend(sceneName)

    return filtered_scenes


def find_downloaded_scenes(search_path, recursive=True):
    from pathlib import Path
    import re
    # match Landsat 5/7/8 Collection 1/2 Level 1 folders and archives (.tar/.tar.gz)
    regexpattern = re.compile(
        '^L[C-T]0[578]_L1[A-Z]{2}_[0-9]{6}_[0-9]{8}_[0-9]{8}_0[12]_(RT|T1|T2)(.tar){0,1}(.gz){0,1}$')
    path = Path(search_path)
    if recursive:
        glob_pattern = '**/*'
    else:
        glob_pattern = '*'
    filepaths = list(path.glob(glob_pattern))

    scene_names = []
    for filepath in filepaths:
        filename = filepath.name
        if regexpattern.match(filename):
            suffixes = ''.join(filepath.suffixes)
            filename_nosuffix = str(filename).replace(suffixes, '')
            scene_names.append(filename_nosuffix)
    return scene_names


def load_tile_list(filepath):
    with open(filepath) as file:
        tile_list = [line.rstrip() for line in file]
    return tile_list


def filter_results_by_pr(scene_response, pr_list):
    filtered_scene_response = []
    for result in scene_response:
        if result['displayId'][10:16] in pr_list:
            filtered_scene_response.append(result)
    return filtered_scene_response
