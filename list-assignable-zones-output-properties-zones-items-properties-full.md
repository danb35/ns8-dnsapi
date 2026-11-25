# Untitled boolean in list-assignable-zones output Schema

```txt
http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items/properties/full
```

dnsapi may write every record (a hosting customer's zone); false: only what dnshelper's rule allows, such as ACME challenges

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                             |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [list-assignable-zones-output.json\*](dnsapi/list-assignable-zones-output.json "open original schema") |

## full Type

`boolean`
