#! /usr/local/bin/python

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(argument_spec=dict())
    module.exit_json(changed=False, msg="Dummy module executed")

if __name__ == '__main__':
    main()
