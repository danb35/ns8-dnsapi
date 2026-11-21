<!--
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div>
    <cv-grid fullWidth>
      <cv-row>
        <cv-column class="page-title">
          <h2>{{ $t("keys.title") }}</h2>
        </cv-column>
      </cv-row>
      <cv-row v-if="error.load">
        <cv-column>
          <NsInlineNotification
            kind="error"
            :title="$t('keys.cannot_load')"
            :description="error.load"
            :showCloseButton="false"
          />
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column>
          <p class="section-intro">{{ $t("keys.intro") }}</p>
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column :md="4" :max="4">
          <cv-select
            v-model="q.owner"
            :label="$t('keys.show')"
            :disabled="loading.load"
            class="mg-bottom-md"
          >
            <cv-select-option value="">{{
              $t("keys.show_all")
            }}</cv-select-option>
            <cv-select-option
              v-for="o in filterOptions"
              :key="o.value"
              :value="o.value"
              >{{ o.label }}</cv-select-option
            >
          </cv-select>
        </cv-column>
        <cv-column>
          <NsButton
            kind="secondary"
            :icon="Add20"
            :disabled="loading.load"
            class="create-button"
            @click="isCreateShown = true"
            >{{ $t("keys.create") }}</NsButton
          >
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column>
          <NsDataTable
            :allRows="shownKeys"
            :columns="columns"
            :rawColumns="['label']"
            :sortable="true"
            :pageSizes="[10, 25, 50]"
            :overflow-menu="true"
            :isLoading="loading.load"
            :skeletonRows="3"
            :itemsPerPageLabel="core.$t('pagination.items_per_page')"
            :rangeOfTotalItemsLabel="core.$t('pagination.range_of_total_items')"
            :ofTotalPagesLabel="core.$t('pagination.of_total_pages')"
            :backwardText="core.$t('pagination.previous_page')"
            :forwardText="core.$t('pagination.next_page')"
            :pageNumberLabel="core.$t('pagination.page_number')"
            @updatePage="page = $event"
          >
            <template slot="empty-state">
              <NsEmptyState :title="$t('keys.no_keys')">
                <template #description>
                  <div>{{ $t("keys.no_keys_description") }}</div>
                </template>
              </NsEmptyState>
            </template>
            <template slot="data">
              <cv-data-table-row
                v-for="(row, i) in page"
                :key="row.id"
                :value="String(i)"
              >
                <cv-data-table-cell>
                  <strong>{{ row.label || row.id }}</strong>
                  <div class="secondary">dnsapi_{{ row.id }}_…</div>
                </cv-data-table-cell>
                <cv-data-table-cell>{{
                  tenantName(tenants, row.owner)
                }}</cv-data-table-cell>
                <cv-data-table-cell>
                  <NsTag
                    :label="$t('keys.scope_' + row.scope)"
                    :kind="row.scope === 'write' ? 'purple' : 'gray'"
                  />
                  <NsTag
                    v-if="row.restrict"
                    :label="restrictLabel(row.restrict)"
                    kind="cyan"
                  />
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <span v-if="!row.allowlist.length" class="secondary">{{
                    $t("keys.any_address")
                  }}</span>
                  <div v-for="a in row.allowlist" :key="a">{{ a }}</div>
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <span v-if="isExpired(row)" class="expired">{{
                    $t("keys.expired")
                  }}</span>
                  <span v-else>{{
                    row.expires ? formatTime(row.expires) : $t("keys.never")
                  }}</span>
                </cv-data-table-cell>
                <cv-data-table-cell>{{
                  row.last_used
                    ? formatTime(row.last_used)
                    : $t("keys.never_used")
                }}</cv-data-table-cell>
                <cv-data-table-cell class="table-overflow-menu-cell">
                  <cv-overflow-menu flip-menu class="table-overflow-menu">
                    <cv-overflow-menu-item danger @click="showRevoke(row)">
                      <NsMenuItem
                        :icon="TrashCan20"
                        :label="$t('keys.revoke')"
                      />
                    </cv-overflow-menu-item>
                  </cv-overflow-menu>
                </cv-data-table-cell>
              </cv-data-table-row>
            </template>
          </NsDataTable>
        </cv-column>
      </cv-row>
    </cv-grid>

    <CreateKeyModal
      :isShown="isCreateShown"
      :tenants="tenants"
      :defaultOwner="q.owner"
      :apiUrl="apiUrl"
      @hide="isCreateShown = false"
      @created="load"
    />
    <ConfirmDeleteModal
      :isShown="isRevokeShown"
      :name="current ? current.id : ''"
      :title="$t('keys.revoke_title')"
      :warning="core.$t('common.please_read_carefully')"
      :description="
        $t('keys.revoke_description', {
          label: current ? current.label || current.id : '',
          owner: current ? tenantName(tenants, current.owner) : '',
        })
      "
      :isErrorShown="!!error.revoke"
      :errorTitle="$t('action.revoke-key')"
      :errorDescription="error.revoke"
      :loading="loading.revoke"
      @hide="isRevokeShown = false"
      @confirmDelete="revoke"
    />
  </div>
</template>

<script>
import { mapState } from "vuex";
import {
  QueryParamService,
  IconService,
  UtilService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";
import DnsapiService from "../mixins/dnsapi";
import CreateKeyModal from "../components/CreateKeyModal.vue";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.vue";

export default {
  name: "Keys",
  components: { CreateKeyModal, ConfirmDeleteModal },
  mixins: [
    DnsapiService,
    QueryParamService,
    IconService,
    UtilService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("keys.title") + " - " + this.appName;
  },
  data() {
    return {
      q: { page: "keys", owner: "" },
      urlCheckInterval: null,
      keys: [],
      tenants: [],
      apiUrl: "",
      page: [],
      current: null,
      isCreateShown: false,
      isRevokeShown: false,
      loading: { load: false, revoke: false },
      error: { load: "", revoke: "" },
    };
  },
  computed: {
    ...mapState(["core", "appName"]),
    columns() {
      return [
        "label",
        "owner",
        "access",
        "allowlist",
        "expires",
        "last_used",
      ].map((c) => this.$t("keys.col_" + c));
    },
    filterOptions() {
      return [
        {
          name: "operator",
          label: this.$t("keys.operator"),
          value: "operator",
        },
        ...this.tenants.map((t) => ({
          name: t.id,
          label: t.name,
          value: t.id,
        })),
      ];
    },
    shownKeys() {
      return this.q.owner
        ? this.keys.filter((k) => k.owner === this.q.owner)
        : this.keys;
    },
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.watchQueryData(vm);
      vm.urlCheckInterval = vm.initUrlBindingForApp(vm, vm.q.page);
    });
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.urlCheckInterval);
    next();
  },
  created() {
    this.load();
  },
  methods: {
    async load() {
      this.loading.load = true;
      this.error.load = "";
      try {
        const [keys, tenants, config] = await Promise.all([
          this.callAction("list-keys"),
          this.callAction("list-tenants"),
          this.callAction("get-configuration"),
        ]);
        this.keys = keys.keys;
        this.tenants = tenants.tenants;
        this.apiUrl = config.host ? `https://${config.host}/v1/` : "";
      } catch (err) {
        this.error.load = this.errorText(err);
      }
      this.loading.load = false;
    },
    restrictLabel(restrict) {
      const acme =
        restrict.names.join(",") === "_acme-challenge,_acme-challenge.*" &&
        restrict.types.join(",") === "TXT";
      return acme
        ? this.$t("keys.restrict_acme_tag")
        : this.$t("keys.restrict_custom_tag");
    },
    isExpired(row) {
      return row.expires && new Date(row.expires) <= new Date();
    },
    formatTime(iso) {
      return new Date(iso).toLocaleString();
    },
    showRevoke(row) {
      this.current = row;
      this.error.revoke = "";
      this.isRevokeShown = true;
    },
    async revoke() {
      this.loading.revoke = true;
      this.error.revoke = "";
      try {
        await this.callAction("revoke-key", { data: { id: this.current.id } });
        this.isRevokeShown = false;
        await this.load();
      } catch (err) {
        this.error.revoke = this.errorText(err);
      }
      this.loading.revoke = false;
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";

.section-intro {
  margin-bottom: $spacing-05;
  max-width: 50rem;
}

.secondary {
  color: $text-02;
  font-size: 0.75rem;
}

.expired {
  color: $support-01;
}

.create-button {
  margin-top: 1.5rem;
}
</style>
