#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule
from truenas_api_client import Client

def main():
    module = AnsibleModule(argument_spec=dict())
    msg = "failed to use client"

    with Client("wss://truenas.i.krel.ing/websocket", verify_ssl=False) as c:
        resp = c.call("system.general.country_choices")
        msg = str(resp)

    module.exit_json(changed=False, msg=msg)


if __name__ == '__main__':
    main()
