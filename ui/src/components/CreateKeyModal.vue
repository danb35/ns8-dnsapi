<!--
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later

  Make an API key. The key is made here, in the browser, and only its id
  and SHA-256 are sent to the create-key action (DESIGN.md: no key secret
  is stored anywhere). It is shown once, with a copy button.
-->
<template>
  <NsModal
    size="default"
    :visible="isShown"
    :primary-button-disabled="loading"
    :isLoading="loading"
    @modal-hidden="$emit('hide')"
    @primary-click="created ? $emit('hide') : save()"
  >
    <template slot="title">{{
      created ? $t("keys.created_title") : $t("keys.create_title")
    }}</template>
    <template slot="content">
      <template v-if="created">
        <NsInlineNotification
          kind="warning"
          :title="$t('keys.shown_once_title')"
          :description="$t('keys.shown_once_description')"
          :showCloseButton="false"
          class="mg-bottom-md"
        />
        <NsCodeSnippet
          :copyTooltip="core.$t('common.copy_to_clipboard')"
          :copy-feedback="core.$t('common.copied_to_clipboard')"
          :wrap-text="true"
          hideExpandButton
          class="mg-bottom-md"
          >{{ created.key }}</NsCodeSnippet
        >
        <p>{{ $t("keys.created_how", { url: shownUrl }) }}</p>
      </template>
      <cv-form v-else @submit.prevent="save">
        <NsComboBox
          v-model="owner"
          :options="ownerOptions"
          :title="$t('keys.owner')"
          :label="$t('keys.owner_placeholder')"
          :helper-text="$t('keys.owner_helper')"
          :invalid-message="error.owner"
          :disabled="loading"
          :marginBottomOnOpen="true"
          class="mg-bottom-md"
          ref="owner"
        />
        <NsComboBox
          v-model="scope"
          :options="scopeOptions"
          :title="$t('keys.scope')"
          :label="$t('keys.scope')"
          :disabled="loading"
          :marginBottomOnOpen="true"
          class="mg-bottom-md"
        />
        <NsTextInput
          v-model.trim="label"
          :label="$t('keys.label')"
          :helper-text="$t('keys.label_helper')"
          :disabled="loading"
          class="mg-bottom-md"
        />
        <NsComboBox
          v-model="restrictKind"
          :options="restrictOptions"
          :title="$t('keys.restrict')"
          :label="$t('keys.restrict')"
          :helper-text="$t('keys.restrict_helper')"
          :disabled="loading"
          :marginBottomOnOpen="true"
          class="mg-bottom-md"
        />
        <template v-if="restrictKind === 'custom'">
          <NsTextInput
            v-model.trim="restrictNames"
            :label="$t('keys.restrict_names')"
            :helper-text="$t('keys.restrict_names_helper')"
            :invalid-message="error.restrict"
            placeholder="www, mail, _acme-challenge.*"
            :disabled="loading"
            class="mg-bottom-md"
          />
          <NsTextInput
            v-model.trim="restrictTypes"
            :label="$t('keys.restrict_types')"
            :helper-text="$t('keys.restrict_types_helper')"
            placeholder="A, AAAA"
            :disabled="loading"
            class="mg-bottom-md"
          />
        </template>
        <cv-text-area
          v-model="allowlist"
          :label="$t('keys.allowlist')"
          :helper-text="$t('keys.allowlist_helper')"
          :invalid-message="error.allowlist"
          placeholder="203.0.113.10&#10;198.51.100.0/24"
          :disabled="loading"
          class="mg-bottom-md"
        />
        <NsTextInput
          v-model.trim="expires"
          type="date"
          :label="$t('keys.expires')"
          :helper-text="$t('keys.expires_helper')"
          :invalid-message="error.expires"
          :disabled="loading"
          class="mg-bottom-md"
        />
        <NsInlineNotification
          v-if="error.save"
          kind="error"
          :title="$t('action.create-key')"
          :description="error.save"
          :showCloseButton="false"
        />
      </cv-form>
    </template>
    <template v-if="!created" slot="secondary-button">{{
      core.$t("common.cancel")
    }}</template>
    <template slot="primary-button">{{
      created ? core.$t("common.close") : $t("keys.create")
    }}</template>
  </NsModal>
</template>

<script>
import { mapState } from "vuex";
import { UtilService } from "@nethserver/ns8-ui-lib";
import DnsapiService from "../mixins/dnsapi";

export default {
  name: "CreateKeyModal",
  mixins: [DnsapiService, UtilService],
  props: {
    isShown: { type: Boolean, default: false },
    tenants: { type: Array, default: () => [] },
    defaultOwner: { type: String, default: "" },
    apiUrl: { type: String, default: "" },
  },
  data() {
    return {
      owner: "",
      scope: "write",
      label: "",
      restrictKind: "none",
      restrictNames: "",
      restrictTypes: "",
      allowlist: "",
      expires: "",
      created: null,
      loading: false,
      error: { owner: "", restrict: "", allowlist: "", expires: "", save: "" },
    };
  },
  computed: {
    ...mapState(["core"]),
    shownUrl() {
      return this.apiUrl || "https://<host>/v1/";
    },
    ownerOptions() {
      return [
        {
          name: "operator",
          label: this.$t("keys.operator_option"),
          value: "operator",
        },
        ...this.tenants.map((t) => ({
          name: t.id,
          label: `${t.name} (${t.id})`,
          value: t.id,
        })),
      ];
    },
    scopeOptions() {
      return ["write", "read"].map((s) => ({
        name: s,
        label: this.$t("keys.scope_" + s),
        value: s,
      }));
    },
    restrictOptions() {
      return ["none", "acme", "custom"].map((r) => ({
        name: r,
        label: this.$t("keys.restrict_" + r),
        value: r,
      }));
    },
  },
  watch: {
    isShown(shown) {
      if (shown) {
        Object.assign(this.$data, this.$options.data.call(this));
        this.owner = this.defaultOwner || "";
      } else {
        // forget the key as soon as the dialog closes
        this.created = null;
      }
    },
  },
  methods: {
    restrictValue() {
      if (this.restrictKind === "acme") {
        return "acme";
      }
      if (this.restrictKind === "custom") {
        const split = (s) => s.split(/[\s,]+/).filter((x) => x);
        const types = split(this.restrictTypes);
        return {
          names: split(this.restrictNames),
          types: types.length ? types : ["*"],
        };
      }
      return null;
    },
    async save() {
      this.error = {
        owner: "",
        restrict: "",
        allowlist: "",
        expires: "",
        save: "",
      };
      if (!this.owner) {
        this.error.owner = this.$t("common.required");
        return;
      }
      const restrict = this.restrictValue();
      if (restrict && restrict.names && !restrict.names.length) {
        this.error.restrict = this.$t("common.required");
        return;
      }
      if (!window.crypto || !window.crypto.subtle) {
        this.error.save = this.$t("keys.no_crypto");
        return;
      }
      this.loading = true;
      try {
        const made = await this.newKey();
        const data = {
          id: made.id,
          hash: made.hash,
          owner: this.owner,
          scope: this.scope,
          label: this.label,
          allowlist: [
            ...new Set(this.allowlist.split(/[\s,]+/).filter((x) => x)),
          ],
          expires: this.expires ? `${this.expires}T00:00:00Z` : null,
          restrict,
        };
        await this.callAction("create-key", { data });
        this.created = { id: made.id, key: made.key };
        this.$emit("created");
      } catch (err) {
        for (const field of ["owner", "restrict", "allowlist", "expires"]) {
          this.error[field] = this.fieldError(err, field);
        }
        this.error.save = this.errorText(err);
      }
      this.loading = false;
    },
  },
};
</script>
