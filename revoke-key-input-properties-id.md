# Untitled string in revoke-key input Schema

```txt
http://schema.nethserver.org/dnsapi/revoke-key-input.json#/properties/id
```

Key id

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [revoke-key-input.json\*](dnsapi/revoke-key-input.json "open original schema") |

## id Type

`string`

## id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")
