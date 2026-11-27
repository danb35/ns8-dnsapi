# Untitled object in create-key input Schema

```txt
http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [create-key-input.json\*](dnsapi/create-key-input.json "open original schema") |

## 2 Type

`object` ([Details](create-key-input-properties-restrict-oneof-2.md))

# 2 Properties

| Property        | Type    | Required | Nullable       | Defined by                                                                                                                                                                                     |
| :-------------- | :------ | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [names](#names) | `array` | Required | cannot be null | [create-key input](create-key-input-properties-restrict-oneof-2-properties-names.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2/properties/names") |
| [types](#types) | `array` | Optional | cannot be null | [create-key input](create-key-input-properties-restrict-oneof-2-properties-types.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2/properties/types") |

## names



`names`

* is required

* Type: `string[]`

* cannot be null

* defined in: [create-key input](create-key-input-properties-restrict-oneof-2-properties-names.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2/properties/names")

### names Type

`string[]`

### names Constraints

**maximum number of items**: the maximum number of items for this array is: `20`

**minimum number of items**: the minimum number of items for this array is: `1`

## types



`types`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [create-key input](create-key-input-properties-restrict-oneof-2-properties-types.md "http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2/properties/types")

### types Type

`string[]`

### types Constraints

**maximum number of items**: the maximum number of items for this array is: `20`

**minimum number of items**: the minimum number of items for this array is: `1`
