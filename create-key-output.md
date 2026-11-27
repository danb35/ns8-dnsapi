# create-key output Schema

```txt
http://schema.nethserver.org/dnsapi/create-key-output.json
```

The key, without its hash

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [create-key-output.json](dnsapi/create-key-output.json "open original schema") |

## create-key output Type

`object` ([create-key output](create-key-output.md))

# create-key output Properties

| Property                | Type          | Required | Nullable       | Defined by                                                                                                                                        |
| :---------------------- | :------------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| [id](#id)               | `string`      | Required | cannot be null | [create-key output](create-key-output-properties-id.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/id")               |
| [owner](#owner)         | `string`      | Required | cannot be null | [create-key output](create-key-output-properties-owner.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/owner")         |
| [scope](#scope)         | Not specified | Required | cannot be null | [create-key output](create-key-output-properties-scope.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/scope")         |
| [label](#label)         | `string`      | Required | cannot be null | [create-key output](create-key-output-properties-label.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/label")         |
| [allowlist](#allowlist) | `array`       | Required | cannot be null | [create-key output](create-key-output-properties-allowlist.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/allowlist") |
| [expires](#expires)     | `string`      | Required | can be null    | [create-key output](create-key-output-properties-expires.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/expires")     |
| [created](#created)     | `string`      | Required | can be null    | [create-key output](create-key-output-properties-created.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/created")     |
| [last_used](#last_used) | `string`      | Required | can be null    | [create-key output](create-key-output-properties-last_used.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/last_used") |
| [restrict](#restrict)   | `object`      | Required | can be null    | [create-key output](create-key-output-properties-restrict.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/restrict")   |
| [modified](#modified)   | `string`      | Optional | can be null    | [create-key output](create-key-output-properties-modified.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/modified")   |

## id

Key id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [create-key output](create-key-output-properties-id.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/id")

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

* defined in: [create-key output](create-key-output-properties-owner.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/owner")

### owner Type

`string`

## scope



`scope`

* is required

* Type: unknown

* cannot be null

* defined in: [create-key output](create-key-output-properties-scope.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/scope")

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

* defined in: [create-key output](create-key-output-properties-label.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/label")

### label Type

`string`

## allowlist



`allowlist`

* is required

* Type: `string[]`

* cannot be null

* defined in: [create-key output](create-key-output-properties-allowlist.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/allowlist")

### allowlist Type

`string[]`

## expires



`expires`

* is required

* Type: `string`

* can be null

* defined in: [create-key output](create-key-output-properties-expires.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/expires")

### expires Type

`string`

## created



`created`

* is required

* Type: `string`

* can be null

* defined in: [create-key output](create-key-output-properties-created.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/created")

### created Type

`string`

## last_used



`last_used`

* is required

* Type: `string`

* can be null

* defined in: [create-key output](create-key-output-properties-last_used.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/last_used")

### last_used Type

`string`

## restrict



`restrict`

* is required

* Type: `object` ([Details](create-key-output-properties-restrict.md))

* can be null

* defined in: [create-key output](create-key-output-properties-restrict.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/restrict")

### restrict Type

`object` ([Details](create-key-output-properties-restrict.md))

## modified

When the label, allowed addresses or expiry were last changed

`modified`

* is optional

* Type: `string`

* can be null

* defined in: [create-key output](create-key-output-properties-modified.md "http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/modified")

### modified Type

`string`
