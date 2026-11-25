# Untitled undefined type in list-keys output Schema

```txt
http://schema.nethserver.org/dnsapi/list-keys-output.json#/properties/keys/items/properties/status
```



| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [list-keys-output.json\*](dnsapi/list-keys-output.json "open original schema") |

## status Type

unknown

## status Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value       | Explanation |    |    |
| :---------- | :---------- | :- | :- |
| `"active"`  |             |
| `"expired"` |             |
| `"revoked"` |             |
