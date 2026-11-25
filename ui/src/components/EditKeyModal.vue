<!--
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later

  Change a key's label, allowed addresses or expiry (update-key). What the
  key can reach (owner, access, records) is fixed and shown read-only: a key
  that should reach more is a new key (DESIGN.md, Concepts). Only the fields
  that changed are sent.
-->
<template>
  <NsModal
    size="default"
    :visible="isShown"
    :primary-button-disabled="loading"
    :isLoading="loading"
    @modal-hidden="$emit('hide')"
    @primary-click="save"
  >
    <template slot="title">{{ $t("keys.edit_title") }}</template>
    <template slot="content">
      <cv-form v-if="keyRecord" @submit.prevent="save">
        <div class="fixed mg-bottom-md">
          <div class="fixed-row">
            <span class="fixed-name">{{ $t("keys.col_label") }}</span>
            <span class="mono">dnsapi_{{ keyRecord.id }}_…</span>
          </div>
          <div class="fixed-row">
            <span class="fixed-name">{{ $t("keys.owner") }}</span>
            <span>{{ ownerName }}</span>
          </div>
          <div class="fixed-row">
            <span class="fixed-name">{{ $t("keys.scope") }}</span>
            <span>
              {{ $t("keys.scope_" + keyRecord.scope) }}
              <template v-if="restrictText">, {{ restrictText }}</template>
            </span>
          </div>
          <p class="secondary">{{ $t("keys.edit_fixed") }}</p>
        </div>
        <NsInlineNotification
          v-if="isExpired"
          kind="info"
          :title="$t('keys.edit_expired_title')"
          :description="$t('keys.edit_expired_description')"
          :showCloseButton="false"
          class="mg-bottom-md"
        />
        <NsTextInput
          v-model.trim="label"
          :label="$t('keys.label')"
          :helper-text="$t('keys.label_helper')"
          :invalid-message="error.label"
          :disabled="loading"
          class="mg-bottom-md"
        />
        <cv-text-area
          v-model="allowlist"
          :label="$t('keys.allowlist')"
          :helper-text="$t('keys.allowlist_helper')"
          :invalid-message="error.allowlist"
          placeholder="203.0.113.10, 198.51.100.0/24"
          :disabled="loading"
          class="mg-bottom-md"
        />
        <NsTextInput
          v-model.trim="expires"
          type="date"
          :label="$t('keys.expires')"
          :helper-text="$t('keys.edit_expires_helper')"
          :invalid-message="error.expires"
          :disabled="loading"
          class="mg-bottom-md"
        />
        <NsInlineNotification
          v-if="error.save"
          kind="error"
          :title="$t('action.update-key')"
          :description="error.save"
          :showCloseButton="false"
        />
      </cv-form>
    </template>
    <template slot="secondary-button">{{ core.$t("common.cancel") }}</template>
    <template slot="primary-button">{{ $t("keys.save") }}</template>
  </NsModal>
</template>

<script>
import { mapState } from "vuex";
import { UtilService } from "@nethserver/ns8-ui-lib";
import DnsapiService from "../mixins/dnsapi";

const UTC_DAY = /^(\d{4}-\d{2}-\d{2})T00:00(:00)?(\.0+)?(Z|\+00:00)$/;

function splitList(text) {
  return [...new Set(text.split(/[\s,]+/).filter((x) => x))];
}

export default {
  name: "EditKeyModal",
  mixins: [DnsapiService, UtilService],
  props: {
    isShown: { type: Boolean, default: false },
    keyRecord: { type: Object, default: null },
    tenants: { type: Array, default: () => [] },
  },
  data() {
    return {
      label: "",
      allowlist: "",
      expires: "",
      initial: { label: "", allowlist: [], expires: "" },
      loading: false,
      error: { label: "", allowlist: "", expires: "", save: "" },
    };
  },
  computed: {
    ...mapState(["core"]),
    ownerName() {
      return this.tenantName(this.tenants, this.keyRecord.owner);
    },
    restrictText() {
      const restrict = this.keyRecord.restrict;
      if (!restrict) {
        return "";
      }
      const acme =
        restrict.names.join(",") === "_acme-challenge,_acme-challenge.*" &&
        restrict.types.join(",") === "TXT";
      return acme
        ? this.$t("keys.restrict_acme_tag")
        : `${restrict.names.join(", ")} (${restrict.types.join(", ")})`;
    },
    isExpired() {
      const expires = this.keyRecord && this.keyRecord.expires;
      return !!expires && new Date(expires) <= new Date();
    },
  },
  watch: {
    isShown(shown) {
      if (shown && this.keyRecord) {
        Object.assign(this.$data, this.$options.data.call(this));
        const record = this.keyRecord;
        // The date field holds a day; a key set to expire at another time
        // (through the API) shows its day, and keeps its time unless changed.
        const match = record.expires ? UTC_DAY.exec(record.expires) : null;
        const day = record.expires
          ? match
            ? match[1]
            : record.expires.slice(0, 10)
          : "";
        this.initial = {
          label: record.label || "",
          allowlist: record.allowlist || [],
          expires: day,
        };
        this.label = this.initial.label;
        this.allowlist = this.initial.allowlist.join("\n");
        this.expires = day;
      }
    },
  },
  methods: {
    changes() {
      const data = {};
      if (this.label !== this.initial.label) {
        data.label = this.label;
      }
      const allowlist = splitList(this.allowlist);
      if (allowlist.join(",") !== this.initial.allowlist.join(",")) {
        data.allowlist = allowlist;
      }
      if (this.expires !== this.initial.expires) {
        data.expires = this.expires ? `${this.expires}T00:00:00Z` : null;
      }
      return data;
    },
    async save() {
      this.error = { label: "", allowlist: "", expires: "", save: "" };
      const data = this.changes();
      if (!Object.keys(data).length) {
        this.$emit("hide");
        return;
      }
      this.loading = true;
      try {
        await this.callAction("update-key", {
          data: { id: this.keyRecord.id, ...data },
        });
        this.$emit("updated");
        this.$emit("hide");
      } catch (err) {
        for (const field of ["label", "allowlist", "expires"]) {
          this.error[field] = this.fieldError(err, field);
        }
        this.error.save = this.errorText(err);
      }
      this.loading = false;
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";

.fixed-row {
  display: flex;
  gap: $spacing-05;
  margin-bottom: $spacing-02;
}

.fixed-name {
  min-width: 6rem;
  color: $text-02;
}

.mono {
  font-family: "IBM Plex Mono", "Menlo", "Courier New", monospace;
}

.secondary {
  color: $text-02;
  font-size: 0.75rem;
  margin-top: $spacing-03;
}
</style>
