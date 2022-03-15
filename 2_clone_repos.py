import json
import os
import subprocess
import time
from util import clone_folder_path
from util import github_rate_limit
from util import repos_folder


def clone_repo(node, wait_time=github_rate_limit):
    destination = clone_folder_path(node)
    url = node['api_package']['clone_url']

    if not os.path.exists(destination):
        # perform cloning operation
        subprocess.run(['git', 'clone', url, destination])

        # rate limit
        print(f'\n{time.time():<20} waiting {wait_time} seconds\n')
        time.sleep(wait_time)


def recursively_clone_repos(tree):
    # clone root node
    clone_repo(tree)

    # clone all forks
    for fork in tree['forks']:
        recursively_clone_repos(fork)


if __name__ == '__main__':
    f = open('fork_tree_data.json', 'r')
    tree = json.loads(f.read())
    f.close()

    if not os.path.exists(repos_folder):
        os.mkdir(repos_folder)

    recursively_clone_repos(tree)
