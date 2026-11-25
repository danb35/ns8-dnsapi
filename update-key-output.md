# update-key output Schema

```txt
http://schema.nethserver.org/dnsapi/update-key-output.json
```

The key after the change, without its hash

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [update-key-output.json](dnsapi/update-key-output.json "open original schema") |

## update-key output Type

`object` ([update-key output](update-key-output.md))

# update-key output Properties

| Property                          | Type          | Required | Nullable       | Defined by                                                                                                                                                  |
| :-------------------------------- | :------------ | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)                         | `string`      | Required | cannot be null | [update-key output](update-key-output-properties-id.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/id")                         |
| [owner](#owner)                   | `string`      | Required | cannot be null | [update-key output](update-key-output-properties-owner.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/owner")                   |
| [scope](#scope)                   | Not specified | Required | cannot be null | [update-key output](update-key-output-properties-scope.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/scope")                   |
| [label](#label)                   | `string`      | Required | cannot be null | [update-key output](update-key-output-properties-label.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/label")                   |
| [allowlist](#allowlist)           | `array`       | Required | cannot be null | [update-key output](update-key-output-properties-allowlist.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/allowlist")           |
| [expires](#expires)               | `string`      | Required | can be null    | [update-key output](update-key-output-properties-expires.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/expires")               |
| [created](#created)               | `string`      | Required | can be null    | [update-key output](update-key-output-properties-created.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/created")               |
| [last_used](#last_used)           | `string`      | Required | can be null    | [update-key output](update-key-output-properties-last_used.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/last_used")           |
| [status](#status)                 | Not specified | Required | cannot be null | [update-key output](update-key-output-properties-status.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/status")                 |
| [revoked](#revoked)               | `string`      | Optional | can be null    | [update-key output](update-key-output-properties-revoked.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/revoked")               |
| [revoked_reason](#revoked_reason) | Not specified | Optional | cannot be null | [update-key output](update-key-output-properties-revoked_reason.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/revoked_reason") |
| [restrict](#restrict)             | `object`      | Required | can be null    | [update-key output](update-key-output-properties-restrict.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/restrict")             |
| [modified](#modified)             | `string`      | Optional | can be null    | [update-key output](update-key-output-properties-modified.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/modified")             |

## id

Key id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [update-key output](update-key-output-properties-id.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## owner

'operator' or a tenant id

`owner`

* is required

* Type: `string`

* cannot be null

* defined in: [update-key output](update-key-output-properties-owner.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/owner")

### owner Type

`string`

## scope



`scope`

* is required

* Type: unknown

* cannot be null

* defined in: [update-key output](update-key-output-properties-scope.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/scope")

### scope Type

unknown

### scope Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value     | Explanation |    |    |
| :-------- | :---------- | :- | :- |
| `"read"`  |             |
| `"write"` |             |

## label



`label`

* is required

* Type: `string`

* cannot be null

* defined in: [update-key output](update-key-output-properties-label.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/label")

### label Type

`string`

## allowlist



`allowlist`

* is required

* Type: `string[]`

* cannot be null

* defined in: [update-key output](update-key-output-properties-allowlist.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/allowlist")

### allowlist Type

`string[]`

## expires



`expires`

* is required

* Type: `string`

* can be null

* defined in: [update-key output](update-key-output-properties-expires.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/expires")

### expires Type

`string`

## created



`created`

* is required

* Type: `string`

* can be null

* defined in: [update-key output](update-key-output-properties-created.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/created")

### created Type

`string`

## last_used



`last_used`

* is required

* Type: `string`

* can be null

* defined in: [update-key output](update-key-output-properties-last_used.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/last_used")

### last_used Type

`string`

## status



`status`

* is required

* Type: unknown

* cannot be null

* defined in: [update-key output](update-key-output-properties-status.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/status")

### status Type

unknown

### status Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value       | Explanation |    |    |
| :---------- | :---------- | :- | :- |
| `"active"`  |             |
| `"expired"` |             |
| `"revoked"` |             |

## revoked

When the key was revoked

`revoked`

* is optional

* Type: `string`

* can be null

* defined in: [update-key output](update-key-output-properties-revoked.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/revoked")

### revoked Type

`string`

## revoked_reason

revoked: by an administrator or the API; plain_http: sent over plain HTTP

`revoked_reason`

* is optional

* Type: unknown

* cannot be null

* defined in: [update-key output](update-key-output-properties-revoked_reason.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/revoked_reason")

### revoked_reason Type

unknown

### revoked_reason Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value          | Explanation |    |    |
| :------------- | :---------- | :- | :- |
| `"revoked"`    |             |
| `"plain_http"` |             |
| `null`         |             |

## restrict



`restrict`

* is required

* Type: `object` ([Details](update-key-output-properties-restrict.md))

* can be null

* defined in: [update-key output](update-key-output-properties-restrict.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/restrict")

### restrict Type

`object` ([Details](update-key-output-properties-restrict.md))

## modified

When the label, allowed addresses or expiry were last changed

`modified`

* is optional

* Type: `string`

* can be null

* defined in: [update-key output](update-key-output-properties-modified.md "http://schema.nethserver.org/dnsapi/update-key-output.json#/properties/modified")

### modified Type

`string`
