*** Settings ***
Library    SSHLibrary
Resource    api.resource
Resource    launcher.resource

*** Variables ***
${CLUSTER_USER}        admin
${CLUSTER_PASSWORD}    Nethesis,1234

*** Test Cases ***
Take screenshots of the module pages
    [Documentation]    Capture what cluster-admin shows for the launcher. Tagged ui:
    ...                the shared runner skips it unless RUN_UI_TESTS is true.
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True    viewport={'width': 1280, 'height': 900}
    Login to cluster-admin
    Screenshot page    ${EMPTY}            Status        1
    Screenshot page    ?page=settings      Settings      2
    Screenshot page    ?page=apps          Apps          3
    Screenshot page    ?page=appearance    Appearance    4
    Screenshot page    ?page=support       Support and links    5
    Close Browser

Take screenshots of the launcher page
    [Documentation]    The test host name resolves nowhere: Chromium maps it to the node.
    [Tags]    ui
    Run task    module/${module_id}/set-settings
    ...    {"welcome":"","support":{"url":"https://support.example.org","email":"support@example.org","phone":""},"categories":[],"apps":{},"links":[{"name":"NethServer documentation","url":"https://docs.nethserver.org","category":""}]}
    Import Library    Browser
    New Browser    chromium    headless=True    args=["--host-resolver-rules=MAP ${TEST_HOST} ${NODE_ADDR}"]
    New Context    ignoreHTTPSErrors=True    viewport={'width': 1280, 'height': 900}    locale=en-US
    New Page    https://${TEST_HOST}/
    Wait For Elements State    css=#apps-view    visible    timeout=20s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/6._Launcher_public.png
    Run task    module/${module_id}/configure-module
    ...    {"host":"${TEST_HOST}","lets_encrypt":false,"auth_mode":"ldap","ldap_domain":"${USER_DOMAIN}"}
    # The jar still holds the session of the LDAP suite, which would answer 200
    Execute Command    rm -f /tmp/launcher.cookies
    Wait Until Keyword Succeeds    20 times    3 seconds
    ...    Launcher answers    /api/apps    401
    Reload
    Wait For Elements State    css=#login-view    visible    timeout=20s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/7._Launcher_login.png
    Fill Text    id=username    alice
    Fill Text    id=password    Nethesis,1234
    Click    css=#login-form button[type=submit]
    Wait For Elements State    css=#apps-view    visible    timeout=20s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/8._Launcher_logged_in.png
    Close Browser

*** Keywords ***
Login to cluster-admin
    New Page    https://${NODE_ADDR}/cluster-admin/
    Fill Text    text="Username"    ${CLUSTER_USER}
    Click    button >> text="Continue"
    Fill Text    text="Password"    ${CLUSTER_PASSWORD}
    Click    button >> text="Log in"
    Wait For Elements State    css=#main-content    visible    timeout=10s

Screenshot page
    [Arguments]    ${query}    ${title}    ${index}
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}${query}
    Wait For Elements State    iframe >>> h2 >> text="${title}"    visible    timeout=10s
    # The page fills itself from several tasks: let them land
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/${index}._${title}.png

Launcher answers
    [Arguments]    ${path}    ${expected}
    ${status} =    Curl launcher    ${path}
    Should Be Equal    ${status}    ${expected}
