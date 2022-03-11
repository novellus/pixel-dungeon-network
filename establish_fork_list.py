import json
import os
import pprint
import re
import requests
import time


github_rate_limit = 61 # default seconds betweeen requests. Actual is usually judged by feedback from server
API_cache_location = 'api_cache'


def url_to_cache_name(url):
    return os.path.join(API_cache_location, re.sub('[://\.?=]', ',', url))


def check_for_API_cache(url):
    path = url_to_cache_name(url)
    if os.path.exists(path):
        f = open(path, 'r')
        return_package = json.loads(f.read())
        f.close()
        return return_package
    else:
        return None


def write_API_cache(url, data_package):
    path = url_to_cache_name(url)
    f = open(path, 'w')
    f.write(json.dumps(data_package))
    f.close()



def retreive_api_page(url, default_wait_time=github_rate_limit, read_cache=True, write_cache=True):
    # retrieves a single API page, parses the GET, and returns select data

    # check for cached value first
    if read_cache:
        cached_data = check_for_API_cache(url)
        if cached_data:
            return cached_data

    # no cached value, retrieve fresh data
    print(f'{time.time():20} retrieving {url}')
    ret = requests.get(url)

    assert ret.status_code == 200

    # convert primary data package to json
    try:
        data_package = ret.json()
    except:
        print('failed json conversion', url)
        print('status_code:', ret.status_code)
        print('headers:')
        pprint.pprint(dict(ret.headers))
        print()
        print('text:', ret.text)

    return_package = (data_package, ret.links)

    # store cached data for later retrieval
    if write_cache:
        write_API_cache(url, return_package)

    # rate limit
    # check specifications from response headers
    headers = ret.headers
    rate_limit_remaining = int(headers['X-RateLimit-Remaining'])
    rate_limit_reset = int(headers['X-RateLimit-Reset'])
    if time.time() < rate_limit_reset:
        wait_time = 1 + (rate_limit_reset - time.time()) / rate_limit_remaining
    else:
        wait_time = default_wait_time

    print(f'{time.time():20} waiting {wait_time} seconds')
    time.sleep(wait_time)

    return return_package


def retrieve_repo_forks(url):
    # retrieves all forks for a single repo, distributed over several API calls

    forks, links = retreive_api_page(url)
    while 'next' in links:
        _forks, links = retreive_api_page(links['next']['url'])
        forks.extend(_forks)

    return forks


def retrieve_recursive_forks_from_api_package(api_package):
    # constructs tree data for base repo, recursively traversing all forks
    # requires API package as input, see below function for entry point with only a repo description

    tree_data = {'api_package': api_package,
                 'forks': []}

    # retrieve recursive data packages, and construct tree data
    if api_package['forks_count'] > 0:
        forks_url = api_package['forks_url']
        forks_api_packages = retrieve_repo_forks(forks_url)

        for fork_api_package in forks_api_packages:
            tree_data['forks'].append(retrieve_recursive_repo_forks(fork_api_package))

    return tree_data


def retrieve_recursive_forks_from_repo_description(user_name, repo_name):
    # entry level function for constructing tree data for base repo

    url = f'https://api.github.com/repos/{user_name}/{repo_name}'
    api_package, links = retreive_api_page(url)

    return retrieve_recursive_forks_from_api_package(api_package)


# 'watchers_count'

if __name__ == '__main__':
    tree_data = retrieve_recursive_forks_from_repo_description('watabou', 'pixel-dungeon')

    # save tree data
    f = open('fork_tree_data.json', 'w')
    f.write(json.dumps(tree_data))
    f.close()

