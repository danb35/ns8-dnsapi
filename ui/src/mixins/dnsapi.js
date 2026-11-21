//
// Copyright (C) 2026 Dan Brown
// SPDX-License-Identifier: GPL-3.0-or-later
//
// One promise-returning call for NS8 tasks, as in ns8-automx and
// ns8-dnshelper:
//
//   const output = await this.callAction("list-tenants");
//
// Rejects with { kind, errors, message }:
//   - kind "validation": the action refused the input; errors is the NS8
//     list of { field, parameter, value, error, message? }
//   - kind "aborted": the task failed
//   - kind "request": the task could not even be created
// errorText(err) gives a translated message, fieldError(err, field) one
// field's message.
//
// newKey() makes an API key in the browser (DESIGN.md, Module plumbing: no
// key secret is stored anywhere): only its id and SHA-256 are sent to the
// create-key action, and the key is shown once.
import to from "await-to-js";
import { TaskService, UtilService } from "@nethserver/ns8-ui-lib";

const BASE32 = "abcdefghijklmnopqrstuvwxyz234567";

function base32(bytes) {
  // RFC 4648, lowercase, no padding: the same as the service's keys.py
  let bits = 0;
  let value = 0;
  let out = "";
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += BASE32[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) {
    out += BASE32[(value << (5 - bits)) & 31];
  }
  return out;
}

function hex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  name: "DnsapiService",
  mixins: [TaskService, UtilService],
  methods: {
    callAction(action, { data, title } = {}) {
      return new Promise((resolve, reject) => {
        const eventId = this.getUuid();
        const root = this.$store.state.core.$root;
        const events = ["completed", "aborted", "validation-failed"].map(
          (name) => `${action}-${name}-${eventId}`
        );
        const done = () => events.forEach((e) => root.$off(e));

        root.$once(events[0], (taskContext, taskResult) => {
          done();
          resolve(taskResult.output);
        });
        root.$once(events[1], (taskResult) => {
          done();
          console.error(`${action} aborted`, taskResult);
          reject({ kind: "aborted", errors: [], message: "" });
        });
        root.$once(events[2], (validationErrors) => {
          done();
          reject({ kind: "validation", errors: validationErrors, message: "" });
        });

        const task = {
          action,
          extra: {
            title: title || this.$t("action." + action),
            isNotificationHidden: true,
            eventId,
          },
        };
        if (data !== undefined) {
          task.data = data;
        }
        to(
          this.createModuleTaskForApp(this.$store.state.instanceName, task)
        ).then(([err]) => {
          if (err) {
            done();
            reject({
              kind: "request",
              errors: [],
              message: this.getErrorMessage(err),
            });
          }
        });
      });
    },

    /** A translated, human readable message for a rejection of callAction. */
    errorText(err) {
      if (err && err.kind === "validation" && err.errors.length) {
        return err.errors.map((e) => this.validationText(e)).join(" ");
      }
      if (err && err.kind === "request") {
        return err.message;
      }
      return this.$t("error.generic_error");
    },

    validationText(e) {
      const key = "error." + e.error;
      const text = this.$te(key) ? this.$t(key) : e.error;
      return e.message && !this.$te(key) ? `${text} (${e.message})` : text;
    },

    /** The first validation error for a field, or "" */
    fieldError(err, field) {
      if (!err || err.kind !== "validation") {
        return "";
      }
      const e = err.errors.find(
        (x) => x.parameter === field || x.field === field
      );
      return e ? this.validationText(e) : "";
    },

    /** A new API key: { id, key, hash }. Needs a secure context (HTTPS). */
    async newKey() {
      const idBytes = new Uint8Array(4);
      const secretBytes = new Uint8Array(32);
      window.crypto.getRandomValues(idBytes);
      window.crypto.getRandomValues(secretBytes);
      const id = hex(idBytes);
      const key = `dnsapi_${id}_${base32(secretBytes)}`;
      const digest = await window.crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(key)
      );
      return { id, key, hash: hex(new Uint8Array(digest)) };
    },

    tenantName(tenants, owner) {
      if (owner === "operator") {
        return this.$t("keys.operator");
      }
      const tenant = tenants.find((t) => t.id === owner);
      return tenant ? tenant.name : owner;
    },
  },
};
