*** Settings ***
Library    SSHLibrary

*** Variables ***
# Any resolvable-looking name: the schema demands a dot, nothing resolves it.
${TEST_HOST}      launcher.ns8-ci.test
${APP_HOST}       probe.ns8-ci.test
${USER_DOMAIN}    launcher.ns8-ci.test

*** Keywords ***
Curl launcher
    [Documentation]    Query the launcher through Traefik as a browser would,
    ...                and return the HTTP status code.
    [Arguments]    ${path}    ${options}=${EMPTY}
    ${status} =    Execute Command
    ...    curl -sk -o /dev/null -w '\%{http_code}' --resolve ${TEST_HOST}:443:127.0.0.1 -b /tmp/launcher.cookies -c /tmp/launcher.cookies ${options} https://${TEST_HOST}${path}
    RETURN    ${status}

Curl launcher body
    [Arguments]    ${path}
    ${body} =    Execute Command
    ...    curl -sk --resolve ${TEST_HOST}:443:127.0.0.1 -b /tmp/launcher.cookies https://${TEST_HOST}${path}
    RETURN    ${body}

Login to launcher
    [Arguments]    ${user}    ${password}
    ${status} =    Curl launcher    /api/login
    ...    -X POST -H 'Content-Type: application/json' --data '{"username":"${user}","password":"${password}"}'
    RETURN    ${status}
