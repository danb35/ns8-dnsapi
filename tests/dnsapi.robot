*** Settings ***
Library    SSHLibrary

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
# In a zone dnshelper manages once it is installed, so the host record is published.
${API_HOST}    api.hosting.example.test
# Never a real service or credential: dnshelper talks only to a throwaway
# PowerDNS on the node's loopback, as in dnshelper's own suite.
${DNSHELPER_IMAGE}    ghcr.io/danb35/dnshelper:0.7.1
${PDNS_IMAGE}    docker.io/powerdns/pdns-auth-49:4.9.17
${PDNS_API}    http://127.0.0.1:18081
${PDNS_KEY}    ci-not-a-real-key
${ZONE_A}    hosting.example.test
${ZONE_B}    other.example.test
${ZONE_ACME}    internal.example.test
${ZONE_DENIED}    denied.example.test
${dnshelper_id}    ${EMPTY}

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
    ${out} =    Execute Command    curl -sk -X ${method} ${auth} ${data} -w '\\n\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 'https://${API_HOST}${path}'
    ${status} =    Evaluate    int($out.rsplit('\\n', 1)[1])
    ${text} =    Evaluate    $out.rsplit('\\n', 1)[0].strip()
    ${json} =    Evaluate    json.loads($text) if $text else None    modules=json
    RETURN    ${status}    ${json}

Expect API
    [Documentation]    Call the API and check the status (and the error code, when given).
    [Arguments]    ${expected}    ${method}    ${path}    ${key}    ${body}=${EMPTY}    ${code}=${EMPTY}
    ${status}    ${json} =    Call API    ${method}    ${path}    ${key}    ${body}
    Should Be Equal As Integers    ${status}    ${expected}    ${method} ${path}: ${json}
    IF    '${code}' != ''
        Should Be Equal    ${json}[error][code]    ${code}
    END
    RETURN    ${json}

Run action
    [Arguments]    ${module}    ${action}    ${data}={}
    ${output}  ${rc} =    Execute Command    api-cli run module/${module}/${action} --data '${data}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0    ${action} failed: ${output}
    ${parsed} =    Evaluate    json.loads(r'''${output}''' or '{}')    modules=json
    RETURN    ${parsed}

PowerDNS values
    [Documentation]    The values PowerDNS itself holds for a name (fully qualified, no final dot) and type.
    [Arguments]    ${zone}    ${name}    ${type}
    ${out} =    Execute Command    curl -fsS -H 'X-API-Key: ${PDNS_KEY}' ${PDNS_API}/api/v1/servers/localhost/zones/${zone}.
    # ${} substitution, not $var, inside the comprehension
    ${values} =    Evaluate    sorted(r['content'] for s in json.loads($out)['rrsets'] if s['name'] == '${name}.' and s['type'] == '${type}' for r in s['records'])    modules=json
    RETURN    ${values}

Names in
    [Arguments]    ${body}
    ${names} =    Evaluate    sorted(set(r['name'] + ' ' + r['type'] for r in $body['records']))
    RETURN    ${names}

Tenant has zones
    [Arguments]    ${tenant}    @{zones}
    ${body} =    Expect API    200    GET    /v1/tenants/${tenant}    ${OPERATOR_KEY}
    ${have} =    Evaluate    sorted($body['zones'])
    ${want} =    Evaluate    sorted($zones)
    Should Be Equal    ${have}    ${want}

dnsapi reports dnshelper missing
    ${output} =    Execute Command    api-cli run module/${module_id}/get-overview
    ${overview} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${overview}[dnshelper_error]    dnshelper_missing

dnsapi has found dnshelper
    ${status}    ${body} =    Call API    GET    /v1/providers    ${OPERATOR_KEY}
    Should Be Equal As Integers    ${status}    200    ${body}

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

# From here on, with dnshelper: installed now, after the cases above checked
# how dnsapi behaves without it, so the install also tests that dnsapi finds a
# dnshelper added later (module-added).

Start a PowerDNS server with the test zones
    # Runs as a non-root user and binds port 53 inside the container: podman needs the sysctl.
    ${rc} =    Execute Command
    ...    podman run -d --name dnsapi-ci-pdns --sysctl net.ipv4.ip_unprivileged_port_start=53 -p 127.0.0.1:18081:8081 -e PDNS_AUTH_API_KEY=${PDNS_KEY} ${PDNS_IMAGE}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    ${rc} =    Execute Command
    ...    for i in $(seq 90); do curl -fsS -o /dev/null -H 'X-API-Key: ${PDNS_KEY}' ${PDNS_API}/api/v1/servers/localhost \&\& exit 0; sleep 1; done; exit 1
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0    PowerDNS did not start
    FOR    ${zone}    IN    ${ZONE_A}    ${ZONE_B}    ${ZONE_ACME}    ${ZONE_DENIED}
        ${rc} =    Execute Command
        ...    curl -fsS -o /dev/null -H 'X-API-Key: ${PDNS_KEY}' -X POST -d '{"name":"${zone}.","kind":"Native","nameservers":["ns1.${zone}."],"soa_edit_api":"DEFAULT"}' ${PDNS_API}/api/v1/servers/localhost/zones
        ...    return_rc=True  return_stdout=False
        Should Be Equal As Integers    ${rc}  0
    END

Check if dnshelper is installed
    ${output}  ${rc} =    Execute Command    add-module ${DNSHELPER_IMAGE} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0    ${output}
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${dnshelper_id}    ${output.module_id}

Give dnshelper the zones and rules for dnsapi
    ${cred} =    Run action    ${dnshelper_id}    add-credential
    ...    {"name":"PowerDNS (CI)","provider":"powerdns","fields":{"api_url":"${PDNS_API}","api_key":"${PDNS_KEY}"}}
    FOR    ${zone}    IN    ${ZONE_A}    ${ZONE_B}    ${ZONE_ACME}    ${ZONE_DENIED}
        Run action    ${dnshelper_id}    add-zone    {"zone":"${zone}","credential":"${cred}[id]"}
    END
    # The "API module (all records)" preset on two zones, the ACME preset on one, nothing on the last.
    Run action    ${dnshelper_id}    set-policy
    ...    {"rules":[{"caller":"module/${module_id}","zones":["${ZONE_A}","${ZONE_B}"],"access":"write","names":["*"],"types":["*"]},{"caller":"module/${module_id}","zones":["${ZONE_ACME}"],"access":"write","names":["_acme-challenge","_acme-challenge.*"],"types":["TXT"]}]}

Check that dnsapi finds dnshelper
    Wait Until Keyword Succeeds    120s    3s    dnsapi has found dnshelper
    ${output} =    Execute Command    api-cli run module/${module_id}/get-overview
    ${overview} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${overview}[dnshelper]    ${dnshelper_id}
    Should Be Equal    ${overview}[dnshelper_error]    ${None}
    Should Be Equal As Integers    ${overview}[zones_writable]    3
    Should Be Equal As Integers    ${overview}[zones_full]    2

Check that the providers come from dnshelper
    ${body} =    Expect API    200    GET    /v1/providers    ${OPERATOR_KEY}
    ${names} =    Evaluate    [p['name'] for p in $body['providers']]
    Should Contain    ${names}    powerdns
    Should Contain    ${names}    cloudflare
    ${pdns} =    Evaluate    [p for p in $body['providers'] if p['name'] == 'powerdns'][0]
    ${secret} =    Evaluate    {f['name']: f['secret'] for f in $pdns['fields']}
    Should Be True    ${secret}[api_key]

Check that adding domains needs a dnshelper with delegates
    # dnshelper 0.7.1 (DNSHELPER_IMAGE) has no dnszoneadmin role: the api-server refuses
    # validate-zone, and the API says that dnshelper may need updating. The rest of the
    # suite shows that the dnswriter half of the grant still works there.
    Expect API    503    POST    /v1/zones    ${OPERATOR_KEY}
    ...    {"zone": "customer.example", "provider": "cloudflare", "credentials": {"api_token": "ci-not-a-real-token"}, "dry_run": true}
    ...    code=not_granted
    Expect API    503    POST    /v1/zones/provision    ${OPERATOR_KEY}
    ...    {"zone": "customer.example", "provider": "cloudflare", "credentials": {"api_token": "ci-not-a-real-token"}, "records": [{"name": "@", "type": "TXT", "data": "x"}], "dry_run": true}
    ...    code=not_granted
    Expect API    404    DELETE    /v1/zones/${ZONE_A}    ${OPERATOR_KEY}    code=zone_not_found

Check that the host record is published in the managed zone
    Run action    ${module_id}    configure-module    {"host": "${API_HOST}"}
    ${config} =    Run action    ${module_id}    get-configuration
    Should Be Equal    ${config}[host_record][status]    created    ${config}[host_record]
    Should Be Equal    ${config}[host_record][zone]    ${ZONE_A}
    ${fqdn} =    Execute Command    api-cli run node/1/get-fqdn
    ${target} =    Evaluate    '%(hostname)s.%(domain)s.' % json.loads($fqdn)    modules=json
    ${values} =    PowerDNS values    ${ZONE_A}    ${API_HOST}    CNAME
    Should Be Equal    ${values}    ${{ [$target] }}
    # once there, configure-module finds it and adds nothing
    Run action    ${module_id}    configure-module    {"host": "${API_HOST}"}
    ${config} =    Run action    ${module_id}    get-configuration
    Should Be Equal    ${config}[host_record][status]    ok

Check which zones dnsapi may assign
    ${body} =    Expect API    200    GET    /v1/zones    ${OPERATOR_KEY}
    ${zones} =    Evaluate    {z['zone']: z['full'] for z in $body['zones']}
    Should Be Equal    ${zones}    ${{ {$ZONE_A: True, $ZONE_B: True, $ZONE_ACME: False} }}

Check that tenants get their zones and no others
    ${body} =    Expect API    201    POST    /v1/tenants    ${OPERATOR_KEY}    {"name": "Hosting customer"}
    Set Suite Variable    ${TENANT_A}    ${body}[id]
    ${body} =    Expect API    201    POST    /v1/tenants    ${OPERATOR_KEY}    {"name": "Internal hosts"}
    Set Suite Variable    ${TENANT_B}    ${body}[id]
    Expect API    200    PUT    /v1/tenants/${TENANT_A}/zones/${ZONE_A}    ${OPERATOR_KEY}
    Expect API    200    PUT    /v1/tenants/${TENANT_B}/zones/${ZONE_B}    ${OPERATOR_KEY}
    Expect API    200    PUT    /v1/tenants/${TENANT_B}/zones/${ZONE_ACME}    ${OPERATOR_KEY}
    Expect API    409    PUT    /v1/tenants/${TENANT_B}/zones/${ZONE_A}    ${OPERATOR_KEY}    code=zone_assigned
    Expect API    409    PUT    /v1/tenants/${TENANT_A}/zones/${ZONE_DENIED}    ${OPERATOR_KEY}    code=zone_not_assignable

Make the tenants' keys
    ${body} =    Expect API    201    POST    /v1/tenants/${TENANT_A}/keys    ${OPERATOR_KEY}    {"scope": "write", "label": "ci A write"}
    Set Suite Variable    ${KEY_A}    ${body}[key]
    Set Suite Variable    ${KEY_A_ID}    ${body}[id]
    ${body} =    Expect API    201    POST    /v1/tenants/${TENANT_A}/keys    ${OPERATOR_KEY}    {"scope": "read", "label": "ci A read"}
    Set Suite Variable    ${KEY_A_READ}    ${body}[key]
    ${body} =    Expect API    201    POST    /v1/tenants/${TENANT_B}/keys    ${OPERATOR_KEY}    {"scope": "write", "label": "ci B write"}
    Set Suite Variable    ${KEY_B}    ${body}[key]
    ${body} =    Expect API    201    POST    /v1/tenants/${TENANT_B}/keys    ${OPERATOR_KEY}    {"scope": "write", "label": "ci B acme", "restrict": "acme"}
    Set Suite Variable    ${KEY_B_ACME}    ${body}[key]
    Set Suite Variable    ${KEY_B_ACME_ID}    ${body}[id]

Check that each tenant key lists only its own zones
    ${body} =    Expect API    200    GET    /v1/zones    ${KEY_A}
    ${zones} =    Evaluate    [z['zone'] for z in $body['zones']]
    Should Be Equal    ${zones}    ${{ [$ZONE_A] }}
    ${body} =    Expect API    200    GET    /v1/zones    ${KEY_B}
    ${zones} =    Evaluate    sorted(z['zone'] for z in $body['zones'])
    Should Be Equal    ${zones}    ${{ sorted([$ZONE_ACME, $ZONE_B]) }}

Check that a tenant adds, edits and deletes records
    ${body} =    Expect API    200    POST    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "www", "type": "A", "ttl": 300, "data": "192.0.2.10"}, {"name": "@", "type": "TXT", "data": "v=spf1 mx -all"}]}
    ${values} =    PowerDNS values    ${ZONE_A}    www.${ZONE_A}    A
    Should Be Equal    ${values}    ${{ ['192.0.2.10'] }}
    ${body} =    Expect API    200    GET    /v1/zones/${ZONE_A}/records?name=@&type=TXT    ${KEY_A_READ}
    Should Be Equal    ${body}[records][0][data]    v=spf1 mx -all
    # an edit as a dry run changes nothing
    ${edit} =    Set Variable    {"remove": [{"name": "www", "type": "A", "data": "192.0.2.10"}], "add": [{"name": "www", "type": "A", "ttl": 300, "data": "192.0.2.11"}]
    ${body} =    Expect API    200    POST    /v1/zones/${ZONE_A}/changes    ${KEY_A}    ${edit}, "dry_run": true}
    Should Be True    ${body}[dry_run]
    ${values} =    PowerDNS values    ${ZONE_A}    www.${ZONE_A}    A
    Should Be Equal    ${values}    ${{ ['192.0.2.10'] }}
    Expect API    200    POST    /v1/zones/${ZONE_A}/changes    ${KEY_A}    ${edit}}
    ${values} =    PowerDNS values    ${ZONE_A}    www.${ZONE_A}    A
    Should Be Equal    ${values}    ${{ ['192.0.2.11'] }}
    # the same edit again: what it removes is no longer there
    Expect API    409    POST    /v1/zones/${ZONE_A}/changes    ${KEY_A}    ${edit}}    code=stale
    # an RRset replaced as a whole
    Expect API    200    PUT    /v1/zones/${ZONE_A}/rrsets    ${KEY_A}    {"records": [{"name": "www", "type": "A", "ttl": 300, "data": "192.0.2.21"}, {"name": "www", "type": "A", "ttl": 300, "data": "192.0.2.22"}]}
    ${values} =    PowerDNS values    ${ZONE_A}    www.${ZONE_A}    A
    Should Be Equal    ${values}    ${{ ['192.0.2.21', '192.0.2.22'] }}
    # dnshelper's safety rails
    Expect API    409    POST    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "www", "type": "CNAME", "data": "web.example.net."}]}    code=conflict
    Expect API    403    POST    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "@", "type": "NS", "data": "ns9.example.net."}]}    code=forbidden
    Expect API    403    POST    /v1/zones/${ZONE_A}/records    ${KEY_A_READ}    {"records": [{"name": "x", "type": "A", "data": "192.0.2.1"}]}    code=insufficient_scope
    # one value of two deleted
    Expect API    200    DELETE    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "www", "type": "A", "data": "192.0.2.21"}]}
    ${values} =    PowerDNS values    ${ZONE_A}    www.${ZONE_A}    A
    Should Be Equal    ${values}    ${{ ['192.0.2.22'] }}

Check that dnshelper records whom each change was for
    ${output} =    Execute Command    journalctl --no-pager -o cat --since '-15min' | grep 'dnshelper audit:' | grep '"apply-changes"'
    Should Contain    ${output}    caller="module/${module_id}"
    Should Contain    ${output}    on_behalf_of="${TENANT_A}:${KEY_A_ID}"
    ${output} =    Execute Command    api-cli run module/${module_id}/list-activity
    Should Contain    ${output}    apply-changes

Check that a tenant cannot reach another tenant's zone
    Expect API    404    GET    /v1/zones/${ZONE_A}/records    ${KEY_B}    code=zone_not_found
    Expect API    404    POST    /v1/zones/${ZONE_A}/records    ${KEY_B}    {"records": [{"name": "x", "type": "A", "data": "192.0.2.1"}]}    code=zone_not_found
    Expect API    404    DELETE    /v1/zones/${ZONE_A}/records    ${KEY_B}    {"records": [{"name": "www"}]}    code=zone_not_found
    Expect API    404    GET    /v1/zones/${ZONE_A}/propagation?name=www&type=A    ${KEY_B}    code=zone_not_found
    Expect API    404    GET    /v1/zones/${ZONE_B}/records    ${KEY_A}    code=zone_not_found
    Expect API    404    POST    /v1/acme/present    ${KEY_B}    {"fqdn": "_acme-challenge.www.${ZONE_A}.", "value": "x"}    code=zone_not_found
    ${values} =    PowerDNS values    ${ZONE_A}    _acme-challenge.www.${ZONE_A}    TXT
    Should Be Empty    ${values}

Check that a zone dnshelper does not grant is unreachable
    FOR    ${key}    IN    ${OPERATOR_KEY}    ${KEY_A}
        Expect API    404    GET    /v1/zones/${ZONE_DENIED}/records    ${key}    code=zone_not_found
        Expect API    404    POST    /v1/zones/${ZONE_DENIED}/records    ${key}    {"records": [{"name": "x", "type": "A", "data": "192.0.2.1"}]}    code=zone_not_found
    END

Check that the API's own host name cannot be changed
    Expect API    403    POST    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "api", "type": "A", "data": "192.0.2.66"}]}    code=reserved_name
    Expect API    403    POST    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "_acme-challenge.api", "type": "TXT", "data": "x"}]}    code=reserved_name
    Expect API    403    DELETE    /v1/zones/${ZONE_A}/records    ${OPERATOR_KEY}    {"records": [{"name": "api"}]}    code=reserved_name
    # read it: dnsapi wrote it as itself, so it is listed as dnsapi's
    ${body} =    Expect API    200    GET    /v1/zones/${ZONE_A}/records?name=api&type=CNAME    ${KEY_A}
    Should Be Equal    ${body}[records][0][owned_by]    ${{ [$module_id] }}
    ${values} =    PowerDNS values    ${ZONE_A}    ${API_HOST}    CNAME
    Length Should Be    ${values}    1

Check the warning for a record another module wrote
    Expect API    200    POST    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "@", "type": "MX", "data": "10 mail.${ZONE_A}."}]}
    # dnshelper's owner index, as if the mail module had written the MX
    ${rc} =    Execute Command
    ...    runagent -m ${dnshelper_id} env AGENT_TASK_USER=module/mail1 python3 -c 'import os, sys; sys.path.insert(0, os.environ["AGENT_INSTALL_DIR"] + "/pypkg"); import dnshelper_lib as l; l.record_owners("${ZONE_A}", {"add": [{"name": "@", "type": "MX", "data": "10 mail.${ZONE_A}."}], "remove": []})'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    ${body} =    Expect API    200    GET    /v1/zones/${ZONE_A}/records?type=MX    ${KEY_A}
    Should Be Equal    ${body}[records][0][owned_by]    ${{ ['mail1'] }}
    ${body} =    Expect API    200    DELETE    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "@", "type": "MX"}], "dry_run": true}
    Should Be Equal    ${body}[warnings][0][code]    owned_by_module
    Should Be Equal    ${body}[warnings][0][modules]    ${{ ['mail1'] }}
    ${values} =    PowerDNS values    ${ZONE_A}    ${ZONE_A}    MX
    Length Should Be    ${values}    1
    ${body} =    Expect API    200    DELETE    /v1/zones/${ZONE_A}/records    ${KEY_A}    {"records": [{"name": "@", "type": "MX"}]}
    Should Be Equal    ${body}[warnings][0][code]    owned_by_module
    ${values} =    PowerDNS values    ${ZONE_A}    ${ZONE_A}    MX
    Should Be Empty    ${values}

Check ACME validation on a zone with only the ACME rule
    # as lego's httpreq and acme.sh's acmeproxy send it: Basic authentication, a trailing dot
    ${body} =    Set Variable    {"fqdn": "_acme-challenge.host1.${ZONE_ACME}.", "value": "ci-token-1"}
    ${output} =    Execute Command    curl -sk -u 'any:${KEY_B_ACME}' -H 'Content-Type: application/json' --data '${body}' -w '\\n\%{http_code}' --resolve ${API_HOST}:443:127.0.0.1 https://${API_HOST}/v1/acme/present
    Should End With    ${output}    200
    Should Contain    ${output}    "ci-token-1"
    Should Contain    ${output}    "zone": "${ZONE_ACME}"
    ${values} =    PowerDNS values    ${ZONE_ACME}    _acme-challenge.host1.${ZONE_ACME}    TXT
    Should Be Equal    ${values}    ${{ ['"ci-token-1"'] }}
    # a wildcard and its base name: two values at once, each removed on its own
    Expect API    200    POST    /v1/acme/present    ${KEY_B_ACME}    {"fqdn": "_acme-challenge.host1.${ZONE_ACME}.", "value": "ci-token-2"}
    ${values} =    PowerDNS values    ${ZONE_ACME}    _acme-challenge.host1.${ZONE_ACME}    TXT
    Length Should Be    ${values}    2
    Expect API    200    POST    /v1/acme/cleanup    ${KEY_B_ACME}    ${body}
    ${values} =    PowerDNS values    ${ZONE_ACME}    _acme-challenge.host1.${ZONE_ACME}    TXT
    Should Be Equal    ${values}    ${{ ['"ci-token-2"'] }}
    Expect API    200    POST    /v1/acme/cleanup    ${KEY_B_ACME}    {"fqdn": "_acme-challenge.host1.${ZONE_ACME}.", "value": "ci-token-2"}
    ${values} =    PowerDNS values    ${ZONE_ACME}    _acme-challenge.host1.${ZONE_ACME}    TXT
    Should Be Empty    ${values}
    Expect API    400    POST    /v1/acme/present    ${KEY_B_ACME}    {"fqdn": "www.${ZONE_ACME}.", "value": "x"}

Check the two limits on ACME records
    # dnsapi's: the key is restricted to ACME records
    Expect API    403    POST    /v1/zones/${ZONE_ACME}/records    ${KEY_B_ACME}    {"records": [{"name": "www", "type": "A", "data": "192.0.2.1"}]}    code=outside_restriction
    Expect API    403    POST    /v1/zones/${ZONE_B}/records    ${KEY_B_ACME}    {"records": [{"name": "www", "type": "A", "data": "192.0.2.1"}]}    code=outside_restriction
    # dnshelper's: its rule for dnsapi covers only ACME records in this zone
    Expect API    403    POST    /v1/zones/${ZONE_ACME}/records    ${KEY_B}    {"records": [{"name": "www", "type": "A", "data": "192.0.2.1"}]}    code=not_permitted
    ${values} =    PowerDNS values    ${ZONE_ACME}    www.${ZONE_ACME}    A
    Should Be Empty    ${values}
    # in a zone with full access the restricted key sees only ACME records
    Expect API    200    POST    /v1/zones/${ZONE_B}/records    ${KEY_B}    {"records": [{"name": "www", "type": "A", "data": "192.0.2.5"}, {"name": "_acme-challenge.www", "type": "TXT", "data": "left"}]}
    ${body} =    Expect API    200    GET    /v1/zones/${ZONE_B}/records    ${KEY_B_ACME}
    ${names} =    Names in    ${body}
    Should Be Equal    ${names}    ${{ ['_acme-challenge.www TXT'] }}

Check that the Status page counts the zones
    ${output} =    Execute Command    api-cli run module/${module_id}/get-overview
    ${overview} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal As Integers    ${overview}[zones_assigned]    3
    Should Be Equal    ${overview}[host_record][status]    ok
    ${output} =    Execute Command    api-cli run module/${module_id}/list-assignable-zones
    Should Contain    ${output}    ${ZONE_A}
    Should Not Contain    ${output}    ${ZONE_DENIED}

Take screenshots of the pages
    # With dnshelper, two tenants with zones and their keys, so the pages show
    # what an administrator sees, without the "dnshelper missing" notices.
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

Check that dnsapi drops a zone dnshelper no longer manages
    Run action    ${dnshelper_id}    remove-zone    {"zone":"${ZONE_B}"}
    Wait Until Keyword Succeeds    60s    3s    Tenant has zones    ${TENANT_B}    ${ZONE_ACME}
    Expect API    404    GET    /v1/zones/${ZONE_B}/records    ${KEY_B}    code=zone_not_found

Check that removing the tenants removes their keys
    Expect API    204    DELETE    /v1/tenants/${TENANT_A}    ${OPERATOR_KEY}
    Expect API    204    DELETE    /v1/tenants/${TENANT_B}    ${OPERATOR_KEY}
    Expect API    401    GET    /v1/zones    ${KEY_A}    code=invalid_key
    Expect API    401    GET    /v1/zones    ${KEY_B_ACME}    code=invalid_key
    # the records the tenants wrote stay
    ${values} =    PowerDNS values    ${ZONE_A}    www.${ZONE_A}    A
    Should Be Equal    ${values}    ${{ ['192.0.2.22'] }}

Check that dnsapi notices dnshelper removed
    ${rc} =    Execute Command    remove-module --no-preserve ${dnshelper_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    Wait Until Keyword Succeeds    60s    3s    dnsapi reports dnshelper missing
    # the zone list is cached for 30 s (the provider list for 10 minutes, so it is not checked)
    Wait Until Keyword Succeeds    90s    5s    Expect API    503    GET    /v1/zones    ${OPERATOR_KEY}    code=dnshelper_missing
    Execute Command    podman rm -f dnsapi-ci-pdns

Check if dnsapi is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
