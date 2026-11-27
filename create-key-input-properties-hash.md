# Untitled string in create-key input Schema

```txt
http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/hash
```



| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [create-key-input.json\*](dnsapi/create-key-input.json "open original schema") |

## hash Type

`string`

## hash Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{64}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B64%7D%24 "try regular expression with regexr.com")
