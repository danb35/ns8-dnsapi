# unassign-zone input Schema

```txt
http://schema.nethserver.org/dnsapi/unassign-zone-input.json
```

Take a zone from a tenant; its records are not changed

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                         |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [unassign-zone-input.json](dnsapi/unassign-zone-input.json "open original schema") |

## unassign-zone input Type

`object` ([unassign-zone input](unassign-zone-input.md))

## unassign-zone input Examples

```json
{
  "tenant": "t1a2b3c4d",
  "zone": "example.com"
}
```

# unassign-zone input Properties

| Property          | Type     | Required | Nullable       | Defined by                                                                                                                                        |
| :---------------- | :------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| [tenant](#tenant) | `string` | Required | cannot be null | [unassign-zone input](unassign-zone-input-properties-tenant.md "http://schema.nethserver.org/dnsapi/unassign-zone-input.json#/properties/tenant") |
| [zone](#zone)     | `string` | Required | cannot be null | [unassign-zone input](unassign-zone-input-properties-zone.md "http://schema.nethserver.org/dnsapi/unassign-zone-input.json#/properties/zone")     |

## tenant

Tenant id

`tenant`

* is required

* Type: `string`

* cannot be null

* defined in: [unassign-zone input](unassign-zone-input-properties-tenant.md "http://schema.nethserver.org/dnsapi/unassign-zone-input.json#/properties/tenant")

### tenant Type

`string`

### tenant Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^t[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5Et%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## zone

A zone managed by dnshelper, like 'example.com'

`zone`

* is required

* Type: `string`

* cannot be null

* defined in: [unassign-zone input](unassign-zone-input-properties-zone.md "http://schema.nethserver.org/dnsapi/unassign-zone-input.json#/properties/zone")

### zone Type

`string`

### zone Constraints

**maximum length**: the maximum number of characters for this string is: `253`

**minimum length**: the minimum number of characters for this string is: `3`

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[A-Za-z0-9_.-]+\.?$
```

[try pattern](https://regexr.com/?expression=%5E%5BA-Za-z0-9_.-%5D%2B%5C.%3F%24 "try regular expression with regexr.com")
