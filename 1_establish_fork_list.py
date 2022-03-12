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
    print(f'{time.time():<20} retrieving {url}')
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

    print(f'{time.time():<20} waiting {wait_time} seconds')
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
            tree_data['forks'].append(retrieve_recursive_forks_from_api_package(fork_api_package))

    return tree_data


def retrieve_recursive_forks_from_repo_description(user_name, repo_name):
    # entry level function for constructing tree data for base repo

    url = f'https://api.github.com/repos/{user_name}/{repo_name}'
    api_package, links = retreive_api_page(url)

    return retrieve_recursive_forks_from_api_package(api_package)


def node_key(node):
    user_name = node['api_package']['owner']['login']
    repo_name = node['api_package']['name']
    key = (user_name, repo_name)

    return key


def find_tree_node(base_tree, parent_user_name, parent_repo_name):
    # finds node in base_tree
    # returns None is specified node not found in base_tree

    current_key = node_key(base_tree)
    parent_key = (parent_user_name, parent_repo_name)

    if current_key == parent_key:
        return [current_key]

    for fork in base_tree['forks']:
        sub_location = find_tree_node(fork, parent_user_name, parent_repo_name)
        if sub_location is not None:
            return [current_key] + sub_location

    return None


def insert_tree_data(base_tree, child_tree, parent_user_name, parent_repo_name):
    # inserts child_tree into base_tree at specified parent
    # requires parent to exist in base_tree
    # returns modified base_tree

    # acquire insertion_location
    insertion_location = find_tree_node(base_tree, parent_user_name, parent_repo_name)
    assert insertion_location is not None, (parent_user_name, parent_repo_name)

    # location should always begin with tree root, which we do not need to search for
    base_key = node_key(base_tree)
    assert insertion_location[0] == base_key, (insertion_location[0], base_key)
    del insertion_location[0]

    # acquire parent node
    sub_tree = base_tree
    for insertion_key in insertion_location:
        for fork in sub_tree['forks']:
            fork_key = node_key(fork)
            if fork_key == insertion_key:
                sub_tree = fork
                break

        else:
            raise ValueError(f"insertion_key is invalid, {insertion_key} from {insertion_location}")

    # insert tree data
    sub_tree['forks'].append(child_tree)

    return base_tree


def manually_link_tree_data(user_name, repo_name, parent_user_name, parent_repo_name, tree_data):
    # manually links a repo to a parent repo
    # looks up api package for given repo and inserts into tree data
    # requires parent repo to exist (anywhere) in tree_data

    # check if node already exists in tree
    if find_tree_node(tree_data, user_name, repo_name) is None:
        # create a new child tree for non-existent node, and insert it into the correct location in the tree
        child_tree = retrieve_recursive_forks_from_repo_description(user_name, repo_name)
        tree_data = insert_tree_data(tree_data, child_tree, parent_user_name, parent_repo_name)

    return tree_data


# 'watchers_count'

if __name__ == '__main__':
    # collected manual links from https://pixeldungeon.fandom.com/wiki/Category:Mods on Mar-03-2022

    tree_data = retrieve_recursive_forks_from_repo_description('watabou', 'pixel-dungeon')
    tree_data = manually_link_tree_data('00-Evan', 'shattered-pixel-dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('dachhack', 'SproutedPixelDungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('hmdzl001', 'SPS-PD', 'dachhack', 'SproutedPixelDungeon', tree_data)
    tree_data = manually_link_tree_data('ConsideredHamster', 'YetAnotherPixelDungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('egoal', 'darkest-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('HappyAlfred', 'fushigi-no-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('3oiDburg', 'WuWuWu', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('rodriformiga', 'pixel-dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('NYRDS', 'remixed-dungeon', 'rodriformiga', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('pseusys', 'PXL610', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('Smujb', 'powered-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('Smujb', 'cursed-pixel-dungeon', 'Smujb', 'powered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('BrightBotTeam', 'DeisticPixelDungeon', 'dachhack', 'SproutedPixelDungeon', tree_data)
    tree_data = manually_link_tree_data('Arcnor', 'pixel-dungeon-gdx', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('arfonzocoward', 'dixel-pungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('G2159687', 'ESPD', 'dachhack', 'SproutedPixelDungeon', tree_data)
    tree_data = manually_link_tree_data('G2159687', 'Easier-Vanilla-Pixel-Dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('TrashboxBobylev', 'experienced-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('TrashboxBobylev', 'Experienced-Pixel-Dungeon-Redone', '00-Evan', 'shattered-pixel-dungeon', tree_data)  # play this
    tree_data = manually_link_tree_data('Sharku2011', 'GirlsFrontline-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('FthrNature', 'unleashed-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('locastan', 'GoblinsPixelDungeonGradle', 'FthrNature', 'unleashed-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('Smujb', 'harder-sprouted-pd', 'dachhack', 'SproutedPixelDungeon', tree_data)
    tree_data = manually_link_tree_data('afomins', 'pixel-dungeon-3d', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('Zrp200', 'lustrous-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('Meduris', 'MinecraftPixelDungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('ndachel', 'PD-ice', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('Meduris', 'german-pixel-dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('AnonymousPD', 'OvergrownPixelDungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('AnonymousPD', 'OvergrownPD', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('bilbolPrime', 'SPD', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('etoitau', 'Pixel-Dungeon-Echo', 'bilbolPrime', 'SPD', tree_data)
    tree_data = manually_link_tree_data('gohjohn', 'phoenix-pixel-dugeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('lighthouse64', 'Random-Dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('cuneytoner', 'PixelDungeonRemake', 'NYRDS', 'remixed-dungeon', tree_data)
    tree_data = manually_link_tree_data('QuasiStellar', 'Re-Remixed_Dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('umarnobbee', 'Ripped-Pixel-Dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('MarshalldotEXE', 'rivals-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('wolispace', 'soft-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('TrashboxBobylev', 'Summoning-Pixel-Dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('CuteLunaMoon', 'Survival-Pixel-Dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('juh9870', 'TooCruelPixelDungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('keithr-git', 'tunable-pixel-dungeon', 'watabou', 'pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('mango-tree', 'UNIST-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)
    tree_data = manually_link_tree_data('FthrNature', 'unleashed-pixel-dungeon', '00-Evan', 'shattered-pixel-dungeon', tree_data)

    # TODO implement gitlab APIs 
    # https://pixeldungeon.fandom.com/wiki/No_Name_Yet_Pixel_Dungeon#Overview 
    #   https://gitlab.com/RavenWolfPD/nonameyetpixeldungeon
    #   tree_data = manually_link_tree_data('RavenWolfPD', 'nonameyetpixeldungeon', 'ConsideredHamster', 'YetAnotherPixelDungeon', tree_data)

    # TODO implement bitbucket APIs
    # https://pixeldungeon.fandom.com/wiki/Moonshine_Pixel_Dungeon
    #   https://bitbucket.org/juh9870/moonshine/src/master/

    # source code not available
    # https://pixeldungeon.fandom.com/wiki/Dungeon_Run_WIP
    # https://pixeldungeon.fandom.com/wiki/Easier_Pixel_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Easy_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Frog_Pixel_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Hell_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Hell_Dungeon_Rewarded
    # https://pixeldungeon.fandom.com/wiki/Jojo%27s_Bizarre_Adventure_(%EC%A3%A0%EC%A3%A0%EC%9D%98_%EA%B8%B0%EB%AC%98%ED%95%9C_%EB%8D%98%EC%A0%84)
    # https://pixeldungeon.fandom.com/wiki/Loot_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Loot_Dungeon_Shattered
    # https://pixeldungeon.fandom.com/wiki/Lovecraft_Pixel_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Perfect_Pixel_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Pixel_Dungeon_%2B
    # https://pixeldungeon.fandom.com/wiki/Pixel_Dungeon_2
    # https://pixeldungeon.fandom.com/wiki/Pixel_Dungeon_Easy_Mode
    # https://pixeldungeon.fandom.com/wiki/Pixel_Dungeon_Prayers
    # https://pixeldungeon.fandom.com/wiki/Plugin_Pixel_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Prismatic_Pixel_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Rat_King_Dungeon
    # https://pixeldungeon.fandom.com/wiki/Shattered_Trap_Dungeon

    # save tree data
    f = open('fork_tree_data.json', 'w')
    f.write(json.dumps(tree_data))
    f.close()

