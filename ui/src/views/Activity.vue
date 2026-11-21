<!--
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later

  The most recent changes (list-activity): what the API changed, and what
  administrators changed here. Reads are not listed.
-->
<template>
  <div>
    <cv-grid fullWidth>
      <cv-row>
        <cv-column class="page-title">
          <h2>{{ $t("activity.title") }}</h2>
        </cv-column>
      </cv-row>
      <cv-row v-if="error.load">
        <cv-column>
          <NsInlineNotification
            kind="error"
            :title="$t('activity.cannot_load')"
            :description="error.load"
            :showCloseButton="false"
          />
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column>
          <p class="section-intro">{{ $t("activity.intro") }}</p>
          <NsButton
            kind="ghost"
            :icon="Restart20"
            :disabled="loading.load"
            class="mg-bottom-md"
            @click="load"
            >{{ $t("activity.refresh") }}</NsButton
          >
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column>
          <NsDataTable
            :allRows="entries"
            :columns="columns"
            :rawColumns="['time']"
            :sortable="false"
            :pageSizes="[25, 50, 100]"
            :isLoading="loading.load"
            :skeletonRows="5"
            :itemsPerPageLabel="core.$t('pagination.items_per_page')"
            :rangeOfTotalItemsLabel="core.$t('pagination.range_of_total_items')"
            :ofTotalPagesLabel="core.$t('pagination.of_total_pages')"
            :backwardText="core.$t('pagination.previous_page')"
            :forwardText="core.$t('pagination.next_page')"
            :pageNumberLabel="core.$t('pagination.page_number')"
            @updatePage="page = $event"
          >
            <template slot="empty-state">
              <NsEmptyState :title="$t('activity.no_activity')">
                <template #description>
                  <div>{{ $t("activity.no_activity_description") }}</div>
                </template>
              </NsEmptyState>
            </template>
            <template slot="data">
              <cv-data-table-row
                v-for="(row, i) in page"
                :key="i"
                :value="String(i)"
              >
                <cv-data-table-cell class="nowrap">{{
                  formatTime(row.time)
                }}</cv-data-table-cell>
                <cv-data-table-cell>
                  <template v-if="row.source === 'api'">
                    <div>{{ who(row) }}</div>
                    <div class="secondary">{{ row.address }}</div>
                  </template>
                  <template v-else>
                    <div>{{ $t("activity.administrator") }}</div>
                    <div class="secondary">{{ row.caller }}</div>
                  </template>
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <div>{{ actionLabel(row.action) }}</div>
                  <div v-if="row.zone" class="secondary">{{ row.zone }}</div>
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <div
                    v-for="r in row.add || []"
                    :key="'a' + r"
                    class="change add"
                  >
                    + {{ r }}
                  </div>
                  <div
                    v-for="r in row.remove || []"
                    :key="'r' + r"
                    class="change remove"
                  >
                    − {{ r }}
                  </div>
                  <div v-if="details(row)" class="secondary">
                    {{ details(row) }}
                  </div>
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <NsTag
                    :label="resultLabel(row.result)"
                    :kind="resultKind(row.result)"
                  />
                </cv-data-table-cell>
              </cv-data-table-row>
            </template>
          </NsDataTable>
        </cv-column>
      </cv-row>
    </cv-grid>
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

export default {
  name: "Activity",
  mixins: [
    DnsapiService,
    QueryParamService,
    IconService,
    UtilService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("activity.title") + " - " + this.appName;
  },
  data() {
    return {
      q: { page: "activity" },
      urlCheckInterval: null,
      entries: [],
      tenants: [],
      page: [],
      loading: { load: false },
      error: { load: "" },
    };
  },
  computed: {
    ...mapState(["core", "appName"]),
    columns() {
      return ["time", "who", "action", "changes", "result"].map((c) =>
        this.$t("activity.col_" + c)
      );
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
        const [activity, tenants] = await Promise.all([
          this.callAction("list-activity", { data: { limit: 500 } }),
          this.callAction("list-tenants"),
        ]);
        this.entries = activity.entries;
        this.tenants = tenants.tenants;
      } catch (err) {
        this.error.load = this.errorText(err);
      }
      this.loading.load = false;
    },
    formatTime(iso) {
      return new Date(iso).toLocaleString();
    },
    who(row) {
      const owner = this.tenantName(this.tenants, row.owner);
      return this.$t("activity.key_of", { key: row.key, owner });
    },
    actionLabel(action) {
      const key = "activity.action_" + action.replace(/-/g, "_");
      return this.$te(key) ? this.$t(key) : action;
    },
    details(row) {
      const parts = [];
      if (row.tenant && !row.zone) {
        // the name recorded with the change, for a tenant removed since
        const known = this.tenants.some((t) => t.id === row.tenant);
        parts.push(
          known || !row.name
            ? this.tenantName(this.tenants, row.tenant)
            : row.name
        );
      }
      // admin entries name the key acted on as key, API entries as target_key
      const target = row.source === "admin" ? row.key : row.target_key;
      if (target) {
        parts.push(this.$t("activity.key_id", { key: target }));
      }
      return parts.join(", ");
    },
    resultLabel(result) {
      const base = (result || "").split(":")[0];
      const key = "activity.result_" + base.replace(/-/g, "_");
      const label = this.$te(key) ? this.$t(key) : base;
      const code = (result || "").split(":")[1];
      return code ? `${label}: ${code}` : label;
    },
    resultKind(result) {
      const base = (result || "").split(":")[0];
      return (
        { ok: "green", "dry-run": "blue", rejected: "magenta", failed: "red" }[
          base
        ] || "gray"
      );
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

.nowrap {
  white-space: nowrap;
}

.change {
  font-family: "IBM Plex Mono", "Menlo", "Courier New", monospace;
  font-size: 0.75rem;
  word-break: break-all;
}

.add {
  color: $support-02;
}

.remove {
  color: $support-01;
}
</style>
