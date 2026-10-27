*** Settings ***
Resource    launcher.resource
Library    SSHLibrary
Resource    api.resource

*** Test Cases ***
Check if launcher is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the user domain is removed correctly
    Run task    remove-internal-domain    {"domain":"${USER_DOMAIN}"}
