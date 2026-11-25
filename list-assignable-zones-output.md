# list-assignable-zones output Schema

```txt
http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json
```

The zones dnshelper lets dnsapi write in, with the tenant each belongs to. 'error' says why the list is empty: dnshelper_missing, dnshelper_too_old, or unavailable

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                           |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-assignable-zones-output.json](dnsapi/list-assignable-zones-output.json "open original schema") |

## list-assignable-zones output Type

`object` ([list-assignable-zones output](list-assignable-zones-output.md))

## list-assignable-zones output Examples

```json
{
  "dnshelper": "dnshelper1",
  "error": null,
  "zones": [
    {
      "zone": "example.com",
      "provider": "cloudflare",
      "tenant": "t1a2b3c4d",
      "full": true
    }
  ]
}
```

# list-assignable-zones output Properties

| Property                | Type     | Required | Nullable       | Defined by                                                                                                                                                                         |
| :---------------------- | :------- | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [dnshelper](#dnshelper) | `string` | Required | can be null    | [list-assignable-zones output](list-assignable-zones-output-properties-dnshelper.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/dnshelper") |
| [error](#error)         | `string` | Required | can be null    | [list-assignable-zones output](list-assignable-zones-output-properties-error.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/error")         |
| [zones](#zones)         | `array`  | Required | cannot be null | [list-assignable-zones output](list-assignable-zones-output-properties-zones.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones")         |

## dnshelper

The dnshelper instance used

`dnshelper`

* is required

* Type: `string`

* can be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-dnshelper.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/dnshelper")

### dnshelper Type

`string`

## error



`error`

* is required

* Type: `string`

* can be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-error.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/error")

### error Type

`string`

## zones



`zones`

* is required

* Type: `object[]` ([Details](list-assignable-zones-output-properties-zones-items.md))

* cannot be null

* defined in: [list-assignable-zones output](list-assignable-zones-output-properties-zones.md "http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones")

### zones Type

`object[]` ([Details](list-assignable-zones-output-properties-zones-items.md))
