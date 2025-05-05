#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule

import requests
from requests.auth import HTTPBasicAuth

def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True, no_log=True),
            api_secret=dict(type='str', required=True, no_log=True),
            certificate=dict(type='str', required=True),
            private_key=dict(type='str', required=True),
            host=dict(type='str', required=True),
        )
    )

    certificate = module.params['certificate']
    private_key = module.params['private_key']
    api_key = module.params['api_key']
    api_secret = module.params['api_secret']
    host = module.params['host']


    uri = f"https://{host}/api/trust/cert/search"
    try:
        response = requests.get(uri, auth=HTTPBasicAuth(api_key, api_secret), verify=False)
        if response.status_code == 200:
            module.exit_json(changed=False, response=response.json())
        else:
            module.fail_json(msg=f"HTTP GET request failed with status code {response.status_code}", response=response.json())
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=f"HTTP GET request encountered an error: {str(e)}")


if __name__ == '__main__':
    main()
