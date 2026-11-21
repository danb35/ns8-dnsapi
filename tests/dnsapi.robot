*** Settings ***
Library    SSHLibrary

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
${API_HOST}    dnsapi.ci.test

*** Keywords ***
Login to cluster-admin
    New Page    https://${NODE_ADDR}/cluster-admin/
    Fill Text    text="Username"    ${ADMIN_USER}
    Click    button >> text="Continue"
    Fill Text    text="Password"    ${ADMIN_PASSWORD}
    Click    button >> text="Log in"
    Wait For Elements State    css=#main-content    visible    timeout=10s

*** Test Cases ***
Check if dnsapi is installed correctly
    ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Take screenshots
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True
    Login to cluster-admin
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}
    Wait For Elements State    iframe >>> h2 >> text="Status"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/1._Status.png
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=settings
    Wait For Elements State    iframe >>> h2 >> text="Settings"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/2._Settings.png
    Close Browser

Check if dnsapi can be configured
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"host": "${API_HOST}", "lets_encrypt": false, "http2https": true}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check that get-configuration returns the settings
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/get-configuration
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    ${config} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${config}[host]    ${API_HOST}
    Should Be True    ${config}[http2https]

Check that a bad allowlist address is refused
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"ip_allowlist": ["not-an-address"]}'
    ...    return_rc=True  return_stdout=False
    Should Not Be Equal As Integers    ${rc}  0

Check that the status endpoint answers through Traefik
    ${output}  ${rc} =    Execute Command    curl -fsk --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/status
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    ${status} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${status}[status]    ok

Check that plain HTTP is redirected to HTTPS
    ${output} =    Execute Command    curl -s -o /dev/null -w '\%{http_code} \%{redirect_url}' --resolve ${API_HOST}:80:127.0.0.1 http://${API_HOST}/v1/status
    Should Match Regexp    ${output}    ^30[178] https://${API_HOST}/v1/status$

Check that an unknown endpoint gets a JSON 404
    ${output} =    Execute Command    curl -sk -o /dev/null -w '\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/nothing
    Should Be Equal    ${output}    404
    ${body} =    Execute Command    curl -sk --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/nothing
    ${error} =    Evaluate    json.loads($body)    modules=json
    Should Be Equal    ${error}[error][code]    not_found

Check if dnsapi is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
