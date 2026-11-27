# HTTP to HTTPS redirection (ignored) Schema

```txt
http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/http2https
```

Accepted for compatibility and ignored: the route never redirects, so that the API can refuse a plain-HTTP request itself, with 403 https_required, and revoke the key it carried.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [configure-module-input.json\*](dnsapi/configure-module-input.json "open original schema") |

## http2https Type

`boolean` ([HTTP to HTTPS redirection (ignored)](configure-module-input-properties-http-to-https-redirection-ignored.md))
