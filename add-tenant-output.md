# add-tenant output Schema

```txt
http://schema.nethserver.org/dnsapi/add-tenant-output.json
```

The new tenant

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [add-tenant-output.json](dnsapi/add-tenant-output.json "open original schema") |

## add-tenant output Type

`object` ([add-tenant output](add-tenant-output.md))

## add-tenant output Examples

```json
{
  "id": "t1a2b3c4d",
  "name": "Acme Ltd",
  "enabled": true,
  "zones": [],
  "created": "2026-11-21T18:00:00Z"
}
```

# add-tenant output Properties

| Property            | Type      | Required | Nullable       | Defined by                                                                                                                                    |
| :------------------ | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)           | `string`  | Required | cannot be null | [add-tenant output](add-tenant-output-properties-id.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/id")           |
| [name](#name)       | `string`  | Required | cannot be null | [add-tenant output](add-tenant-output-properties-name.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/name")       |
| [enabled](#enabled) | `boolean` | Required | cannot be null | [add-tenant output](add-tenant-output-properties-enabled.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/enabled") |
| [zones](#zones)     | `array`   | Required | cannot be null | [add-tenant output](add-tenant-output-properties-zones.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/zones")     |
| [created](#created) | `string`  | Required | can be null    | [add-tenant output](add-tenant-output-properties-created.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/created") |
| [keys](#keys)       | `integer` | Optional | cannot be null | [add-tenant output](add-tenant-output-properties-keys.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/keys")       |

## id

Tenant id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [add-tenant output](add-tenant-output-properties-id.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^t[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5Et%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## name



`name`

* is required

* Type: `string`

* cannot be null

* defined in: [add-tenant output](add-tenant-output-properties-name.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/name")

### name Type

`string`

## enabled



`enabled`

* is required

* Type: `boolean`

* cannot be null

* defined in: [add-tenant output](add-tenant-output-properties-enabled.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/enabled")

### enabled Type

`boolean`

## zones



`zones`

* is required

* Type: `string[]`

* cannot be null

* defined in: [add-tenant output](add-tenant-output-properties-zones.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/zones")

### zones Type

`string[]`

## created



`created`

* is required

* Type: `string`

* can be null

* defined in: [add-tenant output](add-tenant-output-properties-created.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/created")

### created Type

`string`

## keys

Number of keys

`keys`

* is optional

* Type: `integer`

* cannot be null

* defined in: [add-tenant output](add-tenant-output-properties-keys.md "http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/keys")

### keys Type

`integer`
