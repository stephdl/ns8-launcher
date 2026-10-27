*** Settings ***
Library    SSHLibrary
Resource    api.resource
Resource    launcher.resource

*** Test Cases ***
Check if launcher is installed correctly
    ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Check if launcher can be configured in public mode
    Run task    module/${module_id}/configure-module
    ...    {"host":"${TEST_HOST}","lets_encrypt":false,"auth_mode":"public","ldap_domain":""}
    ${config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Equal    ${config}[host]    ${TEST_HOST}
    Should Be Equal    ${config}[auth_mode]    public

Check if HTTP redirects to HTTPS
    ${status} =    Execute Command
    ...    curl -s -o /dev/null -w '\%{http_code}' -H 'Host: ${TEST_HOST}' http://127.0.0.1/
    Should Be Equal    ${status}    301

Check if the launcher page is served
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    Launcher answers    /    200
    ${status} =    Curl launcher    /api/apps
    Should Be Equal    ${status}    200
    ${status} =    Curl launcher    /not-a-page
    Should Be Equal    ${status}    404

Check if a new route shows up in the launcher
    Run task    module/traefik1/set-route
    ...    {"instance":"${module_id}-probe","url":"http://127.0.0.1:9","host":"${APP_HOST}","http2https":true,"lets_encrypt":false}
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    App is listed    ${APP_HOST}

Check if a deleted route leaves the launcher
    Run task    module/traefik1/delete-route    {"instance":"${module_id}-probe"}
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    App is not listed    ${APP_HOST}

Check if the refresh action works
    Run task    module/${module_id}/refresh-apps    {}
    ${settings} =    Run task    module/${module_id}/get-settings    {}
    Should Be True    ${settings}[updated] > 0

Check if requests are logged with their status
    ${output} =    Execute Command    journalctl --since -10min -t launcher --no-pager | grep -c '"GET /not-a-page" 404'
    Should Be True    ${output} >= 1

*** Keywords ***
Launcher answers
    [Arguments]    ${path}    ${expected}
    ${status} =    Curl launcher    ${path}
    Should Be Equal    ${status}    ${expected}

App is listed
    [Arguments]    ${host}
    ${body} =    Curl launcher body    /api/apps
    Should Contain    ${body}    "${host}"

App is not listed
    [Arguments]    ${host}
    ${body} =    Curl launcher body    /api/apps
    Should Not Contain    ${body}    "${host}"
