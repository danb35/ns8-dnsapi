# Untitled array in update-key input Schema

```txt
http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/allowlist
```

IP addresses or CIDR networks the key may be used from; empty for any

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [update-key-input.json\*](dnsapi/update-key-input.json "open original schema") |

## allowlist Type

`string[]`

## allowlist Constraints

**maximum number of items**: the maximum number of items for this array is: `100`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
