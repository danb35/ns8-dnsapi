# Untitled undefined type in get-configuration output Schema

```txt
http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record
```

The host name's CNAME to the node, as configure-module last found it; null before it has run

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [get-configuration-output.json\*](dnsapi/get-configuration-output.json "open original schema") |

## host_record Type

`object` ([Details](get-configuration-output-properties-host_record.md))

# host_record Properties

| Property                  | Type          | Required | Nullable       | Defined by                                                                                                                                                                                                             |
| :------------------------ | :------------ | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [host](#host)             | `string`      | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-host.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/host")             |
| [target](#target)         | `string`      | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-target.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/target")         |
| [zone](#zone)             | `string`      | Optional | can be null    | [get-configuration output](get-configuration-output-properties-host_record-properties-zone.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/zone")             |
| [status](#status)         | Not specified | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-status.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/status")         |
| [existing](#existing)     | `array`       | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-existing.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/existing")     |
| [propagated](#propagated) | `boolean`     | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-propagated.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/propagated") |
| [message](#message)       | `string`      | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-message.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/message")       |
| [checked](#checked)       | `string`      | Optional | cannot be null | [get-configuration output](get-configuration-output-properties-host_record-properties-checked.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/checked")       |

## host



`host`

* is optional

* Type: `string`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-host.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/host")

### host Type

`string`

## target



`target`

* is optional

* Type: `string`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-target.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/target")

### target Type

`string`

## zone



`zone`

* is optional

* Type: `string`

* can be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-zone.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/zone")

### zone Type

`string`

## status



`status`

* is optional

* Type: unknown

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-status.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/status")

### status Type

unknown

### status Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value             | Explanation |    |    |
| :---------------- | :---------- | :- | :- |
| `"ok"`            |             |
| `"created"`       |             |
| `"conflict"`      |             |
| `"not_managed"`   |             |
| `"not_permitted"` |             |
| `"apex"`          |             |
| `"disabled"`      |             |
| `"error"`         |             |

## existing

The records found at the name, as 'TYPE data'

`existing`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-existing.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/existing")

### existing Type

`string[]`

## propagated



`propagated`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-propagated.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/propagated")

### propagated Type

`boolean`

## message



`message`

* is optional

* Type: `string`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-message.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/message")

### message Type

`string`

## checked



`checked`

* is optional

* Type: `string`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host_record-properties-checked.md "http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/checked")

### checked Type

`string`
