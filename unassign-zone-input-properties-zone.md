# Untitled string in unassign-zone input Schema

```txt
http://schema.nethserver.org/dnsapi/unassign-zone-input.json#/properties/zone
```

A zone managed by dnshelper, like 'example.com'

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                           |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [unassign-zone-input.json\*](dnsapi/unassign-zone-input.json "open original schema") |

## zone Type

`string`

## zone Constraints

**maximum length**: the maximum number of characters for this string is: `253`

**minimum length**: the minimum number of characters for this string is: `3`

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[A-Za-z0-9_.-]+\.?$
```

[try pattern](https://regexr.com/?expression=%5E%5BA-Za-z0-9_.-%5D%2B%5C.%3F%24 "try regular expression with regexr.com")
