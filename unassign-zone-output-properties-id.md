# Untitled string in unassign-zone output Schema

```txt
http://schema.nethserver.org/dnsapi/unassign-zone-output.json#/properties/id
```

Tenant id

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                             |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [unassign-zone-output.json\*](dnsapi/unassign-zone-output.json "open original schema") |

## id Type

`string`

## id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^t[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5Et%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")
