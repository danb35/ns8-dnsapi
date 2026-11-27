# list-tenants output Schema

```txt
http://schema.nethserver.org/dnsapi/list-tenants-output.json
```

Every tenant

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                         |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-tenants-output.json](dnsapi/list-tenants-output.json "open original schema") |

## list-tenants output Type

`object` ([list-tenants output](list-tenants-output.md))

## list-tenants output Examples

```json
{
  "tenants": [
    {
      "id": "t1a2b3c4d",
      "name": "Acme Ltd",
      "enabled": true,
      "zones": [
        "example.com"
      ],
      "created": "2026-11-21T18:00:00Z",
      "keys": 1
    }
  ]
}
```

# list-tenants output Properties

| Property            | Type    | Required | Nullable       | Defined by                                                                                                                                          |
| :------------------ | :------ | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| [tenants](#tenants) | `array` | Required | cannot be null | [list-tenants output](list-tenants-output-properties-tenants.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants") |

## tenants



`tenants`

* is required

* Type: `object[]` ([Details](list-tenants-output-properties-tenants-items.md))

* cannot be null

* defined in: [list-tenants output](list-tenants-output-properties-tenants.md "http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants")

### tenants Type

`object[]` ([Details](list-tenants-output-properties-tenants-items.md))
