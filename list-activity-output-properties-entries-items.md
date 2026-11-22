# Untitled object in list-activity output Schema

```txt
http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                             |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-activity-output.json\*](dnsapi/list-activity-output.json "open original schema") |

## items Type

`object` ([Details](list-activity-output-properties-entries-items.md))

# items Properties

| Property                  | Type          | Required | Nullable       | Defined by                                                                                                                                                                                                     |
| :------------------------ | :------------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [time](#time)             | `string`      | Required | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-time.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/time")             |
| [source](#source)         | Not specified | Required | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-source.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/source")         |
| [action](#action)         | `string`      | Required | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-action.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/action")         |
| [result](#result)         | `string`      | Required | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-result.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/result")         |
| [key](#key)               | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-key.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/key")               |
| [owner](#owner)           | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-owner.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/owner")           |
| [caller](#caller)         | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-caller.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/caller")         |
| [tenant](#tenant)         | `string`      | Optional | can be null    | [list-activity output](list-activity-output-properties-entries-items-properties-tenant.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/tenant")         |
| [zone](#zone)             | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-zone.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/zone")             |
| [address](#address)       | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-address.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/address")       |
| [add](#add)               | `array`       | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-add.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/add")               |
| [remove](#remove)         | `array`       | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-remove.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/remove")         |
| [target_key](#target_key) | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-target_key.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/target_key") |
| [name](#name)             | `string`      | Optional | cannot be null | [list-activity output](list-activity-output-properties-entries-items-properties-name.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/name")             |

## time



`time`

* is required

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-time.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/time")

### time Type

`string`

## source



`source`

* is required

* Type: unknown

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-source.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/source")

### source Type

unknown

### source Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value     | Explanation |    |    |
| :-------- | :---------- | :- | :- |
| `"api"`   |             |
| `"admin"` |             |

## action



`action`

* is required

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-action.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/action")

### action Type

`string`

## result



`result`

* is required

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-result.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/result")

### result Type

`string`

## key



`key`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-key.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/key")

### key Type

`string`

## owner



`owner`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-owner.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/owner")

### owner Type

`string`

## caller



`caller`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-caller.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/caller")

### caller Type

`string`

## tenant



`tenant`

* is optional

* Type: `string`

* can be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-tenant.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/tenant")

### tenant Type

`string`

## zone



`zone`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-zone.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/zone")

### zone Type

`string`

## address



`address`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-address.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/address")

### address Type

`string`

## add



`add`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-add.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/add")

### add Type

`string[]`

## remove



`remove`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-remove.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/remove")

### remove Type

`string[]`

## target_key



`target_key`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-target_key.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/target_key")

### target_key Type

`string`

## name

The tenant's name, for tenant changes

`name`

* is optional

* Type: `string`

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries-items-properties-name.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/name")

### name Type

`string`
