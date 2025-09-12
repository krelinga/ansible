#! /usr/local/bin/python

import time

from ansible.module_utils.basic import AnsibleModule
from truenas_api_client import Client, ClientException

CERT_NAME = "certbot"

def get_certificates(w, note):
    """
    Get the list of certificates from the TrueNAS server.
    """
    certs = w.client.call("certificate.query", [], dict(
        prefix=CERT_NAME,
    ))
    w.note(note, certs)
    return certs


def find_certificate(certs):
    """
    Find the certificate with the name CERT_NAME.
    """
    for cert in certs:
        if cert['name'] == CERT_NAME:
            return cert
    return None


class Wrapper(object):
    def __init__(self, client, verbose):
        self._changed = False
        self._client = client
        self._notes = {}
        self._verbose = verbose

    @property
    def changed(self):
        return self._changed
    
    @property
    def client(self):
        return self._client
    
    @property
    def notes(self):
        return self._notes
    
    def change(self):
        self._changed = True

    def note(self, key, value):
        if not self._verbose:
            return
        assert key not in self._notes, "Key already exists in notes"
        self._notes[key] = value


class Error(Exception):
    """Base class for other exceptions"""
    def __init__(self, message):
        super().__init__(message)


def login(w, api_key):
    """
    Login to the TrueNAS server using the API key.
    """
    result = w.client.call("auth.login_with_api_key", api_key)
    w.note("login", result)
    if result != True:
        raise Error("Failed to authenticate with API key")


def ensure_cert_exists(w, certificate, private_key):
    """
    Ensure that the certificate exists on the TrueNAS server.
    """
    certs = get_certificates(w, "existing_certificates")
    existing = find_certificate(certs)
    if existing:
        existing_id = existing['id']
        if check_certificate(existing, certificate, private_key):
            # Certificate already exists with the same content
            return existing_id
        else:
            delete_certificate(w, existing_id)

    return create_certificate(w, certificate, private_key)


def check_certificate(existing, certificate, private_key):
    return existing['certificate'] == certificate and existing['privatekey'] == private_key


def delete_certificate(w, cert_id):
    """
    Delete the certificate from the TrueNAS server.
    """
    w.change()
    result = w.client.call("certificate.delete", dict(
        id=cert_id,
    ))
    w.note("delete_certificate", result)
    if result != True:
        raise Error("Failed to delete certificate")
    

def create_certificate(w, certificate, private_key):
    """
    Create a new certificate on the TrueNAS server.
    """
    w.change()
    result = w.client.call("certificate.create", dict(
        create_type="CERTIFICATE_CREATE_IMPORTED",
        name=CERT_NAME,
        certificate=certificate,
        privatekey=private_key,
    ))
    w.note("create_certificate", result)

    time.sleep(5)  # Wait for the certificate to be created

    # Check if the certificate was created successfully
    new_certs = get_certificates(w, "new_certificates")
    new_cert = find_certificate(new_certs)
    if new_cert is None:
        raise Error("Failed to create certificate")
    return new_cert['id']


def ensure_cert_in_use(w, cert_id):
    """
    Ensure that the certificate is in use on the TrueNAS server.
    """
    config = get_config(w, "current_config")
    if config['ui_certificate']['id'] == cert_id:
        return

    w.change()
    result = w.client.call("system.general.update", dict(
        ui_certificate=cert_id,
    ))
    w.note("update_ui_certificate", result)

    time.sleep(5)  # Wait for the update to take effect

    new_config = get_config(w, "new_config")
    if new_config['ui_certificate']['id'] != cert_id:
        raise Error("Failed to update UI certificate")
    
    restart_result = w.client.call("system.general.ui_restart")
    w.note("restart_ui", restart_result)
    

def get_config(w, key):
    """
    Get the current configuration from the TrueNAS server.
    """
    config = w.client.call("system.general.config")
    w.note(key, config)
    return config


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True),
            certificate=dict(type='str', required=True),
            private_key=dict(type='str', required=True),
            verbose=dict(type='bool', default=False),
            host=dict(type='str', required=True),
        )
    )

    certificate = module.params['certificate']
    private_key = module.params['private_key']
    api_key = module.params['api_key']
    verbose = module.params['verbose']

    w = None
    try:
        # https://forums.truenas.com/t/getting-error-trying-to-connect-via-truenas-api-client-to-websockets-api-endpoint-api-current/28152
        with Client("wss://truenas.i.krel.ing/websocket", verify_ssl=False) as c:
            w = Wrapper(c, verbose)
            login(w, api_key)
            cert_id = ensure_cert_exists(w, certificate, private_key)
            ensure_cert_in_use(w, cert_id)
            module.exit_json(changed=w.changed, **w.notes)
    except (Error, ClientException) as e:
        notes = w.notes if w else {}
        module.fail_json(msg="Failed to add certificate: %s" % str(e), **notes)
        return


if __name__ == '__main__':
    main()
