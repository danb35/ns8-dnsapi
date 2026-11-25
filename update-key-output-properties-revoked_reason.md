# Untitled undefined type in update-key output Schema

```txt
http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/revoked_reason
```

revoked: by an administrator or the API; plain_http: sent over plain HTTP

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                       |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [update-key-output.json\*](dnsapi/update-key-output.json "open original schema") |

## revoked_reason Type

unknown

## revoked_reason Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value          | Explanation |    |    |
| :------------- | :---------- | :- | :- |
| `"revoked"`    |             |
| `"plain_http"` |             |
| `null`         |             |
