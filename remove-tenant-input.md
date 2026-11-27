# remove-tenant input Schema

```txt
http://schema.nethserver.org/dnsapi/remove-tenant-input.json
```

Remove a tenant, its zone assignments and its keys

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                         |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [remove-tenant-input.json](dnsapi/remove-tenant-input.json "open original schema") |

## remove-tenant input Type

`object` ([remove-tenant input](remove-tenant-input.md))

## remove-tenant input Examples

```json
{
  "id": "t1a2b3c4d"
}
```

# remove-tenant input Properties

| Property  | Type     | Required | Nullable       | Defined by                                                                                                                                |
| :-------- | :------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id) | `string` | Required | cannot be null | [remove-tenant input](remove-tenant-input-properties-id.md "http://schema.nethserver.org/dnsapi/remove-tenant-input.json#/properties/id") |

## id

Tenant id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [remove-tenant input](remove-tenant-input-properties-id.md "http://schema.nethserver.org/dnsapi/remove-tenant-input.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^t[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5Et%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")
