# Untitled object in list-tenants output Schema

```txt
http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                           |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-tenants-output.json\*](dnsapi/list-tenants-output.json "open original schema") |

## items Type

`object` ([Details](list-tenants-output-properties-tenants-items.md))

# items Properties

| Property            | Type      | Required | Nullable       | Defined by                                                                                                                                                                                            |
| :------------------ | :-------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)           | `string`  | Required | cannot be null | [list-tenants output](list-tenants-output-properties-tenants-items-properties-id.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/id")           |
| [name](#name)       | `string`  | Required | cannot be null | [list-tenants output](list-tenants-output-properties-tenants-items-properties-name.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/name")       |
| [enabled](#enabled) | `boolean` | Required | cannot be null | [list-tenants output](list-tenants-output-properties-tenants-items-properties-enabled.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/enabled") |
| [zones](#zones)     | `array`   | Required | cannot be null | [list-tenants output](list-tenants-output-properties-tenants-items-properties-zones.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/zones")     |
| [created](#created) | `string`  | Required | can be null    | [list-tenants output](list-tenants-output-properties-tenants-items-properties-created.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/created") |
| [keys](#keys)       | `integer` | Optional | cannot be null | [list-tenants output](list-tenants-output-properties-tenants-items-properties-keys.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/keys")       |

## id

Tenant id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [list-tenants output](list-tenants-output-properties-tenants-items-properties-id.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/id")

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

* defined in: [list-tenants output](list-tenants-output-properties-tenants-items-properties-name.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/name")

### name Type

`string`

## enabled



`enabled`

* is required

* Type: `boolean`

* cannot be null

* defined in: [list-tenants output](list-tenants-output-properties-tenants-items-properties-enabled.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/enabled")

### enabled Type

`boolean`

## zones



`zones`

* is required

* Type: `string[]`

* cannot be null

* defined in: [list-tenants output](list-tenants-output-properties-tenants-items-properties-zones.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/zones")

### zones Type

`string[]`

## created



`created`

* is required

* Type: `string`

* can be null

* defined in: [list-tenants output](list-tenants-output-properties-tenants-items-properties-created.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/created")

### created Type

`string`

## keys

Number of keys

`keys`

* is optional

* Type: `integer`

* cannot be null

* defined in: [list-tenants output](list-tenants-output-properties-tenants-items-properties-keys.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/keys")

### keys Type

`integer`
