#!/usr/bin/env python3
#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Writes dnsapi_server/openapi.json, the document the service serves at
# /v1/openapi.json. Run it after changing the API:
#
#   cd server && python3 make_openapi.py
#
# tests/test_app.py checks that every route of api.ROUTES is in it.

import json
import os

ERR = {"$ref": "#/components/responses/Error"}


def body(schema_ref):
    return {"required": True, "content": {"application/json": {"schema": {"$ref": schema_ref}}}}


def ok(schema_ref, description="OK", status="200"):
    return {status: {"description": description,
                     "content": {"application/json": {"schema": {"$ref": schema_ref}}}}}


def errors(*codes):
    return {str(c): ERR for c in codes}


ZONE_P = {"name": "zone", "in": "path", "required": True, "schema": {"type": "string"},
          "description": "A zone managed by dnshelper, like example.com"}
TENANT_P = {"name": "id", "in": "path", "required": True, "schema": {"type": "string", "pattern": "^t[0-9a-f]{8}$"}}
KEY_P = {"name": "key_id", "in": "path", "required": True, "schema": {"type": "string", "pattern": "^[0-9a-f]{8}$"}}

COMMON_ERRORS = errors(401, 403, 429)
ZONE_ERRORS = errors(401, 403, 404, 429, 502, 503, 504)
CHANGE_ERRORS = errors(400, 401, 403, 404, 409, 413, 429, 502, 503, 504)

record = {
    "type": "object",
    "required": ["name", "type", "data"],
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "description": "Relative to the zone; @ for the apex", "examples": ["www"]},
        "type": {"type": "string", "pattern": "^[A-Za-z0-9]{1,10}$", "examples": ["A"]},
        "ttl": {"type": "integer", "minimum": 0, "description": "Seconds; 0 or absent lets the DNS host choose"},
        "data": {"type": "string", "description": "Zone-file form without quotes: TXT is one plain string, MX \"10 mail.example.com.\", SRV \"priority weight port target\"",
                 "examples": ["192.0.2.1"]},
    },
}
match = {**record, "required": ["name"],
         "description": "A record to delete: a type, ttl or data left out matches anything"}

doc = {
    "openapi": "3.1.0",
    "info": {
        "title": "dnsapi",
        "version": "1",
        "description": "DNS records through NethServer 8's dnshelper, for billing and client portals, customers' scripts and ACME DNS-01 clients. A tenant key reaches only its tenant's zones and gets 404 for any other zone. Every call that reaches the DNS host counts against the key's rate limit, and may take as long as the host does: allow 60 s.",
        "license": {"name": "GPL-3.0-or-later"},
    },
    "servers": [{"url": "/"}],
    "security": [{"bearer": []}],
    "paths": {
        "/v1/status": {"get": {"summary": "Liveness", "security": [], "tags": ["service"],
                               "responses": ok("#/components/schemas/Status")}},
        "/v1/openapi.json": {"get": {"summary": "This document", "security": [], "tags": ["service"],
                                     "responses": {"200": {"description": "OpenAPI 3.1"}}}},
        "/v1/zones": {"get": {
            "summary": "The key's zones",
            "description": "An operator key gets every zone dnsapi may use, with its tenant; a tenant key its own zones.",
            "tags": ["zones"], "responses": {**ok("#/components/schemas/ZoneList"), **ZONE_ERRORS}}},
        "/v1/zones/{zone}/records": {
            "parameters": [ZONE_P],
            "get": {"summary": "Read records", "tags": ["records"],
                    "parameters": [{"name": "name", "in": "query", "schema": {"type": "string"}},
                                   {"name": "type", "in": "query", "schema": {"type": "string"}}],
                    "responses": {**ok("#/components/schemas/RecordList"), **ZONE_ERRORS}},
            "post": {"summary": "Add records", "description": "Never removes any record; adding one that exists is not an error.",
                     "tags": ["records"], "requestBody": body("#/components/schemas/RecordsRequest"),
                     "responses": {**ok("#/components/schemas/ChangeResult"), **CHANGE_ERRORS}},
            "delete": {"summary": "Delete matching records", "tags": ["records"],
                       "requestBody": body("#/components/schemas/DeleteRequest"),
                       "responses": {**ok("#/components/schemas/ChangeResult"), **CHANGE_ERRORS}},
        },
        "/v1/zones/{zone}/changes": {
            "parameters": [ZONE_P],
            "post": {"summary": "Remove exact records and add others as one change",
                     "description": "Refused as a whole with 409 stale if a record to remove is no longer there. An edit is one remove plus one add.",
                     "tags": ["records"], "requestBody": body("#/components/schemas/ChangesRequest"),
                     "responses": {**ok("#/components/schemas/ChangeResult"), **CHANGE_ERRORS}}},
        "/v1/zones/{zone}/rrsets": {
            "parameters": [ZONE_P],
            "put": {"summary": "Make the given records the only ones of each name and type",
                    "tags": ["records"], "requestBody": body("#/components/schemas/RecordsRequest"),
                    "responses": {**ok("#/components/schemas/ChangeResult"), **CHANGE_ERRORS}}},
        "/v1/zones/{zone}/propagation": {
            "parameters": [ZONE_P],
            "get": {"summary": "What the zone's name servers answer for one name and type",
                    "tags": ["records"],
                    "parameters": [{"name": "name", "in": "query", "required": True, "schema": {"type": "string"}},
                                   {"name": "type", "in": "query", "required": True, "schema": {"type": "string"}}],
                    "responses": {**ok("#/components/schemas/Propagation"), **ZONE_ERRORS}}},
        "/v1/acme/present": {"post": {
            "summary": "Add an ACME DNS-01 challenge",
            "description": "The protocol of lego's httpreq provider and acme.sh's acmeproxy. HTTP Basic authentication with the key as the password is accepted here. fqdn must start with _acme-challenge.; the zone is the longest of the key's zones containing it. The TXT value is added with TTL 60, beside any other.",
            "tags": ["acme"], "security": [{"bearer": []}, {"basic": []}],
            "requestBody": body("#/components/schemas/AcmeRequest"),
            "responses": {**ok("#/components/schemas/AcmeResult"), **CHANGE_ERRORS}}},
        "/v1/acme/cleanup": {"post": {
            "summary": "Remove an ACME DNS-01 challenge", "description": "Removes only that value.",
            "tags": ["acme"], "security": [{"bearer": []}, {"basic": []}],
            "requestBody": body("#/components/schemas/AcmeRequest"),
            "responses": {**ok("#/components/schemas/AcmeResult"), **CHANGE_ERRORS}}},
        "/v1/tenants": {
            "get": {"summary": "List tenants", "tags": ["tenants (operator)"],
                    "responses": {**ok("#/components/schemas/TenantList"), **COMMON_ERRORS}},
            "post": {"summary": "Add a tenant", "tags": ["tenants (operator)"],
                     "requestBody": body("#/components/schemas/TenantRequest"),
                     "responses": {**ok("#/components/schemas/Tenant", "Created", "201"), **errors(400, 401, 403, 429)}}},
        "/v1/tenants/{id}": {
            "parameters": [TENANT_P],
            "get": {"summary": "Read a tenant", "tags": ["tenants (operator)"],
                    "responses": {**ok("#/components/schemas/Tenant"), **errors(401, 403, 404, 429)}},
            "patch": {"summary": "Rename, enable or disable a tenant", "tags": ["tenants (operator)"],
                      "requestBody": body("#/components/schemas/TenantRequest"),
                      "responses": {**ok("#/components/schemas/Tenant"), **errors(400, 401, 403, 404, 429)}},
            "delete": {"summary": "Remove a tenant and its keys; its zones' records are not changed",
                       "tags": ["tenants (operator)"],
                       "responses": {"204": {"description": "Removed"}, **errors(401, 403, 404, 429)}}},
        "/v1/tenants/{id}/zones/{zone}": {
            "parameters": [TENANT_P, ZONE_P],
            "put": {"summary": "Assign a zone", "description": "409 zone_assigned if another tenant has it; 409 zone_not_assignable if dnshelper does not let dnsapi write in it.",
                    "tags": ["tenants (operator)"],
                    "responses": {**ok("#/components/schemas/Tenant"), **errors(401, 403, 404, 409, 429, 503)}},
            "delete": {"summary": "Unassign a zone", "tags": ["tenants (operator)"],
                       "responses": {"204": {"description": "Unassigned"}, **errors(401, 403, 404, 429)}}},
        "/v1/tenants/{id}/keys": {
            "parameters": [TENANT_P],
            "get": {"summary": "The tenant's keys", "tags": ["tenants (operator)"],
                    "responses": {**ok("#/components/schemas/KeyList"), **errors(401, 403, 404, 429)}},
            "post": {"summary": "Make a tenant key", "description": "The response is the only place the key appears.",
                     "tags": ["tenants (operator)"], "requestBody": body("#/components/schemas/KeyRequest"),
                     "responses": {**ok("#/components/schemas/NewKey", "Created", "201"), **errors(400, 401, 403, 404, 429)}}},
        "/v1/tenants/{id}/keys/{key_id}": {
            "parameters": [TENANT_P, KEY_P],
            "delete": {"summary": "Revoke a tenant key", "tags": ["tenants (operator)"],
                       "responses": {"204": {"description": "Revoked"}, **errors(401, 403, 404, 429)}}},
    },
    "components": {
        "securitySchemes": {
            "bearer": {"type": "http", "scheme": "bearer", "description": "dnsapi_<8 hex>_<52 base32>"},
            "basic": {"type": "http", "scheme": "basic", "description": "Only on /v1/acme/*: any user name, the key as the password"},
        },
        "responses": {"Error": {"description": "An error",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}},
        "schemas": {
            "Error": {"type": "object", "required": ["error"], "properties": {"error": {
                "type": "object", "required": ["code", "message", "field"],
                "properties": {"code": {"type": "string", "description": "invalid_request, invalid_json, missing_key, invalid_key, key_expired, insufficient_scope, tenant_disabled, address_not_allowed, restricted_key, outside_restriction, not_found, zone_not_found, tenant_not_found, key_not_found, stale, conflict, zone_assigned, zone_not_assignable, reserved_name, https_required, body_too_large, rate_limited, too_many_concurrent, busy, upstream_error, upstream_timeout, unavailable, dnshelper_missing, and dnshelper's own codes such as not_permitted and forbidden"},
                               "message": {"type": "string"}, "field": {"type": ["string", "null"]}}}}},
            "Status": {"type": "object", "properties": {"status": {"const": "ok"}}},
            "Record": {**record, "required": ["name", "type", "ttl", "data"],
                       "properties": {**record["properties"],
                                      "owned_by": {"type": "array", "items": {"type": "string"},
                                                   "description": "NS8 modules that wrote the record and may write it again"}}},
            "RecordInput": record,
            "RecordMatch": match,
            "Zone": {"type": "object", "required": ["zone", "provider", "full"],
                     "properties": {"zone": {"type": "string"}, "provider": {"type": ["string", "null"]},
                                    "full": {"type": "boolean", "description": "false: dnshelper lets dnsapi change only some records, such as ACME challenges"},
                                    "tenant": {"type": ["string", "null"], "description": "Operator keys only"}}},
            "ZoneList": {"type": "object", "properties": {"zones": {"type": "array", "items": {"$ref": "#/components/schemas/Zone"}}}},
            "RecordList": {"type": "object", "properties": {"zone": {"type": "string"},
                                                           "records": {"type": "array", "items": {"$ref": "#/components/schemas/Record"}}}},
            "RecordsRequest": {"type": "object", "required": ["records"],
                               "properties": {"records": {"type": "array", "minItems": 1, "maxItems": 100,
                                                          "items": {"$ref": "#/components/schemas/RecordInput"}},
                                              "dry_run": {"type": "boolean"}}},
            "DeleteRequest": {"type": "object", "required": ["records"],
                              "properties": {"records": {"type": "array", "minItems": 1, "maxItems": 100,
                                                         "items": {"$ref": "#/components/schemas/RecordMatch"}},
                                             "dry_run": {"type": "boolean"}}},
            "ChangesRequest": {"type": "object",
                               "properties": {"remove": {"type": "array", "items": {"$ref": "#/components/schemas/RecordInput"}},
                                              "add": {"type": "array", "items": {"$ref": "#/components/schemas/RecordInput"}},
                                              "dry_run": {"type": "boolean"}},
                               "description": "At most 100 records in all"},
            "Warning": {"type": "object", "properties": {
                "code": {"const": "owned_by_module"}, "record": {"$ref": "#/components/schemas/Record"},
                "modules": {"type": "array", "items": {"type": "string"}}, "message": {"type": "string"}}},
            "ChangeResult": {"type": "object", "required": ["zone", "dry_run", "changes", "warnings", "records"],
                             "properties": {"zone": {"type": "string"}, "dry_run": {"type": "boolean"},
                                            "changes": {"type": "object", "properties": {
                                                "add": {"type": "array", "items": {"$ref": "#/components/schemas/Record"}},
                                                "remove": {"type": "array", "items": {"$ref": "#/components/schemas/Record"}}}},
                                            "warnings": {"type": "array", "items": {"$ref": "#/components/schemas/Warning"}},
                                            "records": {"type": "array", "items": {"$ref": "#/components/schemas/Record"},
                                                        "description": "The zone's records after the change, as the DNS host reports them"}}},
            "Propagation": {"type": "object", "description": "dnshelper's check-propagation output",
                            "properties": {"zone": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"},
                                           "records": {"type": "array", "items": {"$ref": "#/components/schemas/Record"}},
                                           "servers_from": {"enum": ["dns", "provider"]},
                                           "servers": {"type": "array", "items": {"type": "object", "properties": {
                                               "server": {"type": "string"}, "address": {"type": "string"},
                                               "status": {"enum": ["same", "different", "error"]},
                                               "values": {"type": "array", "items": {"type": "string"}},
                                               "message": {"type": "string"}}}}}},
            "AcmeRequest": {"type": "object", "required": ["fqdn", "value"],
                            "properties": {"fqdn": {"type": "string", "examples": ["_acme-challenge.www.example.com."]},
                                           "value": {"type": "string", "maxLength": 255}}},
            "AcmeResult": {"type": "object", "properties": {"fqdn": {"type": "string"}, "value": {"type": "string"},
                                                           "zone": {"type": "string"},
                                                           "changes": {"$ref": "#/components/schemas/ChangeResult/properties/changes"}}},
            "Tenant": {"type": "object", "required": ["id", "name", "enabled", "zones", "created"],
                       "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "enabled": {"type": "boolean"},
                                      "zones": {"type": "array", "items": {"type": "string"}},
                                      "created": {"type": ["string", "null"], "format": "date-time"}}},
            "TenantList": {"type": "object", "properties": {"tenants": {"type": "array", "items": {"$ref": "#/components/schemas/Tenant"}}}},
            "TenantRequest": {"type": "object", "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 100},
                                                              "enabled": {"type": "boolean"}}},
            "Restrict": {"oneOf": [
                {"type": "null"}, {"const": "acme", "description": "_acme-challenge and _acme-challenge.* TXT records"},
                {"type": "object", "required": ["names"], "properties": {
                    "names": {"type": "array", "items": {"type": "string"}, "description": "Relative to the zone; * and ? are wildcards"},
                    "types": {"type": "array", "items": {"type": "string"}}}}]},
            "Key": {"type": "object", "properties": {
                "id": {"type": "string"}, "owner": {"type": "string"}, "scope": {"enum": ["read", "write"]},
                "label": {"type": "string"}, "allowlist": {"type": "array", "items": {"type": "string"}},
                "expires": {"type": ["string", "null"], "format": "date-time"},
                "restrict": {"type": ["object", "null"]},
                "created": {"type": ["string", "null"], "format": "date-time"},
                "last_used": {"type": ["string", "null"], "format": "date-time"}}},
            "KeyList": {"type": "object", "properties": {"keys": {"type": "array", "items": {"$ref": "#/components/schemas/Key"}}}},
            "KeyRequest": {"type": "object", "required": ["scope"], "properties": {
                "scope": {"enum": ["read", "write"]}, "label": {"type": "string", "maxLength": 100},
                "allowlist": {"type": "array", "items": {"type": "string"}, "description": "IP addresses or CIDR networks"},
                "expires": {"type": ["string", "null"], "format": "date-time"},
                "restrict": {"$ref": "#/components/schemas/Restrict"}}},
            "NewKey": {"allOf": [{"$ref": "#/components/schemas/Key"},
                                 {"type": "object", "required": ["key"], "properties": {"key": {"type": "string"}}}]},
        },
    },
}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dnsapi_server", "openapi.json")
with open(out, "w") as fp:
    json.dump(doc, fp, indent=1)
    fp.write("\n")
print("wrote", out)
