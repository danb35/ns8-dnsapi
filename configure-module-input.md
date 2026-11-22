# configure-module input Schema

```txt
http://schema.nethserver.org/dnsapi/configure-module-input.json
```

Configure dnsapi: the host name the API is published on, its certificate and HTTP redirect, the client addresses Traefik lets through, and the per-key rate limit. An omitted field keeps its current value; host is required until it has been set once.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                               |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [configure-module-input.json](dnsapi/configure-module-input.json "open original schema") |

## configure-module input Type

`object` ([configure-module input](configure-module-input.md))

## configure-module input Examples

```json
{
  "host": "dnsapi.example.com",
  "lets_encrypt": true,
  "http2https": true,
  "ip_allowlist": [
    "203.0.113.10",
    "198.51.100.0/24"
  ],
  "rate_limit": 60,
  "publish_host_record": true
}
```

```json
{
  "ip_allowlist": []
}
```

# configure-module input Properties

| Property                                    | Type      | Required | Nullable       | Defined by                                                                                                                                                                                    |
| :------------------------------------------ | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [host](#host)                               | `string`  | Optional | cannot be null | [configure-module input](configure-module-input-properties-api-host-name.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/host")                               |
| [lets_encrypt](#lets_encrypt)               | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-lets-encrypt-certificate.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/lets_encrypt")            |
| [http2https](#http2https)                   | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-http-to-https-redirection.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/http2https")             |
| [ip_allowlist](#ip_allowlist)               | `array`   | Optional | cannot be null | [configure-module input](configure-module-input-properties-allowed-client-addresses.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/ip_allowlist")            |
| [rate_limit](#rate_limit)                   | `integer` | Optional | cannot be null | [configure-module input](configure-module-input-properties-rate-limit.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/rate_limit")                            |
| [publish_host_record](#publish_host_record) | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-publish-the-host-name-in-dns.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/publish_host_record") |

## host

A fully qualified host name that Traefik routes to the API. It must not be used by another route.

`host`

* is optional

* Type: `string` ([API host name](configure-module-input-properties-api-host-name.md))

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-api-host-name.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/host")

### host Type

`string` ([API host name](configure-module-input-properties-api-host-name.md))

### host Constraints

**maximum length**: the maximum number of characters for this string is: `253`

**pattern**: the string must match the following regular expression:&#x20;

```regexp
\.
```

[try pattern](https://regexr.com/?expression=%5C. "try regular expression with regexr.com")

**hostname**: the string must be a hostname, according to [RFC 1123, section 2.1](https://tools.ietf.org/html/rfc1123 "check the specification")

## lets_encrypt

Request a Let's Encrypt certificate for the host name. The request must succeed for the action to succeed. Default false.

`lets_encrypt`

* is optional

* Type: `boolean` ([Let's Encrypt certificate](configure-module-input-properties-lets-encrypt-certificate.md))

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-lets-encrypt-certificate.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/lets_encrypt")

### lets_encrypt Type

`boolean` ([Let's Encrypt certificate](configure-module-input-properties-lets-encrypt-certificate.md))

## http2https

Redirect plain HTTP requests to HTTPS. Default true.

`http2https`

* is optional

* Type: `boolean` ([HTTP to HTTPS redirection](configure-module-input-properties-http-to-https-redirection.md))

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-http-to-https-redirection.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/http2https")

### http2https Type

`boolean` ([HTTP to HTTPS redirection](configure-module-input-properties-http-to-https-redirection.md))

## ip_allowlist

IP addresses or CIDR networks that Traefik lets reach the API; every other client gets 403 from Traefik. An empty list allows every address. Default empty.

`ip_allowlist`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-allowed-client-addresses.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/ip_allowlist")

### ip_allowlist Type

`string[]`

### ip_allowlist Constraints

**maximum number of items**: the maximum number of items for this array is: `100`

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## rate_limit

DNS requests per minute for each API key: every request that calls dnshelper counts, reads included, because the DNS hosts' own limits count them too. Default 60.

`rate_limit`

* is optional

* Type: `integer` ([Rate limit](configure-module-input-properties-rate-limit.md))

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-rate-limit.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/rate_limit")

### rate_limit Type

`integer` ([Rate limit](configure-module-input-properties-rate-limit.md))

### rate_limit Constraints

**maximum**: the value of this number must smaller than or equal to: `10000`

**minimum**: the value of this number must greater than or equal to: `1`

## publish_host_record

When the host name is in a zone dnshelper manages and its rules let dnsapi write it, add a CNAME from the host name to this node if there is none. Another record at the name is never changed. Default true.

`publish_host_record`

* is optional

* Type: `boolean` ([Publish the host name in DNS](configure-module-input-properties-publish-the-host-name-in-dns.md))

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-publish-the-host-name-in-dns.md "http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/publish_host_record")

### publish_host_record Type

`boolean` ([Publish the host name in DNS](configure-module-input-properties-publish-the-host-name-in-dns.md))
