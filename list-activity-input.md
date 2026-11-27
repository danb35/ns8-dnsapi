# list-activity input Schema

```txt
http://schema.nethserver.org/dnsapi/list-activity-input.json
```

The most recent changes; limit is the number of entries (default 200)

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                         |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [list-activity-input.json](dnsapi/list-activity-input.json "open original schema") |

## list-activity input Type

`object` ([list-activity input](list-activity-input.md))

## list-activity input Examples

```json
{}
```

```json
{
  "limit": 50
}
```

# list-activity input Properties

| Property        | Type      | Required | Nullable       | Defined by                                                                                                                                      |
| :-------------- | :-------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| [limit](#limit) | `integer` | Optional | cannot be null | [list-activity input](list-activity-input-properties-limit.md "http://schema.nethserver.org/dnsapi/list-activity-input.json#/properties/limit") |

## limit



`limit`

* is optional

* Type: `integer`

* cannot be null

* defined in: [list-activity input](list-activity-input-properties-limit.md "http://schema.nethserver.org/dnsapi/list-activity-input.json#/properties/limit")

### limit Type

`integer`

### limit Constraints

**maximum**: the value of this number must smaller than or equal to: `2000`

**minimum**: the value of this number must greater than or equal to: `1`
