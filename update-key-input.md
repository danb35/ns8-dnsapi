# update-key input Schema

```txt
http://schema.nethserver.org/dnsapi/update-key-input.json
```

Change an API key's label, allowed addresses or expiry; the fields left out keep their value. Owner, scope and restrict cannot be changed, nor can a revoked key

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                   |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [update-key-input.json](dnsapi/update-key-input.json "open original schema") |

## update-key input Type

`object` ([update-key input](update-key-input.md))

## update-key input Examples

```json
{
  "id": "a1b2c3d4",
  "allowlist": [
    "203.0.113.20"
  ]
}
```

```json
{
  "id": "b2c3d4e5",
  "label": "host1 certificates",
  "expires": "2027-12-31T00:00:00Z"
}
```

# update-key input Properties

| Property                | Type     | Required | Nullable       | Defined by                                                                                                                                     |
| :---------------------- | :------- | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)               | `string` | Required | cannot be null | [update-key input](update-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/id")               |
| [label](#label)         | `string` | Optional | cannot be null | [update-key input](update-key-input-properties-label.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/label")         |
| [allowlist](#allowlist) | `array`  | Optional | cannot be null | [update-key input](update-key-input-properties-allowlist.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/allowlist") |
| [expires](#expires)     | `string` | Optional | can be null    | [update-key input](update-key-input-properties-expires.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/expires")     |

## id

Key id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [update-key input](update-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## label



`label`

* is optional

* Type: `string`

* cannot be null

* defined in: [update-key input](update-key-input-properties-label.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/label")

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

* defined in: [update-key input](update-key-input-properties-allowlist.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/allowlist")

### allowlist Type

`string[]`

### allowlist Constraints

**maximum number of items**: the maximum number of items for this array is: `100`

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## expires

ISO 8601 date-time in the future after which the key is refused; null for never. An expired key given a later expiry works again

`expires`

* is optional

* Type: `string`

* can be null

* defined in: [update-key input](update-key-input-properties-expires.md "http://schema.nethserver.org/dnsapi/update-key-input.json#/properties/expires")

### expires Type

`string`
