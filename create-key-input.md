# create-key input Schema

```txt
http://schema.nethserver.org/dnsapi/create-key-input.json
```

Store an API key from its id and the SHA-256 (hex) of the whole key string 'dnsapi\_<id>\_<secret>', where secret is 32 random bytes in lowercase base32 without padding. The secret never reaches the action. From a shell, use bin/create-key instead

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                   |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [create-key-input.json](dnsapi/create-key-input.json "open original schema") |

## create-key input Type

`object` ([create-key input](create-key-input.md))

## create-key input Examples

```json
{
  "id": "a1b2c3d4",
  "hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "owner": "t1a2b3c4d",
  "scope": "write",
  "label": "Acme portal",
  "allowlist": [
    "203.0.113.10"
  ],
  "expires": null
}
```

```json
{
  "id": "b2c3d4e5",
  "hash": "1111111111111111111111111111111111111111111111111111111111111111",
  "owner": "t1a2b3c4d",
  "scope": "write",
  "label": "host1 certificates",
  "allowlist": [
    "10.0.0.5"
  ],
  "restrict": "acme"
}
```

# create-key input Properties

| Property                | Type          | Required | Nullable       | Defined by                                                                                                                                     |
| :---------------------- | :------------ | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)               | `string`      | Required | cannot be null | [create-key input](create-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/id")               |
| [hash](#hash)           | `string`      | Required | cannot be null | [create-key input](create-key-input-properties-hash.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/hash")           |
| [owner](#owner)         | `string`      | Required | cannot be null | [create-key input](create-key-input-properties-owner.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/owner")         |
| [scope](#scope)         | Not specified | Required | cannot be null | [create-key input](create-key-input-properties-scope.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/scope")         |
| [label](#label)         | `string`      | Optional | cannot be null | [create-key input](create-key-input-properties-label.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/label")         |
| [allowlist](#allowlist) | `array`       | Optional | cannot be null | [create-key input](create-key-input-properties-allowlist.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/allowlist") |
| [expires](#expires)     | `string`      | Optional | can be null    | [create-key input](create-key-input-properties-expires.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/expires")     |
| [restrict](#restrict)   | Merged        | Optional | cannot be null | [create-key input](create-key-input-properties-restrict.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict")   |

## id

Key id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [create-key input](create-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## hash



`hash`

* is required

* Type: `string`

* cannot be null

* defined in: [create-key input](create-key-input-properties-hash.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/hash")

### hash Type

`string`

### hash Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{64}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B64%7D%24 "try regular expression with regexr.com")

## owner



`owner`

* is required

* Type: `string`

* cannot be null

* defined in: [create-key input](create-key-input-properties-owner.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/owner")

### owner Type

`string`

### owner Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^(operator|t[0-9a-f]{8})$
```

[try pattern](https://regexr.com/?expression=%5E\(operator%7Ct%5B0-9a-f%5D%7B8%7D\)%24 "try regular expression with regexr.com")

## scope



`scope`

* is required

* Type: unknown

* cannot be null

* defined in: [create-key input](create-key-input-properties-scope.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/scope")

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

* is optional

* Type: `string`

* cannot be null

* defined in: [create-key input](create-key-input-properties-label.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/label")

### label Type

`string`

### label Constraints

**maximum length**: the maximum number of characters for this string is: `100`

## allowlist

IP addresses or CIDR networks the key may be used from; empty for any

`allowlist`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [create-key input](create-key-input-properties-allowlist.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/allowlist")

### allowlist Type

`string[]`

### allowlist Constraints

**maximum number of items**: the maximum number of items for this array is: `100`

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## expires

ISO 8601 date-time after which the key is refused; null for never

`expires`

* is optional

* Type: `string`

* can be null

* defined in: [create-key input](create-key-input-properties-expires.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/expires")

### expires Type

`string`

## restrict

Limit the key to some records: a preset ('acme': \_acme-challenge and \_acme-challenge.\* TXT records), or name patterns relative to the zone (\* and ? wildcards, as in dnshelper's rules) and record types; null for every record

`restrict`

* is optional

* Type: merged type ([Details](create-key-input-properties-restrict.md))

* cannot be null

* defined in: [create-key input](create-key-input-properties-restrict.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict")

### restrict Type

merged type ([Details](create-key-input-properties-restrict.md))

one (and only one) of

* [Untitled null in create-key input](create-key-input-properties-restrict-oneof-0.md "check type definition")

* [Untitled string in create-key input](create-key-input-properties-restrict-oneof-1.md "check type definition")

* [Untitled object in create-key input](create-key-input-properties-restrict-oneof-2.md "check type definition")
