# revoke-key input Schema

```txt
http://schema.nethserver.org/dnsapi/revoke-key-input.json
```

Delete an API key

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                   |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [revoke-key-input.json](dnsapi/revoke-key-input.json "open original schema") |

## revoke-key input Type

`object` ([revoke-key input](revoke-key-input.md))

## revoke-key input Examples

```json
{
  "id": "a1b2c3d4"
}
```

# revoke-key input Properties

| Property  | Type     | Required | Nullable       | Defined by                                                                                                                       |
| :-------- | :------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| [id](#id) | `string` | Required | cannot be null | [revoke-key input](revoke-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/revoke-key-input.json#/properties/id") |

## id

Key id

`id`

* is required

* Type: `string`

* cannot be null

* defined in: [revoke-key input](revoke-key-input-properties-id.md "http://schema.nethserver.org/dnsapi/revoke-key-input.json#/properties/id")

### id Type

`string`

### id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[0-9a-f]{8}$
```

[try pattern](https://regexr.com/?expression=%5E%5B0-9a-f%5D%7B8%7D%24 "try regular expression with regexr.com")
