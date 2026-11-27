# Untitled object in list-assignable-zones output Schema

```txt
http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                             |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-assignable-zones-output.json\*](dnsapi/list-assignable-zones-output.json "open original schema") |

## items Type

`object` ([Details](list-assignable-zones-output-properties-zones-items.md))

# items Properties

| Property              | Type      | Required | Nullable       | Defined by                                                                                                                                                                                                                     |
| :-------------------- | :-------- | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [zone](#zone)         | `string`  | Required | cannot be null | [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-zone.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/zone")         |
| [provider](#provider) | `string`  | Required | can be null    | [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-provider.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/provider") |
| [tenant](#tenant)     | `string`  | Required | can be null    | [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-tenant.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/tenant")     |
| [full](#full)         | `boolean` | Required | cannot be null | [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-full.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/full")         |
| [hosted](#hosted)     | `boolean` | Optional | cannot be null | [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-hosted.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/hosted")     |

## zone



`zone`

* is required

* Type: `string`

* cannot be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-zone.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/zone")

### zone Type

`string`

## provider



`provider`

* is required

* Type: `string`

* can be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-provider.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/provider")

### provider Type

`string`

## tenant



`tenant`

* is required

* Type: `string`

* can be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-tenant.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/tenant")

### tenant Type

`string`

## full

dnsapi may write every record (a hosting customer's zone); false: only what dnshelper's rule allows, such as ACME challenges

`full`

* is required

* Type: `boolean`

* cannot be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-full.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/full")

### full Type

`boolean`

## hosted

Whether the zone was added through the API (POST /v1/zones) with the customer's credentials

`hosted`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-zones-items-properties-hosted.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/hosted")

### hosted Type

`boolean`
