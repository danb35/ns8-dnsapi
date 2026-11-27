# Untitled string in unassign-zone input Schema

```txt
http://schema.nethserver.org/dnsapi/unassign-zone-input.json#/properties/tenant
```

Tenant id

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                           |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [unassign-zone-input.json\*](dnsapi/unassign-zone-input.json "open original schema") |

## tenant Type

`string`

## tenant Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^t[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5Et%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")
