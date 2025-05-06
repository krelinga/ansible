#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule

import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup


CERT_NAME = "certbot"


class Error(Exception):
    """Base class for other exceptions"""
    def __init__(self, message):
        super().__init__(message)


class Context(object):
    def __init__(self, urifmt, params):
        self._urifmt = urifmt
        self._params = params
        self._changed = False
        self._notes = {}

    @property
    def urifmt(self):
        return self._urifmt
    
    @property
    def params(self):
        return self._params
    
    @property
    def changed(self):
        return self._changed
    
    @property
    def notes(self):
        return self._notes
    
    def change(self):
        self._changed = True

    def note(self, key, value):
        if key in self._notes:
            raise Error(f"Key '{key}' already exists in notes")
        self._notes[key] = value


def get_certificates(ctx):
    """
    Get the list of certificates from the OPNsense server.
    """
    uri = ctx.urifmt("api/trust/cert/search")
    try:
        response = requests.get(uri, **ctx.params)
        response.raise_for_status()
        return response.json().get('rows', [])
    except requests.exceptions.RequestException as e:
        raise Error(f"Failed to fetch certificates: {str(e)}")
    

def find_certificate(certs, cert_name):
    """
    Find the certificate with the specified name.
    """
    found = None
    for cert in certs:
        if cert['descr'] == cert_name:
            if found is not None:
                raise Error(f"Multiple certificates found with name '{cert_name}'")
            found = cert
    return found
    

def get_certificate_body(ctx, cert_uuid):
    """
    Get the certificate body from the OPNsense server.
    """
    uri = ctx.urifmt(f"api/trust/cert/get/{cert_uuid}")
    try:
        response = requests.get(uri, **ctx.params)
        response.raise_for_status()
        return response.json().get('cert', None)
    except requests.exceptions.RequestException as e:
        raise Error(f"Failed to fetch certificate body: {str(e)}")
    

def get_certificate_refid(ctx, cert_uuid):
    """
    Get the certificate refid from the OPNsense server.
    """
    body = get_certificate_body(ctx, cert_uuid)
    if "refid" not in body:
        raise Error(f"Certificate with UUID '{cert_uuid}' does not have a refid")
    return body["refid"]
    

def push_new_certificate(ctx, certificate, private_key):
    """
    Push a new certificate to the OPNsense server.
    """
    uri = ctx.urifmt("api/trust/cert/add")
    data = dict(
        cert=dict(
            action='import',
            cert_type='usr_cert',
            descr=CERT_NAME,
            crt_payload=certificate,
            prv_payload=private_key
        )
    )
    try:
        ctx.change()
        response = requests.post(uri, json=data, **ctx.params)
        response.raise_for_status()
        return response.json().get('uuid')
    except requests.exceptions.RequestException as e:
        raise Error(f"Failed to create certificate: {str(e)}")
    

class CertInfo(object):
    def __init__(self, old_uuid, new_refid):
        self.old_uuid = old_uuid
        self.new_refid = new_refid


def ensure_cert_exists(ctx, certificate, private_key):
    """
    Ensure that the specified certificate exists on the OPNsense server.
    If it does not exist, upload it.
    """
    certs = get_certificates(ctx)
    cert = find_certificate(certs, CERT_NAME)

    if cert is not None:
        # Certificate already exists, check if it matches
        cert_uuid = cert['uuid']
        existing_cert_body = get_certificate_body(ctx, cert_uuid)
        
        if existing_cert_body["crt_payload"] == certificate and existing_cert_body["prv_payload"] == private_key:
            # Certificate matches, no need to update
            return CertInfo(old_uuid=None, new_refid=get_certificate_refid(ctx, cert_uuid))

        # Certificate does not match, we need to update it
        new_cert_uuid = push_new_certificate(ctx, certificate, private_key)
        return CertInfo(old_uuid=cert_uuid, new_refid=get_certificate_refid(ctx, new_cert_uuid))
    
    # Certificate does not exist, we need to create it
    new_cert_uuid = push_new_certificate(ctx, certificate, private_key)
    return CertInfo(old_uuid=None, new_refid=get_certificate_refid(ctx, new_cert_uuid))


def ensure_cert_in_use(ctx, web_user_name, web_password, cert_refid):
    """
    Ensure that the specified certificate is in use on the OPNsense server.
    This function assumes that the certificate is already uploaded.
    """
    s = requests.Session()
    uri = ctx.urifmt("system_advanced_admin.php")
    try:
        login_page = s.get(uri, **ctx.params)
        login_page.raise_for_status()
        login_soup = BeautifulSoup(login_page.text, "html.parser")
        login_form = login_soup.find("form")
        login_action = login_form.get("action")
        login_inputs = {tag['name']: tag.get('value', '') for tag in login_form.find_all("input")}
        login_inputs.update(dict(
            usernamefld=web_user_name,
            passwordfld=web_password,
            login="1"  # This comes from the submit button.
        ))
        login_url = requests.compat.urljoin(login_page.url, login_action)
        admin_page = s.post(login_url, data=login_inputs, **ctx.params)
        admin_page.raise_for_status()

        admin_soup = BeautifulSoup(admin_page.text, "html.parser")
        admin_form = admin_soup.find("form", {"id": "iform"})
        if admin_form.find("select", dict(name="ssl-certref")).find("option", dict(selected="selected"))['value'] == cert_refid:
            # Certificate is already in use, no need to update
            return
        ctx.change()
        admin_action = admin_form.get("action")
        relevant_names = [
            "webguiproto",  # Needed because of a weirdness in how OPNsense handles this form.
            "ssl-certref",
        ]
        relevant_inputs = lambda tag: tag.get("type") in ["hidden", "submit"] or tag.get("name") in relevant_names
        admin_inputs = {tag['name']: tag.get('value', '') for tag in admin_form.find_all(relevant_inputs)}
        admin_inputs.update({
            "ssl-certref": cert_refid
        })
        ctx.note("admin_inputs", admin_inputs)
        admin_url = requests.compat.urljoin(admin_page.url, admin_action)
        update_response = s.post(admin_url, data=admin_inputs, **ctx.params)
        update_response.raise_for_status()
        if "The changes have been applied successfully." not in update_response.text:
            raise Error("Failed to update the certificate in use on the OPNsense server")

    except requests.exceptions.RequestException as e:
        raise Error(f"Failed to fetch system advanced admin page: {str(e)}")
    

def delete_certificate(ctx, cert_uuid):
    """
    Delete the specified certificate from the OPNsense server.
    """
    uri = ctx.urifmt(f"api/trust/cert/del/{cert_uuid}")
    try:
        ctx.change()
        response = requests.post(uri, **ctx.params)
        response.raise_for_status()
        return response.json().get('success', False)
    except requests.exceptions.RequestException as e:
        raise Error(f"Failed to delete certificate: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True, no_log=True),
            api_secret=dict(type='str', required=True, no_log=True),
            certificate=dict(type='str', required=True),
            private_key=dict(type='str', required=True),
            host=dict(type='str', required=True),
            web_user_name=dict(type='str', required=True),
            web_password=dict(type='str', required=True, no_log=True)
        )
    )

    certificate = module.params['certificate']
    private_key = module.params['private_key']
    api_key = module.params['api_key']
    api_secret = module.params['api_secret']
    host = module.params['host']
    web_user_name = module.params['web_user_name']
    web_password = module.params['web_password']

    params = dict(
        auth=HTTPBasicAuth(api_key, api_secret),
        verify=False,  # Disable SSL verification for testing; consider enabling in production
    )

    urifmt = lambda endpoint: f"https://{host}/{endpoint}"

    ctx = Context(urifmt, params)

    try:
        info = ensure_cert_exists(ctx, certificate, private_key)
        ensure_cert_in_use(ctx, web_user_name, web_password, info.new_refid)
        if info.old_uuid is not None:
            delete_certificate(ctx, info.old_uuid)
        module.exit_json(changed=ctx.changed, **ctx.notes)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=f"HTTP GET request encountered an error: {str(e)}")


if __name__ == '__main__':
    main()
