# Revoke keys sent over plain HTTP Schema

```txt
http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/revoke_cleartext_keys
```

Revoke a valid key, operator keys included, as soon as the API receives it over plain HTTP; the request is refused either way. Default true.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [configure-module-input.json\*](dnsapi/configure-module-input.json "open original schema") |

## revoke_cleartext_keys Type

`boolean` ([Revoke keys sent over plain HTTP](configure-module-input-properties-revoke-keys-sent-over-plain-http.md))
