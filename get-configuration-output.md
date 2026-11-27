# get-configuration output Schema

```txt
http://schema.nethserver.org/dnsapi/get-configuration-output.json
```

Get dnsapi configuration. host is null until configure-module has run.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                   |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [get-configuration-output.json](dnsapi/get-configuration-output.json "open original schema") |

## get-configuration output Type

`object` ([get-configuration output](get-configuration-output.md))

## get-configuration output Examples

```json
{
  "host": "dnsapi.example.com",
  "lets_encrypt": true,
  "ip_allowlist": [
    "203.0.113.10"
  ],
  "rate_limit": 60,
  "publish_host_record": true,
  "revoke_cleartext_keys": true,
  "host_record": {
    "host": "dnsapi.example.com",
    "target": "node1.example.com",
    "zone": "example.com",
    "status": "ok",
    "existing": [
      "CNAME node1.example.com."
    ],
    "message": "",
    "checked": "2026-11-21T18:00:00Z"
  }
}
```

# get-configuration output Properties

| Property                                        | Type      | Required | Nullable       | Defined by                                                                                                                                                                                     |
| :---------------------------------------------- | :-------- | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [host](#host)                                   | `string`  | Required | can be null    | [get-configuration output](get-configuration-output-properties-host.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host")                                   |
| [lets_encrypt](#lets_encrypt)                   | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-lets_encrypt.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/lets_encrypt")                   |
| [ip_allowlist](#ip_allowlist)                   | `array`   | Required | cannot be null | [get-configuration output](get-configuration-output-properties-ip_allowlist.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/ip_allowlist")                   |
| [rate_limit](#rate_limit)                       | `integer` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-rate_limit.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/rate_limit")                       |
| [publish_host_record](#publish_host_record)     | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-publish_host_record.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/publish_host_record")     |
| [revoke_cleartext_keys](#revoke_cleartext_keys) | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-revoke_cleartext_keys.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/revoke_cleartext_keys") |
| [host_record](#host_record)                     | `object`  | Required | can be null    | [get-configuration output](get-configuration-output-properties-host_record.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record")                     |

## host

The API host name

`host`

* is required

* Type: `string`

* can be null

* defined in: [get-configuration output](get-configuration-output-properties-host.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host")

### host Type

`string`

## lets_encrypt



`lets_encrypt`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-lets_encrypt.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/lets_encrypt")

### lets_encrypt Type

`boolean`

## ip_allowlist



`ip_allowlist`

* is required

* Type: `string[]`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-ip_allowlist.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/ip_allowlist")

### ip_allowlist Type

`string[]`

## rate_limit



`rate_limit`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-rate_limit.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/rate_limit")

### rate_limit Type

`integer`

## publish_host_record



`publish_host_record`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-publish_host_record.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/publish_host_record")

### publish_host_record Type

`boolean`

## revoke_cleartext_keys



`revoke_cleartext_keys`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-revoke_cleartext_keys.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/revoke_cleartext_keys")

### revoke_cleartext_keys Type

`boolean`

## host_record

The host name's CNAME to the node, as configure-module last found it; null before it has run

`host_record`

* is required

* Type: `object` ([Details](get-configuration-output-properties-host_record.md))

* can be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record")

### host_record Type

`object` ([Details](get-configuration-output-properties-host_record.md))
