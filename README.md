# README

## Top-level Schemas

* [add-tenant input](./add-tenant-input.md "Add a tenant") – `http://schema.nethserver.org/dnsapi/add-tenant-input.json`

* [add-tenant output](./add-tenant-output.md "The new tenant") – `http://schema.nethserver.org/dnsapi/add-tenant-output.json`

* [assign-zone input](./assign-zone-input.md "Give a zone to a tenant") – `http://schema.nethserver.org/dnsapi/assign-zone-input.json`

* [assign-zone output](./assign-zone-output.md "The tenant") – `http://schema.nethserver.org/dnsapi/assign-zone-output.json`

* [configure-module input](./configure-module-input.md "Configure dnsapi: the host name the API is published on, its certificate and HTTP redirect, the client addresses Traefik lets through, and the per-key rate limit") – `http://schema.nethserver.org/dnsapi/configure-module-input.json`

* [create-key input](./create-key-input.md "Store an API key from its id and the SHA-256 (hex) of the whole key string 'dnsapi_<id>_<secret>', where secret is 32 random bytes in lowercase base32 without padding") – `http://schema.nethserver.org/dnsapi/create-key-input.json`

* [create-key output](./create-key-output.md "The key, without its hash") – `http://schema.nethserver.org/dnsapi/create-key-output.json`

* [get-configuration output](./get-configuration-output.md "Get dnsapi configuration") – `http://schema.nethserver.org/dnsapi/get-configuration-output.json`

* [get-overview input](./get-overview-input.md "No input") – `http://schema.nethserver.org/dnsapi/get-overview-input.json`

* [get-overview output](./get-overview-output.md "What the Status page shows") – `http://schema.nethserver.org/dnsapi/get-overview-output.json`

* [list-activity input](./list-activity-input.md "The most recent changes; limit is the number of entries (default 200)") – `http://schema.nethserver.org/dnsapi/list-activity-input.json`

* [list-activity output](./list-activity-output.md "Changes, newest first") – `http://schema.nethserver.org/dnsapi/list-activity-output.json`

* [list-assignable-zones input](./list-assignable-zones-input.md "No input") – `http://schema.nethserver.org/dnsapi/list-assignable-zones-input.json`

* [list-assignable-zones output](./list-assignable-zones-output.md "The zones dnshelper lets dnsapi write in, with the tenant each belongs to") – `http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json`

* [list-keys input](./list-keys-input.md "The keys, optionally of one owner") – `http://schema.nethserver.org/dnsapi/list-keys-input.json`

* [list-keys output](./list-keys-output.md "The keys, without their hashes") – `http://schema.nethserver.org/dnsapi/list-keys-output.json`

* [list-tenants input](./list-tenants-input.md "No input") – `http://schema.nethserver.org/dnsapi/list-tenants-input.json`

* [list-tenants output](./list-tenants-output.md "Every tenant") – `http://schema.nethserver.org/dnsapi/list-tenants-output.json`

* [remove-tenant input](./remove-tenant-input.md "Remove a tenant, its zone assignments and its keys") – `http://schema.nethserver.org/dnsapi/remove-tenant-input.json`

* [revoke-key input](./revoke-key-input.md "Delete an API key") – `http://schema.nethserver.org/dnsapi/revoke-key-input.json`

* [unassign-zone input](./unassign-zone-input.md "Take a zone from a tenant; its records are not changed") – `http://schema.nethserver.org/dnsapi/unassign-zone-input.json`

* [unassign-zone output](./unassign-zone-output.md "The tenant") – `http://schema.nethserver.org/dnsapi/unassign-zone-output.json`

* [update-tenant input](./update-tenant-input.md "Rename, enable or disable a tenant") – `http://schema.nethserver.org/dnsapi/update-tenant-input.json`

* [update-tenant output](./update-tenant-output.md "The tenant") – `http://schema.nethserver.org/dnsapi/update-tenant-output.json`

## Other Schemas

### Objects

* [Untitled object in create-key input](./create-key-input-properties-restrict-oneof-2.md) – `http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2`

* [Untitled object in list-activity output](./list-activity-output-properties-entries-items.md) – `http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items`

* [Untitled object in list-assignable-zones output](./list-assignable-zones-output-properties-zones-items.md) – `http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones/items`

* [Untitled object in list-keys output](./list-keys-output-properties-keys-items.md) – `http://schema.nethserver.org/dnsapi/list-keys-output.json#/properties/keys/items`

* [Untitled object in list-tenants output](./list-tenants-output-properties-tenants-items.md) – `http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items`

### Arrays

* [Allowed client addresses](./configure-module-input-properties-allowed-client-addresses.md "IP addresses or CIDR networks that Traefik lets reach the API; every other client gets 403 from Traefik") – `http://schema.nethserver.org/dnsapi/configure-module-input.json#/properties/ip_allowlist`

* [Untitled array in add-tenant output](./add-tenant-output-properties-zones.md) – `http://schema.nethserver.org/dnsapi/add-tenant-output.json#/properties/zones`

* [Untitled array in assign-zone output](./assign-zone-output-properties-zones.md) – `http://schema.nethserver.org/dnsapi/assign-zone-output.json#/properties/zones`

* [Untitled array in create-key input](./create-key-input-properties-allowlist.md "IP addresses or CIDR networks the key may be used from; empty for any") – `http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/allowlist`

* [Untitled array in create-key input](./create-key-input-properties-restrict-oneof-2-properties-names.md) – `http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2/properties/names`

* [Untitled array in create-key input](./create-key-input-properties-restrict-oneof-2-properties-types.md) – `http://schema.nethserver.org/dnsapi/create-key-input.json#/properties/restrict/oneOf/2/properties/types`

* [Untitled array in create-key output](./create-key-output-properties-allowlist.md) – `http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/allowlist`

* [Untitled array in create-key output](./create-key-output-properties-restrict-properties-names.md) – `http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/restrict/properties/names`

* [Untitled array in create-key output](./create-key-output-properties-restrict-properties-types.md) – `http://schema.nethserver.org/dnsapi/create-key-output.json#/properties/restrict/properties/types`

* [Untitled array in get-configuration output](./get-configuration-output-properties-ip_allowlist.md) – `http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/ip_allowlist`

* [Untitled array in get-configuration output](./get-configuration-output-properties-host_record-properties-existing.md "The records found at the name, as 'TYPE data'") – `http://schema.nethserver.org/dnsapi/get-configuration-output.json#/properties/host_record/properties/existing`

* [Untitled array in get-overview output](./get-overview-output-properties-host_record-properties-existing.md "The records found at the name, as 'TYPE data'") – `http://schema.nethserver.org/dnsapi/get-overview-output.json#/properties/host_record/properties/existing`

* [Untitled array in list-activity output](./list-activity-output-properties-entries.md) – `http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries`

* [Untitled array in list-activity output](./list-activity-output-properties-entries-items-properties-add.md) – `http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/add`

* [Untitled array in list-activity output](./list-activity-output-properties-entries-items-properties-remove.md) – `http://schema.nethserver.org/dnsapi/list-activity-output.json#/properties/entries/items/properties/remove`

* [Untitled array in list-assignable-zones output](./list-assignable-zones-output-properties-zones.md) – `http://schema.nethserver.org/dnsapi/list-assignable-zones-output.json#/properties/zones`

* [Untitled array in list-keys output](./list-keys-output-properties-keys.md) – `http://schema.nethserver.org/dnsapi/list-keys-output.json#/properties/keys`

* [Untitled array in list-keys output](./list-keys-output-properties-keys-items-properties-allowlist.md) – `http://schema.nethserver.org/dnsapi/list-keys-output.json#/properties/keys/items/properties/allowlist`

* [Untitled array in list-keys output](./list-keys-output-properties-keys-items-properties-restrict-properties-names.md) – `http://schema.nethserver.org/dnsapi/list-keys-output.json#/properties/keys/items/properties/restrict/properties/names`

* [Untitled array in list-keys output](./list-keys-output-properties-keys-items-properties-restrict-properties-types.md) – `http://schema.nethserver.org/dnsapi/list-keys-output.json#/properties/keys/items/properties/restrict/properties/types`

* [Untitled array in list-tenants output](./list-tenants-output-properties-tenants.md) – `http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants`

* [Untitled array in list-tenants output](./list-tenants-output-properties-tenants-items-properties-zones.md) – `http://schema.nethserver.org/dnsapi/list-tenants-output.json#/properties/tenants/items/properties/zones`

* [Untitled array in unassign-zone output](./unassign-zone-output-properties-zones.md) – `http://schema.nethserver.org/dnsapi/unassign-zone-output.json#/properties/zones`

* [Untitled array in update-tenant output](./update-tenant-output-properties-zones.md) – `http://schema.nethserver.org/dnsapi/update-tenant-output.json#/properties/zones`

## Version Note

The schemas linked above follow the JSON Schema Spec version: `http://json-schema.org/draft-07/schema#`
