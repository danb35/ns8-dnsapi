# Data and privacy

dnsapi has no telemetry, and nothing is sent to its author.

dnsapi holds no DNS host credentials and never contacts a DNS host itself. It reads and changes
records only through the dnshelper module, so dnshelper's own
[data and privacy terms](https://github.com/danb35/ns8-dnshelper/blob/master/TERMS.md) also apply
to every record read or changed through the API.

## What goes where

| Data | Where it goes | When |
|---|---|---|
| API keys | From each client to the API, in the `Authorization` header, over HTTPS. The node keeps only a SHA-256 hash of each key; the key itself is shown once, when it is made, and is never stored, logged or kept in Redis | On every request |
| Zone names and DNS records (names, types, values, TTLs) | dnshelper, which passes them to the zone's DNS host. dnshelper records which customer and key made each change | When a client reads or changes records |
| DNS queries for one name and type | The zone's authoritative name servers, asked by dnshelper | When a client asks for `propagation`, and when the API's host name is published in DNS |
| The API's host name, and a CNAME from it to the node's host name | The DNS host of the zone that holds it, through dnshelper | When **Publish the host name in DNS** is on and dnshelper's access rules allow it |
| The API's host name | Let's Encrypt, which NS8's Traefik asks for a certificate | When a Let's Encrypt certificate is requested in Settings |
| Customers' names, zone assignments, and each key's owner, label, access, record restriction, allowed addresses, expiry and hash | Kept on the node, in files only the module can read (mode 0600), and in your backup destination, encrypted by NS8 | When you or a client using an operator key change them, and if you have configured backups |
| Client IP addresses, and when each key was last used | Kept on the node: failed sign-ins per address in memory for one minute, and last-used times in a file. Neither is backed up | On every request |
| Activity: date, key id, customer, client IP address, action, zone, records added and removed (in full), outcome | Kept on the node (the most recent 1000 to 2000 entries, not backed up), shown on the Activity page | On every change through the API or the admin UI |
| Audit log: the same as the activity, plus failed sign-ins and refused requests with the key id and client address. Never a key | NS8's log server, and any syslog server or Cloud Log Manager you forward logs to | On every change, and every refused request |

A client sees only the zones of its own customer, and only the records its key's restriction
allows. Clients never see dnshelper's credentials, its access rules, or another customer's data.

## How keys are stored

A key is a random 256-bit secret; dnsapi keeps only its SHA-256 hash, which cannot be turned back
into the key. A lost key cannot be shown again: revoke it and make a new one. A key that was sent
over plain HTTP is refused and, unless you turn that off in Settings, revoked at once, since
anyone on the network may have read it.

## Removing data

Revoking a key deletes it from the node at once, and the API refuses it from the next request.
Removing a customer deletes its keys and frees its zones. Neither touches any DNS record: records
a customer added stay at the DNS host until they are deleted there, through the API or on
dnshelper's Records page.

Older backups still contain revoked keys' hashes and removed customers. Restoring such a backup
brings them back, revoked keys included, so revoke them again after a restore.

Removing dnsapi deletes its data from the node, including the activity log. The CNAME it added
for its own host name is left in the zone; dnshelper's Records page lists it as dnsapi's.
