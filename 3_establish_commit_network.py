import json
import os
import subprocess
from util import clone_folder_path


def pull_node_commit_history(node):
    # pulls commit history for a single repo

    # navigate to cloned directory and extract a formatted git log
    cwd = os.getcwd()
    os.chdir(os.path.join(cwd, clone_folder_path(node)))
    git_log = subprocess.run(['git', 'log', '--pretty=format:"%at %H"'], capture_output=True)
    os.chdir(cwd)

    # parse log
    log = re.sub('"', '', git_log)
    history = []
    for line in log.strip().split('\n'):
        timestamp, commit_hash = line.strip().split()
        timestamp = int(timestamp)

        entry = (timestamp, commit_hash)
        history.append(entry)

    return history


def recursively_pull_commit_histories(tree):
    # pulls commit history for all repos, storing as new key in tree

    # add root node
    tree['commit_history'] = pull_node_commit_history(tree)

    # add all forks
    for fork in tree['forks']:
        tree = recursively_pull_commit_histories(fork)

    return tree


def latest_common_commit(parent, child):
    # establishes latest commit hash common to both repos

    parent_commit_history = parent['commit_history']
    child_commit_history = child['commit_history']
    child_hashes = [commit_hash for timestamp, commit_hash in child_commit_history]

    for timestamp, commit_hash in sorted(parent_commit_history, reverse=True):
        if commit_hash in child_hashes:
            return commit_hash

    raise ValueError(f'No common hash found bewtween parent and child\n{parent_commit_history}\n{child_commit_history}')


def establish_latest_common_commits(tree):
    # establishes latest commit hashes common to each parent-child pair
    # stores as property of the fork
    # property does not exist on the root node (no parent)

    for fork in tree['forks']:
        try:
            commit_hash = latest_common_commit(tree, fork)
        except:
            # add info in case of error
            print(f'{tree['api_package']['full_name']} -> {fork['api_package']['full_name']}')
            raise

        fork['latest_commit_common_with_parent'] = commit_hash

    return tree


def main():
    f = open('fork_tree_data.json', 'r')
    tree = json.loads(f.read())
    f.close()

    tree = recursively_pull_commit_histories(tree)
    tree = establish_latest_common_commits(tree)

    # save modified data strcuture
    f = open('fork_tree_data_3.json', 'w')
    f.write(json.dumps(tree))
    f.close()


if __name__ == '__main__':
    main()
