# revoke-exposed-key input Schema

```txt
http://schema.nethserver.org/dnsapi/revoke-exposed-key-input.json
```

Delete an API key, operator keys included, because it was sent over plain HTTP. The API service calls it after checking the whole key; an administrator uses revoke-key.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                   |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [revoke-exposed-key-input.json](dnsapi/revoke-exposed-key-input.json "open original schema") |

## revoke-exposed-key input Type

`object` ([revoke-exposed-key input](revoke-exposed-key-input.md))

## revoke-exposed-key input Examples

```json
{
  "id": "a1b2c3d4",
  "address": "203.0.113.10"
}
```

# revoke-exposed-key input Properties

| Property            | Type     | Required | Nullable       | Defined by                                                                                                                                                         |
| :------------------ | :------- | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id)           | `string` | Required | cannot be null | [revoke-exposed-key input](revoke-exposed-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/revoke-exposed-key-input.json#/properties/id")           |
| [address](#address) | `string` | Optional | cannot be null | [revoke-exposed-key input](revoke-exposed-key-input-properties-address.md "http://schema.nethserver.org/dnsapi/revoke-exposed-key-input.json#/properties/address") |

## id

Key id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [revoke-exposed-key input](revoke-exposed-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/revoke-exposed-key-input.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")

## address

The client address the key came from

`address`

* is optional

* Type: `string`

* cannot be null

* defined in: [revoke-exposed-key input](revoke-exposed-key-input-properties-address.md "http://schema.nethserver.org/dnsapi/revoke-exposed-key-input.json#/properties/address")

### address Type

`string`

### address Constraints

**maximum length**: the maximum number of characters for this string is: `64`
