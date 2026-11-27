# get-overview output Schema

```txt
http://schema.nethserver.org/dnsapi/get-overview-output.json
```

What the Status page shows. dnshelper_error: dnshelper_missing, dnshelper_too_old or unavailable

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                         |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [get-overview-output.json](dnsapi/get-overview-output.json "open original schema") |

## get-overview output Type

`object` ([get-overview output](get-overview-output.md))

## get-overview output Examples

```json
{
  "host": "dnsapi.example.com",
  "url": "https://dnsapi.example.com/v1/",
  "dnshelper": "dnshelper1",
  "dnshelper_error": null,
  "zones_writable": 3,
  "zones_full": 2,
  "zones_assigned": 2,
  "tenants": 2,
  "tenants_disabled": 0,
  "keys_operator": 1,
  "keys_tenant": 3,
  "host_record": null,
  "exposed_keys": [
    {
      "time": "2026-11-22T09:30:00Z",
      "key": "a1b2c3d4",
      "owner": "t1a2b3c4d",
      "address": "203.0.113.10",
      "tenant_name": "Acme Shop"
    }
  ]
}
```

# get-overview output Properties

| Property                              | Type      | Required | Nullable       | Defined by                                                                                                                                                            |
| :------------------------------------ | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [host](#host)                         | `string`  | Required | can be null    | [get-overview output](get-overview-output-properties-host.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/host")                         |
| [url](#url)                           | `string`  | Required | can be null    | [get-overview output](get-overview-output-properties-url.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/url")                           |
| [dnshelper](#dnshelper)               | `string`  | Required | can be null    | [get-overview output](get-overview-output-properties-dnshelper.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/dnshelper")               |
| [dnshelper_error](#dnshelper_error)   | `string`  | Required | can be null    | [get-overview output](get-overview-output-properties-dnshelper_error.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/dnshelper_error")   |
| [zones_writable](#zones_writable)     | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-zones_writable.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/zones_writable")     |
| [zones_full](#zones_full)             | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-zones_full.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/zones_full")             |
| [zones_assigned](#zones_assigned)     | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-zones_assigned.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/zones_assigned")     |
| [tenants](#tenants)                   | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-tenants.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/tenants")                   |
| [tenants_disabled](#tenants_disabled) | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-tenants_disabled.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/tenants_disabled") |
| [keys_operator](#keys_operator)       | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-keys_operator.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/keys_operator")       |
| [keys_tenant](#keys_tenant)           | `integer` | Required | cannot be null | [get-overview output](get-overview-output-properties-keys_tenant.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/keys_tenant")           |
| [host_record](#host_record)           | `object`  | Required | can be null    | [get-overview output](get-overview-output-properties-host_record.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/host_record")           |
| [exposed_keys](#exposed_keys)         | `array`   | Required | cannot be null | [get-overview output](get-overview-output-properties-exposed_keys.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys")         |

## host



`host`

* is required

* Type: `string`

* can be null

* defined in: [get-overview output](get-overview-output-properties-host.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/host")

### host Type

`string`

## url



`url`

* is required

* Type: `string`

* can be null

* defined in: [get-overview output](get-overview-output-properties-url.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/url")

### url Type

`string`

## dnshelper



`dnshelper`

* is required

* Type: `string`

* can be null

* defined in: [get-overview output](get-overview-output-properties-dnshelper.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/dnshelper")

### dnshelper Type

`string`

## dnshelper_error



`dnshelper_error`

* is required

* Type: `string`

* can be null

* defined in: [get-overview output](get-overview-output-properties-dnshelper_error.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/dnshelper_error")

### dnshelper_error Type

`string`

## zones_writable



`zones_writable`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-zones_writable.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/zones_writable")

### zones_writable Type

`integer`

### zones_writable Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## zones_full



`zones_full`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-zones_full.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/zones_full")

### zones_full Type

`integer`

### zones_full Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## zones_assigned



`zones_assigned`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-zones_assigned.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/zones_assigned")

### zones_assigned Type

`integer`

### zones_assigned Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## tenants



`tenants`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-tenants.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/tenants")

### tenants Type

`integer`

### tenants Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## tenants_disabled



`tenants_disabled`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-tenants_disabled.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/tenants_disabled")

### tenants_disabled Type

`integer`

### tenants_disabled Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## keys_operator



`keys_operator`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-keys_operator.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/keys_operator")

### keys_operator Type

`integer`

### keys_operator Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## keys_tenant



`keys_tenant`

* is required

* Type: `integer`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-keys_tenant.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/keys_tenant")

### keys_tenant Type

`integer`

### keys_tenant Constraints

**minimum**: the value of this number must greater than or equal to: `0`

## host_record

The host name's CNAME to the node, as configure-module last found it; null before it has run

`host_record`

* is required

* Type: `object` ([Details](get-overview-output-properties-host_record.md))

* can be null

* defined in: [get-overview output](get-overview-output-properties-host_record.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/host_record")

### host_record Type

`object` ([Details](get-overview-output-properties-host_record.md))

## exposed_keys

Keys revoked in the last 7 days because the API received them over plain HTTP, newest first

`exposed_keys`

* is required

* Type: `object[]` ([Details](get-overview-output-properties-exposed_keys-items.md))

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-exposed_keys.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys")

### exposed_keys Type

`object[]` ([Details](get-overview-output-properties-exposed_keys-items.md))
