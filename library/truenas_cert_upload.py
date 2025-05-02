#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule
from truenas_api_client import Client

CERT_NAME = "certbot"

def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True),
            certificate=dict(type='str', required=True),
            private_key=dict(type='str', required=True),
        )
    )

    # https://forums.truenas.com/t/getting-error-trying-to-connect-via-truenas-api-client-to-websockets-api-endpoint-api-current/28152
    with Client("wss://truenas.i.krel.ing/websocket", verify_ssl=False) as c:
        if c.call("auth.login_with_api_key", module.params['api_key']) == False:
            module.fail_json(msg="Failed to authenticate with API key")
            return
        
        custom_results = {}
        certs = c.call("certificate.query", [], dict(
            prefix=CERT_NAME,
        ))
        custom_results['certificates'] = certs
        for cert in certs:
            if cert['name'] != CERT_NAME:
                continue
        result = c.call("certificate.create", dict(
            create_type="CERTIFICATE_CREATE_IMPORTED",
            name=CERT_NAME,
            certificate=module.params['certificate'],
            privatekey=module.params['private_key'],
        ))
        custom_results['create_result'] = result
        if result == False:
            module.fail_json(msg="Failed to create certificate", **custom_results)
            return
        module.exit_json(changed=True, msg="Certificate created successfully", **custom_results)


if __name__ == '__main__':
    main()
