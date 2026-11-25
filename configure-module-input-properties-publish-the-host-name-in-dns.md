# Publish the host name in DNS Schema

```txt
http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/publish_host_record
```

When the host name is in a zone dnshelper manages and its rules let dnsapi write it, add a CNAME from the host name to this node if there is none. Another record at the name is never changed. Default true.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [configure-module-input.json\*](dnsapi/configure-module-input.json "open original schema") |

## publish_host_record Type

`boolean` ([Publish the host name in DNS](configure-module-input-properties-publish-the-host-name-in-dns.md))
