import multiprocessing as mp
import os
import re
import signal
from datetime import datetime

from tqdm import tqdm

from landsatlinks import utils


def load_links(filepath: str) -> list:
    utils.validate_file_paths(filepath, 'url', file=True, write=False)
    with open(filepath, 'r') as f:
        links = f.read().splitlines()
    if not links:
        print(f'File seems to be empty {filepath}')
    return links


def check_for_broken_links(links: list) -> bool:
    pattern = re.compile('https://landsatlook\.usgs\.gov/gen-bundle\?landsat_product_id=.{258,262}$')
    broken_links = [link for link in links if not re.match(pattern, link)]
    if broken_links:
        print(f'Some links seem to be broken, please check:')
        print(*broken_links, sep='\n')
        exit(1)

    return True


def check_for_downloaded_scenes(links: str, dest_folder: str, no_partial_dls: bool = True) -> list:
    """
    Remove all urls for product bundles that are present in dest_folder
    """
    products_in_filesystem = utils.find_files(
        dest_folder, 'product', recursive=True, no_partial_dls=no_partial_dls
    )
    not_downloaded = [url for url in links if re.findall(utils.PRODUCT_ID_REGEX, url)[0] not in products_in_filesystem]

    return not_downloaded


def download_worker(url: str, dest: str) -> None:
    import subprocess
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    subprocess.call(
        [
            'aria2c',
            '--dir', dest,
            '--max-concurrent-downloads', '3',
            '--max-connection-per-server', '5',
            '--max-tries', '5',
            '--retry-wait', '400',
            '--quiet',
            '--continue',
            '--log', os.path.join(dest, f'landsatlinks_{datetime.strftime(datetime.now(), "%Y-%m-%dT%H%M%S")}.log'),
            '--log-level', 'notice',
            url
        ]
    )


def download(urls: list, dest_folder: str, n_tasks: int = 3) -> str:
    pool = mp.Pool(n_tasks)
    progress_bar = tqdm(total=len(urls), desc=f'Downloading', unit='product bundle', ascii=' >=')

    for url in urls:
        pool.apply_async(download_worker, (url, dest_folder,), callback=lambda _: progress_bar.update())
    pool.close()
    pool.join()

    return 'Download complete'


def download_standalone(links_fp: str, output_dir: str, n_tasks: int = 3) -> str:

    print(f'Loading urls from {links_fp}\n')
    urls = load_links(links_fp)
    check_for_broken_links(urls)
    urls_to_download = check_for_downloaded_scenes(urls, output_dir)

    n_left = len(urls_to_download)
    if not n_left:
        print(f'All products already present in filesystem.\n{output_dir}\nExiting.')
        exit()

    print(
        f'{len(urls) - len(urls_to_download)} product bundles found in filesystem, '
        f'{n_left} left to download.\n'
    )

    download(urls_to_download, output_dir, n_tasks)

    print('Download complete')


