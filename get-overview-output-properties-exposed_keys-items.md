# Untitled object in get-overview output Schema

```txt
http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                           |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [get-overview-output.json\*](dnsapi/get-overview-output.json "open original schema") |

## items Type

`object` ([Details](get-overview-output-properties-exposed_keys-items.md))

# items Properties

| Property                    | Type     | Required | Nullable       | Defined by                                                                                                                                                                                                              |
| :-------------------------- | :------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [time](#time)               | `string` | Required | cannot be null | [get-overview output](get-overview-output-properties-exposed_keys-items-properties-time.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/time")               |
| [key](#key)                 | `string` | Required | cannot be null | [get-overview output](get-overview-output-properties-exposed_keys-items-properties-key.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/key")                 |
| [owner](#owner)             | `string` | Required | cannot be null | [get-overview output](get-overview-output-properties-exposed_keys-items-properties-owner.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/owner")             |
| [address](#address)         | `string` | Required | cannot be null | [get-overview output](get-overview-output-properties-exposed_keys-items-properties-address.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/address")         |
| [tenant_name](#tenant_name) | `string` | Required | cannot be null | [get-overview output](get-overview-output-properties-exposed_keys-items-properties-tenant_name.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/tenant_name") |

## time



`time`

* is required

* Type: `string`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-exposed_keys-items-properties-time.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/time")

### time Type

`string`

## key



`key`

* is required

* Type: `string`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-exposed_keys-items-properties-key.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/key")

### key Type

`string`

## owner

operator, or the tenant id

`owner`

* is required

* Type: `string`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-exposed_keys-items-properties-owner.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/owner")

### owner Type

`string`

## address



`address`

* is required

* Type: `string`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-exposed_keys-items-properties-address.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/address")

### address Type

`string`

## tenant_name

The tenant's name; empty for an operator key

`tenant_name`

* is required

* Type: `string`

* cannot be null

* defined in: [get-overview output](get-overview-output-properties-exposed_keys-items-properties-tenant_name.md "http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/exposed_keys/items/properties/tenant_name")

### tenant_name Type

`string`
