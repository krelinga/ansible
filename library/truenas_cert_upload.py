#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule
from truenas_api_client import Client

def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True)
        )
    )
    msg = "failed to use client"

    # https://forums.truenas.com/t/getting-error-trying-to-connect-via-truenas-api-client-to-websockets-api-endpoint-api-current/28152
    with Client("wss://truenas.i.krel.ing/websocket", verify_ssl=False) as c:
        resp = c.call("auth.login_with_api_key", module.params['api_key'])
        assert resp
        resp = c.call("system.general.country_choices")
        msg = str(resp)

    module.exit_json(changed=False, msg=msg)


if __name__ == '__main__':
    main()
