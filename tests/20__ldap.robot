*** Settings ***
Library    SSHLibrary
Resource    api.resource
Resource    launcher.resource

*** Variables ***
${PORTAL_URL}    https://node.ns8-ci.test/users-admin/launcher.ns8-ci.test/

*** Test Cases ***
Check if the user domain is installed
    ${response} =    Run task    add-internal-provider    {"image":"openldap","node":1}
    Set Global Variable    ${ldap_id}    ${response['module_id']}
    Run task    module/${ldap_id}/configure-module
    ...    {"domain":"${USER_DOMAIN}","admuser":"admin","admpass":"Nethesis,1234","provision":"new-domain"}
    Run task    module/${ldap_id}/add-user
    ...    {"user":"alice","display_name":"Alice","password":"Nethesis,1234"}
    Run task    module/${ldap_id}/add-group    {"group":"staff","description":"","users":["alice"]}

Check if launcher can be configured in LDAP mode
    Run task    module/${module_id}/configure-module
    ...    {"host":"${TEST_HOST}","lets_encrypt":false,"auth_mode":"ldap","ldap_domain":"${USER_DOMAIN}"}
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    Launcher answers    /api/apps    401

Check if the groups of the domain are listed
    ${output} =    Run task    module/${module_id}/list-groups    {}
    ${groups} =    Evaluate    [g['group'] for g in $output['groups']]
    Should Contain    ${groups}    staff

Check if a wrong password is refused
    ${status} =    Login to launcher    alice    wrong-password
    Should Be Equal    ${status}    401
    ${output} =    Execute Command    journalctl --since -5min -t launcher --no-pager | grep -c "login failed user='alice'"
    Should Be True    ${output} >= 1

Check if a valid user can log in
    ${status} =    Login to launcher    alice    Nethesis,1234
    Should Be Equal    ${status}    200
    ${status} =    Curl launcher    /api/apps
    Should Be Equal    ${status}    200

Check if repeated failures are blocked
    FOR    ${i}    IN RANGE    10
        Login to launcher    alice    wrong-password
    END
    ${status} =    Login to launcher    alice    Nethesis,1234
    Should Be Equal    ${status}    429

Check if the password portal link is published
    Run task    module/${module_id}/configure-module
    ...    {"host":"${TEST_HOST}","lets_encrypt":false,"auth_mode":"ldap","ldap_domain":"${USER_DOMAIN}","password_portal_url":"${PORTAL_URL}"}
    ${config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Equal    ${config}[password_portal_url]    ${PORTAL_URL}
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    Launcher answers    /api/apps    401
    ${body} =    Curl launcher body    /api/config
    Should Contain    ${body}    ${PORTAL_URL}

Check if the password portal link is kept on reconfigure
    Run task    module/${module_id}/configure-module
    ...    {"host":"${TEST_HOST}","lets_encrypt":false,"auth_mode":"ldap","ldap_domain":"${USER_DOMAIN}"}
    ${config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Equal    ${config}[password_portal_url]    ${PORTAL_URL}

Check if launcher goes back to public mode
    # Restart the container: it also clears the in-memory failure counters
    Run task    module/${module_id}/configure-module
    ...    {"host":"${TEST_HOST}","lets_encrypt":false,"auth_mode":"public","ldap_domain":""}
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    Launcher answers    /api/apps    200
    ${config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Empty    ${config}[password_portal_url]

*** Keywords ***
Launcher answers
    [Arguments]    ${path}    ${expected}
    ${status} =    Curl launcher    ${path}
    Should Be Equal    ${status}    ${expected}
