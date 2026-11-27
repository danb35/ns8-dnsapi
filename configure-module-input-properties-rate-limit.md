# Rate limit Schema

```txt
http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/rate_limit
```

DNS requests per minute for each API key: every request that calls dnshelper counts, reads included, because the DNS hosts' own limits count them too. Default 60.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [configure-module-input.json\*](dnsapi/configure-module-input.json "open original schema") |

## rate_limit Type

`integer` ([Rate limit](configure-module-input-properties-rate-limit.md))

## rate_limit Constraints

**maximum**: the value of this number must smaller than or equal to: `10000`

**minimum**: the value of this number must greater than or equal to: `1`
