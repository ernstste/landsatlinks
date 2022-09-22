import json
import requests
import sys
import landsatlinks.utils as utils
import time


class eeapi(object):

    def __init__(self, user, password):
        self.endpoint = 'https://m2m.cr.usgs.gov/api/api/json/stable/'
        self.key = self.login(user, password)

    def login(self, user, password):
        loginData = json.dumps({'username': user, 'password': password, 'catalogID': 'EE'})
        response = requests.post(f'{self.endpoint}login?', data=loginData).json()
        if response.get('errorCode', None):
            print(f'Error: {response["errorCode"]}: {response["errorMessage"]}\n'
                  'Please check your login data.\n'
                  'Login will fail if you did not request access to the M2M API yet.\n'
                  'Request access through your user profile at https://ers.cr.usgs.gov/')
            exit(1)
        return response['data']

    def logout(self):
        self.request('logout')

    def request(self, request_code, **kwargs):
        """
        Send a request to the machine2machine API.
        :type request_code: string
        :param request_code: Indicating method to API. List of codes: https://m2m.cr.usgs.gov/api/docs/reference/
        :type kwargs: dict
        :param kwargs: parameterization of the API request.
        :return: API response as dict
        """
        url = f'{self.endpoint}{request_code}'
        params = json.dumps(kwargs)
        headers = {'X-Auth-Token': self.key}
        response = requests.post(url, params, headers=headers).json()
        if response.get('errorCode', None):
            if response['errorCode'] == 'RATE_LIMIT_USER_DL':
                print('Rate limit exceeded. Will sleep for 15 minutes.')
                utils.countdown(905)
                response = requests.post(url, params, headers=headers).json()
                if response.get('errorCode', None):
                    print(f'Error: {response["errorCode"]}: {response["errorMessage"]}')
                    print('M2M API threw an error despite waiting.\nPlease open an issue on github if the error persists.')
                    sys.exit(1)
                return response['data']
            else:
                print(f'Error: {response["errorCode"]}: {response["errorMessage"]}')
                sys.exit(1)
        else:
            return response['data']

    def scene_search(self, start, end, dataset_name=None, entity_id=None, seasonal_filter=None, pr_list=None,
                     max_results=50000, **kwargs):
        """
        Search for scenes matching search criteria
        :param start: Temporal filter: start date
        :param end: Temporal filter: end date
        :param dataset_name: Name of the dataset to be queried (e.g. 'landsat_ot_c2_l1')
        :param entity_id: Entity ID to directly search for scenes
                          (legacy identifier in the format 'LC81920272020347LGN00')
        :param seasonal_filter: Temporal filter: months to be included (list of int)
        :param pr_list: Filter by path/row (list of int or str)
        :param max_results: maximum number of results returned
        :param kwargs: additional filters for the metadataFilter childFilters
        :return: List containing one dict per scene
        """
        if not dataset_name:
            print("No dataset defined. Use 'landsat_ot_c2_l1', 'landsat_etm_c2_l1', or 'landsat_tm_c2_l1'")
            exit(1)
        if dataset_name == 'landsat_ot_c2_l1':
            kwargs.update(sensor='OLI_TIRS', nadir='NADIR')

        if pr_list:
            paths = [pr[0:3] for pr in pr_list]
            rows = [pr[3:6] for pr in pr_list]
            p_min = min(paths)
            p_max = max(paths)
            r_min = min(rows)
            r_max = max(rows)
            kwargs.update(path_min=p_min, path_max=p_max, row_min=r_min, row_max=r_max)

        childFilters = utils.create_child_filters(dataset_name, **kwargs)
        sceneFilter = {
            'acquisitionFilter': {'start': start, 'end': end},
            'metadataFilter': {
                'filterType': 'and',
                'childFilters': childFilters
            }
        }
        if seasonal_filter:
            sceneFilter.update(seasonalFilter=seasonal_filter)
        searchParams = {
            'datasetName': dataset_name,
            'includeUnknownCloudCover': False,
            'maxResults': max_results,
            'sceneFilter': sceneFilter
        }
        if entity_id:
            searchParams.update(entityId=entity_id)

        response = self.request('scene-search', **searchParams)
        if response.get('errorCode', None):
            print(f'Error: {response["errorCode"]}: {response["errorMessage"]}')
            sys.exit(1)
        elif response['recordsReturned'] == 0:
            print('No scenes matching search results found. Exiting.')
            exit(0)
        else:
            return response['results']

    def get_download_options(self, dataset_name, scene_ids):
        """
        Retrieve download options, filter out the product bundles
        :param dataset_name: Name of the dataset to be queried (e.g., 'landsat_ot_c2_l1')
        :param scene_ids: List of entityIds (legacy scene identifiers, e.g., 'LC81920272020347LGN00')
        :return: List of dictionaries containing entity id and product id (e.g., '5e81f14ff4f9941c') for each
                 collection 2 level-1 product bundle
        """

        sceneIdsSplit = [scene_ids[i:i + 1000] for i in range(0, len(scene_ids), 1000)]
        dlOptions = []
        for i, entity_ids in enumerate(sceneIdsSplit):
            dl_options_params = {'datasetName': dataset_name, 'entityIds': entity_ids}
            response = self.request('download-options', **dl_options_params)
            dlOptions.extend(response)

        dlProductIds = []
        for product in dlOptions:
            # Make sure the product is available for this scene
            if product['productName'] == 'Landsat Collection 2 Level-1 Product Bundle':
                if product['available'] is True:
                    dlProductIds.append(
                        {
                            'entityId': product['entityId'],
                            'productId': product['id'],
                            'displayId': product['displayId'],
                            'filesize': product['filesize']
                        }
                    )

        return dlProductIds

    def get_download_links(self, dl_product_ids):
        """
        Retrieve download links for product bundles.
        Requests are split into chunks of 1000 as large numbers have been leading to issues.
        :param dl_product_ids: product ids (e.g., '5e81f14ff4f9941c') from get_download_options
        :return: List of download urls
        """

        dlSplit = [dl_product_ids[i:i + 1000] for i in range(0, len(dl_product_ids), 1000)]
        # Generate links
        urls = []
        for i, downloads in enumerate(dlSplit):
            dl_request_params = {'downloads': downloads}
            # Call the download to get the direct download urls
            response = self.request('download-request', **dl_request_params)
            for download in response['availableDownloads']:
                urls.append(download['url'])

        return urls
