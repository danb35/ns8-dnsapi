# update-tenant input Schema

```txt
http://schema.nethserver.org/dnsapi/update-tenant-input.json
```

Rename, enable or disable a tenant

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                         |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [update-tenant-input.json](dnsapi/update-tenant-input.json "open original schema") |

## update-tenant input Type

`object` ([update-tenant input](update-tenant-input.md))

## update-tenant input Examples

```json
{
  "id": "t1a2b3c4d",
  "enabled": false
}
```

# update-tenant input Properties

| Property            | Type      | Required | Nullable       | Defined by                                                                                                                                          |
| :------------------ | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)           | `string`  | Required | cannot be null | [update-tenant input](update-tenant-input-properties-id.md "http://schema.nethserver.org/dnsapi/update-tenant-input.json#/properties/id")           |
| [name](#name)       | `string`  | Optional | cannot be null | [update-tenant input](update-tenant-input-properties-name.md "http://schema.nethserver.org/dnsapi/update-tenant-input.json#/properties/name")       |
| [enabled](#enabled) | `boolean` | Optional | cannot be null | [update-tenant input](update-tenant-input-properties-enabled.md "http://schema.nethserver.org/dnsapi/update-tenant-input.json#/properties/enabled") |

## id

Tenant id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [update-tenant input](update-tenant-input-properties-id.md "http://schema.nethserver.org/dnsapi/update-tenant-input.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^t[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5Et%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## name

Display name

`name`

* is optional

* Type: `string`

* cannot be null

* defined in: [update-tenant input](update-tenant-input-properties-name.md "http://schema.nethserver.org/dnsapi/update-tenant-input.json#/properties/name")

### name Type

`string`

### name Constraints

**maximum length**: the maximum number of characters for this string is: `100`

**minimum length**: the minimum number of characters for this string is: `1`

**pattern**: the string must match the following regular expression:&#x20;

```regexp
\S
```

[try pattern](https://regexr.com/?expression=%5CS "try regular expression with regexr.com")

## enabled



`enabled`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [update-tenant input](update-tenant-input-properties-enabled.md "http://schema.nethserver.org/dnsapi/update-tenant-input.json#/properties/enabled")

### enabled Type

`boolean`
