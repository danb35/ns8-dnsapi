# Untitled undefined type in get-overview output Schema

```txt
http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/host_record/properties/status
```



| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                           |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [get-overview-output.json\*](dnsapi/get-overview-output.json "open original schema") |

## status Type

unknown

## status Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value             | Explanation |    |    |
| :---------------- | :---------- | :- | :- |
| `"ok"`            |             |
| `"created"`       |             |
| `"conflict"`      |             |
| `"not_managed"`   |             |
| `"not_permitted"` |             |
| `"apex"`          |             |
| `"disabled"`      |             |
| `"error"`         |             |
