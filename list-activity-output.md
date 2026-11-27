# list-activity output Schema

```txt
http://schema.nethserver.org/dnsapi/list-activity-output.json
```

Changes, newest first. source 'api': made through the API (key, owner, address); source 'admin': made by an administrator through an action (caller); target_key: a key made or revoked

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                           |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-activity-output.json](dnsapi/list-activity-output.json "open original schema") |

## list-activity output Type

`object` ([list-activity output](list-activity-output.md))

## list-activity output Examples

```json
{
  "entries": [
    {
      "time": "2026-11-21T18:00:00Z",
      "source": "api",
      "key": "a1b2c3d4",
      "owner": "t1a2b3c4d",
      "tenant": "t1a2b3c4d",
      "address": "203.0.113.10",
      "action": "apply-changes",
      "zone": "example.com",
      "add": [
        "www A 192.0.2.2"
      ],
      "remove": [
        "www A 192.0.2.1"
      ],
      "result": "ok"
    }
  ]
}
```

# list-activity output Properties

| Property            | Type    | Required | Nullable       | Defined by                                                                                                                                             |
| :------------------ | :------ | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [entries](#entries) | `array` | Required | cannot be null | [list-activity output](list-activity-output-properties-entries.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries") |

## entries



`entries`

* is required

* Type: `object[]` ([Details](list-activity-output-properties-entries-items.md))

* cannot be null

* defined in: [list-activity output](list-activity-output-properties-entries.md "http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries")

### entries Type

`object[]` ([Details](list-activity-output-properties-entries-items.md))
