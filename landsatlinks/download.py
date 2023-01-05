import multiprocessing
import multiprocessing as mp
import os
import re
import signal

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


def create_force_queue(url: str, output_dir: str, queue_fp: str) -> None:
    scene_name = f'{re.search(utils.PRODUCT_ID_REGEX, url).group(0)}.tar'
    scene_path = os.path.join(os.path.realpath(output_dir), scene_name)

    if os.path.exists(scene_path) and not os.path.exists(f'{scene_path}.aria2'):
        with open(queue_fp, 'a') as f:
            f.write(f'{scene_path} QUEUED\n')


def download_worker(url: str, output_dir: str, mp_queue: multiprocessing.Queue) -> None:
    import subprocess
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    subprocess.call(
        [
            'aria2c',
            '--dir', output_dir,
            '--max-concurrent-downloads', '3',
            '--max-connection-per-server', '5',
            '--max-tries', '5',
            '--retry-wait', '400',
            '--quiet',
            '--continue',
            url
        ]
    )
    mp_queue.put(url)

    return url


def dl_listener_for_force_queue(output_dir: str, queue_fp: str, mp_queue: multiprocessing.Queue) -> None:
    """Listens to urls on the multiprocessing queue and runs create_force_queue"""

    if queue_fp:
        with open(queue_fp, 'a') as f:
            while True:
                url = mp_queue.get()
                if url == 'finished':
                    break

                scene_name = f'{re.search(utils.PRODUCT_ID_REGEX, url).group(0)}.tar'
                scene_path = os.path.join(os.path.realpath(output_dir), scene_name)
                if os.path.exists(scene_path) and not os.path.exists(f'{scene_path}.aria2'):
                    f.write(f'{scene_path} QUEUED\n')
                    f.flush()

    else:
        while True:
            url = mp_queue.get()
            if url == 'finished':
                break


def download(urls: list, output_dir: str, n_tasks: int = 4, force_queue_fp: str = None) -> None:
    manager = mp.Manager()
    mp_queue = manager.Queue()
    pool = mp.Pool(n_tasks)
    # set up watcher to listen for new results that can be added to the force_queue
    watcher = pool.apply_async(dl_listener_for_force_queue, (output_dir, force_queue_fp, mp_queue))

    progress_bar = tqdm(total=len(urls), desc=f'Downloading', unit='product bundle', ascii=' >=')
    # logpath = os.path.join(output_dir, f'landsatlinks_{datetime.strftime(datetime.now(), "%Y-%m-%dT%H%M%S")}.log')

    def callback(url):
        progress_bar.update()

    # set up jobs
    jobs = []
    for url in urls:
        job = pool.apply_async(download_worker, (url, output_dir, mp_queue), callback=callback)
        jobs.append(job)

    # collect the results
    for job in jobs:
        job.get()

    # tell listener to stop
    mp_queue.put('finished')
    pool.close()
    pool.join()


def download_standalone(links_fp: str, output_dir: str, n_tasks: int = 3, queue_fp: str = None) -> str:

    print(f'\nLoading urls from {links_fp}\n')
    urls = load_links(links_fp)
    check_for_broken_links(urls)
    urls_to_download = check_for_downloaded_scenes(urls, output_dir)

    n_left = len(urls_to_download)
    if not n_left:
        print(f'All products already present in filesystem.\n{output_dir}\nExiting.')
        exit()
    if n_left == len(urls):
        print(f'Found {len(urls)} product bundle URLs.')
    else:
        print(
            f'{len(urls) - n_left} of {len(urls)} product bundles found in filesystem, '
            f'{n_left} left to download.\n'
        )

    download(urls_to_download, output_dir, n_tasks, queue_fp)

    print('Download complete')
