#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule
from truenas_api_client import Client, ClientException


class Error(Exception):
    """Base class for other exceptions"""
    def __init__(self, message):
        super().__init__(message)


def login(client, api_key):
    """
    Login to the TrueNAS server using the API key.
    """
    result = client.call("auth.login_with_api_key", api_key)
    if result != True:
        raise Error("Failed to authenticate with API key, got result %r" % result)
    

def dataset_is_locked(client, dataset_id):
    """
    Check if the dataset with the given ID is locked.
    """
    datasets = client.call("pool.dataset.query")
    for dataset in datasets:
        if dataset['id'] == dataset_id:
            return dataset.get('locked')
    raise Error("Dataset with ID %r not found" % dataset_id)


def unlock_dataset(client, dataset_id, passphrase):
    """
    Unlock the dataset with the given ID using the provided passphrase.
    """
    options = dict(
        datasets=[dict(name=dataset_id, passphrase=passphrase)],
    )
    result = client.call("pool.dataset.unlock", dataset_id, options, job=True)
    if not isinstance(result, dict):
        raise Error(f"Failed to unlock dataset {dataset_id}, got malformed result {result}")
    unlocked = result.get('unlocked', None)
    if unlocked is None or not isinstance(unlocked, list):
        raise Error(f"Failed to unlock dataset {dataset_id}, got malformed result {result}")
    if dataset_id not in unlocked:
        raise Error(f"Failed to unlock dataset {dataset_id}, got result {result}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True, no_log=True),
            host=dict(type='str', required=True),
            dataset_id=dict(type='str', required=True),
            passphrase=dict(type='str', required=True, no_log=True),
        ),
    )

    host = module.params['host']
    api_key = module.params['api_key']
    dataset_id = module.params['dataset_id']
    passphrase = module.params['passphrase']
    try:
        uri = f"wss://{host}/websocket"
        client = Client(uri, verify_ssl=False)
        login(client, api_key)
        locked = dataset_is_locked(client, dataset_id)
        if not locked:
            return module.exit_json(changed=False)
        unlock_dataset(client, dataset_id, passphrase)
        module.exit_json(changed=True)
    except Error as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()