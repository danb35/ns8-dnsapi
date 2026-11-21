<!--
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later

  Add a tenant, or edit one: its name, whether it is enabled, and its zones.
  The zones offered are the ones dnshelper lets dnsapi write in that no
  other tenant has (list-assignable-zones). Saving calls add-tenant or
  update-tenant, then assign-zone and unassign-zone for what changed.
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
    <template slot="title">{{
      tenant
        ? $t("tenants.edit_title", { name: tenant.name })
        : $t("tenants.add_title")
    }}</template>
    <template slot="content">
      <cv-form @submit.prevent="save">
        <NsTextInput
          v-model.trim="name"
          :label="$t('tenants.name')"
          :helper-text="$t('tenants.name_helper')"
          :invalid-message="error.name"
          :disabled="loading"
          class="mg-bottom-md"
          ref="name"
        />
        <NsToggle
          value="enabled"
          :label="$t('tenants.enabled')"
          v-model="enabled"
          :disabled="loading"
          class="mg-bottom-md"
        >
          <template #tooltip>{{ $t("tenants.enabled_tooltip") }}</template>
          <template slot="text-left">{{ $t("common.disabled") }}</template>
          <template slot="text-right">{{ $t("common.enabled") }}</template>
        </NsToggle>

        <div class="mg-bottom-sm">
          <strong>{{ $t("tenants.zones") }}</strong>
        </div>
        <p class="mg-bottom-sm helper">{{ $t("tenants.zones_helper") }}</p>
        <div v-if="!zoneOptions.length" class="mg-bottom-md helper">
          {{ $t("tenants.no_zones_to_assign") }}
        </div>
        <div v-for="option in zoneOptions" :key="option.zone">
          <NsCheckbox
            v-model="zones"
            :value="option.zone"
            :label="option.zone"
            :disabled="loading"
          />
          <NsTag
            v-if="!option.full"
            :label="$t('zones.partial')"
            kind="warm-gray"
            size="sm"
            class="zone-tag"
          />
        </div>

        <NsInlineNotification
          v-if="error.save"
          kind="error"
          :title="$t('tenants.save_failed')"
          :description="error.save"
          :showCloseButton="false"
          class="mg-top-md"
        />
      </cv-form>
    </template>
    <template slot="secondary-button">{{ core.$t("common.cancel") }}</template>
    <template slot="primary-button">{{
      tenant ? $t("common.save") : $t("tenants.add")
    }}</template>
  </NsModal>
</template>

<script>
import { mapState } from "vuex";
import { UtilService } from "@nethserver/ns8-ui-lib";
import DnsapiService from "../mixins/dnsapi";

export default {
  name: "TenantModal",
  mixins: [DnsapiService, UtilService],
  props: {
    isShown: { type: Boolean, default: false },
    tenant: { type: Object, default: null }, // null: add a tenant
    assignable: { type: Array, default: () => [] }, // list-assignable-zones' zones
  },
  data() {
    return {
      name: "",
      enabled: true,
      zones: [],
      loading: false,
      error: { name: "", save: "" },
    };
  },
  computed: {
    ...mapState(["core"]),
    zoneOptions() {
      const own = this.tenant ? this.tenant.id : null;
      const offered = this.assignable.filter(
        (z) => !z.tenant || z.tenant === own
      );
      // a zone the tenant has that dnshelper no longer lets dnsapi use still shows, to remove it
      const extra = (this.tenant ? this.tenant.zones : [])
        .filter((z) => !offered.some((o) => o.zone === z))
        .map((z) => ({ zone: z, full: true }));
      return [...offered, ...extra].sort((a, b) =>
        a.zone.localeCompare(b.zone)
      );
    },
  },
  watch: {
    isShown(shown) {
      if (shown) {
        this.name = this.tenant ? this.tenant.name : "";
        this.enabled = this.tenant ? this.tenant.enabled : true;
        this.zones = this.tenant ? [...this.tenant.zones] : [];
        this.error = { name: "", save: "" };
      }
    },
  },
  methods: {
    async save() {
      this.error = { name: "", save: "" };
      if (!this.name) {
        this.error.name = this.$t("common.required");
        this.focusElement("name");
        return;
      }
      this.loading = true;
      try {
        let id;
        if (this.tenant) {
          id = this.tenant.id;
          if (
            this.name !== this.tenant.name ||
            this.enabled !== this.tenant.enabled
          ) {
            await this.callAction("update-tenant", {
              data: { id, name: this.name, enabled: this.enabled },
            });
          }
        } else {
          const out = await this.callAction("add-tenant", {
            data: { name: this.name, enabled: this.enabled },
          });
          id = out.id;
        }
        const before = this.tenant ? this.tenant.zones : [];
        for (const zone of this.zones.filter((z) => !before.includes(z))) {
          await this.callAction("assign-zone", { data: { tenant: id, zone } });
        }
        for (const zone of before.filter((z) => !this.zones.includes(z))) {
          await this.callAction("unassign-zone", {
            data: { tenant: id, zone },
          });
        }
        this.loading = false;
        this.$emit("saved");
        this.$emit("hide");
      } catch (err) {
        this.loading = false;
        this.error.name = this.fieldError(err, "name");
        this.error.save = this.errorText(err);
        // what was saved before the error shows when the page reloads
        this.$emit("saved");
      }
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";

.helper {
  color: $text-02;
  max-width: 40rem;
}

.zone-tag {
  margin-left: $spacing-03;
  vertical-align: middle;
}
</style>
