# Untitled undefined type in create-key input Schema

```txt
http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict
```

Limit the key to some records: a preset ('acme': \_acme-challenge and \_acme-challenge.\* TXT records), or name patterns relative to the zone (\* and ? wildcards, as in dnshelper's rules) and record types; null for every record

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                     |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [create-key-input.json\*](dnsapi/create-key-input.json "open original schema") |

## restrict Type

merged type ([Details](create-key-input-properties-restrict.md))

one (and only one) of

* [Untitled null in create-key input](create-key-input-properties-restrict-oneof-0.md "check type definition")

* [Untitled string in create-key input](create-key-input-properties-restrict-oneof-1.md "check type definition")

* [Untitled object in create-key input](create-key-input-properties-restrict-oneof-2.md "check type definition")
