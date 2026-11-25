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
    Should Be True    ${config}[revoke_cleartext_keys]
    Should Not Contain    ${config}    http2https

Check that the host record step reports dnshelper missing
    # No dnshelper on CI nodes: configure-module still succeeds and says why it did not publish.
    ${output} =    Execute Command    api-cli run module/${module_id}/get-configuration
    ${config} =    Evaluate    json.loads($output)    modules=json
    Should Be True    ${config}[publish_host_record]
    Should Be Equal    ${config}[host_record][status]    error
    Should Be Equal    ${config}[host_record][host]    ${API_HOST}

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

Check that plain HTTP reaches the API and is refused, not redirected
    # http2https was passed true above: it is ignored
    ${output} =    Execute Command    curl -s -o /dev/null -w '\%{http_code}' --resolve ${API_HOST}:80:127.0.0.1 http://${API_HOST}/v1/status
    Should Be Equal    ${output}    200
    ${output} =    Execute Command    curl -s -w '\n\%{http_code}' --resolve ${API_HOST}:80:127.0.0.1 http://${API_HOST}/v1/zones
    Should End With    ${output}    403
    Should Contain    ${output}    https_required

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

Check that the Status and Activity actions report the changes
    ${output} =    Execute Command    api-cli run module/${module_id}/get-overview
    ${overview} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal As Integers    ${overview}[tenants]    1
    Should Be Equal As Integers    ${overview}[keys_operator]    1
    Should Be Equal As Integers    ${overview}[keys_tenant]    1
    Should Be Equal    ${overview}[dnshelper_error]    dnshelper_missing
    Should Be Equal    ${overview}[url]    https://${API_HOST}/v1/
    ${output} =    Execute Command    api-cli run module/${module_id}/list-activity
    ${activity} =    Evaluate    [e['action'] for e in json.loads($output)['entries']]    modules=json
    Should Contain    ${activity}    add-tenant
    Should Contain    ${activity}    create-key
    Should Not Contain    ${output}    ${TENANT_KEY}

Take screenshots of the pages
    # After a tenant and two keys exist, so the pages show rows.
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True    viewport={'width': 1440, 'height': 1000}
    Login to cluster-admin
    FOR    ${index}    ${page}    ${title}    IN
    ...    1    status    Status
    ...    2    tenants    Tenants
    ...    3    keys    Keys
    ...    4    activity    Activity
    ...    5    settings    Settings
        Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=${page}
        Wait For Elements State    iframe >>> h2 >> text="${title}"    visible    timeout=20s
        Sleep    5s
        Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/${index}._${title}.png
    END
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=keys
    Wait For Elements State    iframe >>> h2 >> text="Keys"    visible    timeout=20s
    # the dialog's own primary button says "Create key" too
    Click    iframe >>> button >> text="Create key" >> nth=0
    Wait For Elements State    iframe >>> text="Create a key"    visible    timeout=10s
    Sleep    2s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/6._Create_key.png
    Close Browser

Check that a tenant key cannot reach the operator endpoints
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    404

Check that the zones endpoint reports dnshelper missing
    ${status}    ${body} =    Call API    GET    /v1/zones    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    503
    Should Be Equal    ${body}[error][code]    dnshelper_missing

Check that the providers endpoint is for operator keys
    ${status}    ${body} =    Call API    GET    /v1/providers    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    404
    ${status}    ${body} =    Call API    GET    /v1/providers    ${OPERATOR_KEY}
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

Check that a key restricted to ACME records cannot manage tenants
    ${key}    ${rc} =    Execute Command    runagent -m ${module_id} create-key --owner operator --scope write --restrict acme --label ci-acme
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    Set Suite Variable    ${ACME_KEY}    ${key}
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${ACME_KEY}
    Should Be Equal As Integers    ${status}    403
    Should Be Equal    ${body}[error][code]    restricted_key
    ${output} =    Execute Command    api-cli run module/${module_id}/list-keys --data '{"owner": "operator"}'
    Should Contain    ${output}    _acme-challenge

Check that the ACME endpoints take Basic authentication
    ${output} =    Execute Command    curl -sk -u 'any:${ACME_KEY}' -H 'Content-Type: application/json' --data '{"fqdn": "_acme-challenge.www.example.test.", "value": "x"}' -w '\\n\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/acme/present
    Should End With    ${output}    503
    Should Contain    ${output}    dnshelper_missing
    ${output} =    Execute Command    curl -sk -u 'any:${ACME_KEY}' -o /dev/null -w '\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/zones
    Should Be Equal    ${output}    401

Check that a key sent over plain HTTP is revoked
    # a key-shaped string with a real key id is not enough
    ${fake} =    Evaluate    $OPERATOR_KEY[:16] + 'a' * 52
    ${output} =    Execute Command    curl -s -o /dev/null -w '\%{http_code}' -H 'Authorization: Bearer ${fake}' --resolve ${API_HOST}:80:127.0.0.1 http://${API_HOST}/v1/tenants
    Should Be Equal    ${output}    403
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    200
    # an operator key sent with Basic to an ACME endpoint, as lego and acme.sh do
    ${output} =    Execute Command    curl -s -u 'any:${ACME_KEY}' -H 'Content-Type: application/json' --data '{"fqdn": "_acme-challenge.www.example.test.", "value": "x"}' -w '\n\%{http_code}' --resolve ${API_HOST}:80:127.0.0.1 http://${API_HOST}/v1/acme/present
    Should End With    ${output}    403
    Should Contain    ${output}    https_required
    ${output} =    Execute Command    curl -sk -u 'any:${ACME_KEY}' -H 'Content-Type: application/json' --data '{"fqdn": "_acme-challenge.www.example.test.", "value": "x"}' -o /dev/null -w '\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/acme/present
    Should Be Equal    ${output}    401
    ${output} =    Execute Command    api-cli run module/${module_id}/get-overview
    ${overview} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal As Integers    ${overview}[keys_operator]    1
    Length Should Be    ${overview}[exposed_keys]    1
    Should Be Equal    ${overview}[exposed_keys][0][owner]    operator
    ${output} =    Execute Command    api-cli run module/${module_id}/list-activity
    Should Contain    ${output}    revoke-exposed-key

Check that a key's allowed addresses and label can be changed
    ${status}    ${body} =    Call API    PATCH    /v1/tenants/${TENANT_ID}/keys/${TENANT_KEY_ID}    ${OPERATOR_KEY}    {"allowlist": ["192.0.2.0/24"], "label": "ci tenant, fenced"}
    Should Be Equal As Integers    ${status}    200
    Should Be Equal    ${body}[label]    ci tenant, fenced
    Should Not Be Equal    ${body}[modified]    ${None}
    ${status}    ${body} =    Call API    GET    /v1/zones    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    403
    Should Be Equal    ${body}[error][code]    address_not_allowed
    ${status}    ${body} =    Call API    PATCH    /v1/tenants/${TENANT_ID}/keys/${TENANT_KEY_ID}    ${OPERATOR_KEY}    {"allowlist": []}
    Should Be Equal As Integers    ${status}    200
    ${status}    ${body} =    Call API    GET    /v1/zones    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    503
    # what a key can reach is fixed
    ${status}    ${body} =    Call API    PATCH    /v1/tenants/${TENANT_ID}/keys/${TENANT_KEY_ID}    ${OPERATOR_KEY}    {"scope": "write"}
    Should Be Equal As Integers    ${status}    400
    Should Be Equal    ${body}[error][code]    not_editable
    ${output} =    Execute Command    api-cli run module/${module_id}/list-activity
    Should Contain    ${output}    update-key
    # an operator key, by the administrator
    ${id} =    Evaluate    $OPERATOR_KEY.split('_')[1]
    ${output}    ${rc} =    Execute Command    api-cli run module/${module_id}/update-key --data '{"id": "${id}", "label": "ci operator"}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    ${key} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${key}[label]    ci operator
    Should Be Equal    ${key}[scope]    write

Check that a revoked key stops working
    ${status}    ${body} =    Call API    DELETE    /v1/tenants/${TENANT_ID}/keys/${TENANT_KEY_ID}    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    204
    ${status}    ${body} =    Call API    GET    /v1/zones    ${TENANT_KEY}
    Should Be Equal As Integers    ${status}    401
    Should Be Equal    ${body}[error][code]    key_revoked
    # kept as a record: listed on request, and by list-keys with its status
    ${status}    ${body} =    Call API    GET    /v1/tenants/${TENANT_ID}/keys    ${OPERATOR_KEY}
    ${ids} =    Evaluate    [k['id'] for k in $body['keys']]
    Should Not Contain    ${ids}    ${TENANT_KEY_ID}
    ${status}    ${body} =    Call API    GET    /v1/tenants/${TENANT_ID}/keys?revoked=true    ${OPERATOR_KEY}
    # ${} substitution, not $var: a comprehension cannot see Robot's variables
    ${found} =    Evaluate    [k for k in $body['keys'] if k['id'] == '${TENANT_KEY_ID}']
    Should Be Equal    ${found}[0][status]    revoked
    ${status}    ${body} =    Call API    DELETE    /v1/tenants/${TENANT_ID}/keys/${TENANT_KEY_ID}    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    404
    ${output} =    Execute Command    api-cli run module/${module_id}/list-keys --data '{"owner": "operator"}'
    ${keys} =    Evaluate    json.loads($output)['keys']    modules=json
    ${exposed} =    Evaluate    [k for k in $keys if k['revoked_reason'] == 'plain_http']
    Length Should Be    ${exposed}    1
    Should Be Equal    ${exposed}[0][status]    revoked

Check that removing the tenant through the API works
    ${status}    ${body} =    Call API    DELETE    /v1/tenants/${TENANT_ID}    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    204
    ${status}    ${body} =    Call API    GET    /v1/tenants    ${OPERATOR_KEY}
    Should Be Empty    ${body}[tenants]

Check if dnsapi is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
