# Allowed client addresses Schema

```txt
http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/ip_allowlist
```

IP addresses or CIDR networks that Traefik lets reach the API; every other client gets 403 from Traefik. An empty list allows every address. Default empty.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [configure-module-input.json\*](dnsapi/configure-module-input.json "open original schema") |

## ip_allowlist Type

`string[]`

## ip_allowlist Constraints

**maximum number of items**: the maximum number of items for this array is: `100`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
