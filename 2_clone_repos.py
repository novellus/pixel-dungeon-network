import json
import os
import subprocess
import time


github_rate_limit = 61 # seconds betweeen requests
repos_folder = 'repos'


def clone_folder_name(node):
    user_name = node['api_package']['owner']['login']
    repo_name = node['api_package']['name']
    name = f'{user_name},{repo_name}'

    return name


def clone_repo(node, wait_time=github_rate_limit):
    destination = os.path.join(repos_folder, clone_folder_name(node))
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
