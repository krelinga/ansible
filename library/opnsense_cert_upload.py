#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule

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

    module.exit_json(changed=False)


if __name__ == '__main__':
    main()
