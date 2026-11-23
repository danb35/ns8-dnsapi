# add-tenant input Schema

```txt
http://schema.nethserver.org/dnsapi/add-tenant-input.json
```

Add a tenant

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                   |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [add-tenant-input.json](dnsapi/add-tenant-input.json "open original schema") |

## add-tenant input Type

`object` ([add-tenant input](add-tenant-input.md))

## add-tenant input Examples

```json
{
  "name": "Acme Ltd"
}
```

# add-tenant input Properties

| Property            | Type      | Required | Nullable       | Defined by                                                                                                                                 |
| :------------------ | :-------- | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| [name](#name)       | `string`  | Required | cannot be null | [add-tenant input](add-tenant-input-properties-name.md "http://schema.nethserver.org/dnsapi/add-tenant-input.json#/properties/name")       |
| [enabled](#enabled) | `boolean` | Optional | cannot be null | [add-tenant input](add-tenant-input-properties-enabled.md "http://schema.nethserver.org/dnsapi/add-tenant-input.json#/properties/enabled") |

## name

Display name

`name`

* is required

* Type: `string`

* cannot be null

* defined in: [add-tenant input](add-tenant-input-properties-name.md "http://schema.nethserver.org/dnsapi/add-tenant-input.json#/properties/name")

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

* defined in: [add-tenant input](add-tenant-input-properties-enabled.md "http://schema.nethserver.org/dnsapi/add-tenant-input.json#/properties/enabled")

### enabled Type

`boolean`
