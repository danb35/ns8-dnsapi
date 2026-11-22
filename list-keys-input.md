# list-keys input Schema

```txt
http://schema.nethserver.org/dnsapi/list-keys-input.json
```

The keys, optionally of one owner

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                 |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [list-keys-input.json](dnsapi/list-keys-input.json "open original schema") |

## list-keys input Type

`object` ([list-keys input](list-keys-input.md))

## list-keys input Examples

```json
{}
```

```json
{
  "owner": "operator"
}
```

# list-keys input Properties

| Property        | Type     | Required | Nullable       | Defined by                                                                                                                          |
| :-------------- | :------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| [owner](#owner) | `string` | Optional | cannot be null | [list-keys input](list-keys-input-properties-owner.md "http://schema.nethserver.org/dnsapi/list-keys-input.json#/properties/owner") |

## owner



`owner`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-keys input](list-keys-input-properties-owner.md "http://schema.nethserver.org/dnsapi/list-keys-input.json#/properties/owner")

### owner Type

`string`

### owner Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^(operator|t[0-9a-f]{8})$
```

[try pattern](https://regexr.com/?expression=%5E\(operator%7Ct%5B0-9a-f%5D%7B8%7D\)%24 "try regular expression with regexr.com")
