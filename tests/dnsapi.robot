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

Call API
    [Arguments]    ${method}    ${path}    ${key}=${EMPTY}    ${body}=${EMPTY}
    ${auth} =    Set Variable If    '${key}' != ''    -H 'Authorization: Bearer ${key}'    ${EMPTY}
    ${data} =    Set Variable If    '''${body}''' != ''    -H 'Content-Type: application/json' --data '${body}'    ${EMPTY}
    ${out} =    Execute Command    curl -sk -X ${method} ${auth} ${data} -w '\\n\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}${path}
    ${status} =    Evaluate    int($out.rsplit('\\n', 1)[1])
    ${text} =    Evaluate    $out.rsplit('\\n', 1)[0].strip()
    ${json} =    Evaluate    json.loads($text) if $text else None    modules=json
    RETURN    ${status}    ${json}

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

Check that the API refuses requests without a valid key
    ${status}    ${body} =    Call API    GET    /v1/nothing
    Should Be Equal As Integers    ${status}    401
    Should Be Equal    ${body}[error][code]    missing_key
    ${status}    ${body} =    Call API    GET    /v1/tenants    dnsapi_00000000_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    Should Be Equal As Integers    ${status}    401
    Should Be Equal    ${body}[error][code]    invalid_key

Check that an operator key can be made from the shell
    ${key}    ${rc} =    Execute Command    runagent -m ${module_id} create-key --owner operator --scope write --label ci
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    Should Match Regexp    ${key}    ^dnsapi_[0-9a-f]{8}_[a-z2-7]{52}$
    Set Suite Variable    ${OPERATOR_KEY}    ${key}
    ${status}    ${body} =    Call API    GET    /v1/nothing    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    404
    Should Be Equal    ${body}[error][code]    not_found

Check that the operator adds a tenant through the API
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    200
    Should Be Empty    ${body}[tenants]
    ${status}    ${body} =    Call API    POST    /v1/tenants    ${OPERATOR_KEY}    {"name": "CI tenant"}
    Should Be Equal As Integers    ${status}    201
    Should Match Regexp    ${body}[id]    ^t[0-9a-f]{8}$
    Set Suite Variable    ${TENANT_ID}    ${body}[id]
    ${output} =    Execute Command    api-cli run module/${module_id}/list-tenants
    ${listed} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${listed}[tenants][0][name]    CI tenant

Check that the operator makes a tenant key through the API
    ${status}    ${body} =    Call API    POST    /v1/tenants/${TENANT_ID}/keys    ${OPERATOR_KEY}    {"scope": "read", "label": "ci tenant"}
    Should Be Equal As Integers    ${status}    201
    Set Suite Variable    ${TENANT_KEY}    ${body}[key]
    Set Suite Variable    ${TENANT_KEY_ID}    ${body}[id]
    ${output} =    Execute Command    api-cli run module/${module_id}/list-keys
    Should Not Contain    ${output}    hash
    Should Not Contain    ${output}    ${TENANT_KEY}
    Should Contain    ${output}    ${TENANT_KEY_ID}

Check that a tenant key cannot reach the operator endpoints
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    404

Check that the zones endpoint reports dnshelper missing
    ${status}    ${body} =    Call API    GET    /v1/zones    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    503
    Should Be Equal    ${body}[error][code]    dnshelper_missing

Check that a read key cannot change records
    ${status}    ${body} =    Call API    POST    /v1/zones/example.test/records    ${TENANT_KEY}    {"records": [{"name": "www", "type": "A", "data": "192.0.2.1"}]}
    Should Be Equal As Integers    ${status}    403
    Should Be Equal    ${body}[error][code]    insufficient_scope

Check that a change reports dnshelper missing
    ${status}    ${body} =    Call API    POST    /v1/zones/example.test/changes    ${OPERATOR_KEY}    {"add": [{"name": "www", "type": "A", "data": "192.0.2.1"}], "dry_run": true}
    Should Be Equal As Integers    ${status}    503
    Should Be Equal    ${body}[error][code]    dnshelper_missing

Check that a revoked key stops working
    ${status}    ${body} =    Call API    DELETE    /v1/tenants/${TENANT_ID}/keys/${TENANT_KEY_ID}    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    204
    ${status}    ${body} =    Call API    GET    /v1/zones    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    401

Check that removing the tenant through the API works
    ${status}    ${body} =    Call API    DELETE    /v1/tenants/${TENANT_ID}    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    204
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${OPERATOR_KEY}
    Should Be Empty    ${body}[tenants]

Check if dnsapi is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
