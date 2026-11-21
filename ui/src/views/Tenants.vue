<!--
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div>
    <cv-grid fullWidth>
      <cv-row>
        <cv-column class="page-title">
          <h2>{{ $t("tenants.title") }}</h2>
        </cv-column>
      </cv-row>
      <cv-row v-if="error.load">
        <cv-column>
          <NsInlineNotification
            kind="error"
            :title="$t('tenants.cannot_load')"
            :description="error.load"
            :showCloseButton="false"
          />
        </cv-column>
      </cv-row>
      <cv-row v-if="!loading.load && zonesError">
        <cv-column>
          <NsInlineNotification
            kind="warning"
            :title="$t('zones.unavailable_title')"
            :description="$t('zones.unavailable_' + zonesError)"
            :showCloseButton="false"
          />
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column>
          <p class="section-intro">{{ $t("tenants.intro") }}</p>
          <NsButton
            kind="secondary"
            :icon="Add20"
            :disabled="loading.load"
            class="mg-bottom-md"
            @click="showAdd"
            >{{ $t("tenants.add") }}</NsButton
          >
        </cv-column>
      </cv-row>
      <cv-row>
        <cv-column>
          <NsDataTable
            :allRows="tenants"
            :columns="columns"
            :rawColumns="['name']"
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
              <NsEmptyState :title="$t('tenants.no_tenants')">
                <template #description>
                  <div>{{ $t("tenants.no_tenants_description") }}</div>
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
                  <strong>{{ row.name }}</strong>
                  <div class="secondary">{{ row.id }}</div>
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <span v-if="!row.zones.length" class="secondary">-</span>
                  <NsTag
                    v-for="zone in row.zones"
                    :key="zone"
                    :label="zone"
                    :kind="isFull(zone) ? 'blue' : 'warm-gray'"
                    size="sm"
                  />
                </cv-data-table-cell>
                <cv-data-table-cell>{{ row.keys }}</cv-data-table-cell>
                <cv-data-table-cell>
                  <NsTag
                    :label="
                      row.enabled ? $t('common.enabled') : $t('common.disabled')
                    "
                    :kind="row.enabled ? 'green' : 'gray'"
                  />
                </cv-data-table-cell>
                <cv-data-table-cell class="table-overflow-menu-cell">
                  <cv-overflow-menu flip-menu class="table-overflow-menu">
                    <cv-overflow-menu-item @click="showEdit(row)">
                      <NsMenuItem :icon="Edit20" :label="$t('tenants.edit')" />
                    </cv-overflow-menu-item>
                    <cv-overflow-menu-item @click="goToKeys(row)">
                      <NsMenuItem
                        :icon="Password20"
                        :label="$t('tenants.show_keys')"
                      />
                    </cv-overflow-menu-item>
                    <NsMenuDivider />
                    <cv-overflow-menu-item danger @click="showRemove(row)">
                      <NsMenuItem
                        :icon="TrashCan20"
                        :label="$t('tenants.remove')"
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

    <TenantModal
      :isShown="isEditShown"
      :tenant="current"
      :assignable="assignable"
      @hide="isEditShown = false"
      @saved="load"
    />
    <ConfirmDeleteModal
      :isShown="isRemoveShown"
      :name="current ? current.name : ''"
      :title="$t('tenants.remove_title')"
      :warning="core.$t('common.please_read_carefully')"
      :description="
        $tc('tenants.remove_description', current ? current.keys : 0, {
          name: current ? current.name : '',
          keys: current ? current.keys : 0,
        })
      "
      :isErrorShown="!!error.remove"
      :errorTitle="$t('action.remove-tenant')"
      :errorDescription="error.remove"
      :loading="loading.remove"
      @hide="isRemoveShown = false"
      @confirmDelete="remove"
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
import TenantModal from "../components/TenantModal.vue";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.vue";

export default {
  name: "Tenants",
  components: { TenantModal, ConfirmDeleteModal },
  mixins: [
    DnsapiService,
    QueryParamService,
    IconService,
    UtilService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("tenants.title") + " - " + this.appName;
  },
  data() {
    return {
      q: { page: "tenants" },
      urlCheckInterval: null,
      tenants: [],
      assignable: [],
      zonesError: null,
      page: [],
      current: null,
      isEditShown: false,
      isRemoveShown: false,
      loading: { load: false, remove: false },
      error: { load: "", remove: "" },
    };
  },
  computed: {
    ...mapState(["core", "appName", "instanceName"]),
    columns() {
      return ["name", "zones", "keys", "status"].map((c) =>
        this.$t("tenants.col_" + c)
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
        const [tenants, zones] = await Promise.all([
          this.callAction("list-tenants"),
          this.callAction("list-assignable-zones"),
        ]);
        this.tenants = tenants.tenants;
        this.assignable = zones.zones;
        this.zonesError = zones.error;
      } catch (err) {
        this.error.load = this.errorText(err);
      }
      this.loading.load = false;
    },
    isFull(zone) {
      const z = this.assignable.find((a) => a.zone === zone);
      return !z || z.full;
    },
    showAdd() {
      this.current = null;
      this.isEditShown = true;
    },
    showEdit(row) {
      this.current = row;
      this.isEditShown = true;
    },
    showRemove(row) {
      this.current = row;
      this.error.remove = "";
      this.isRemoveShown = true;
    },
    goToKeys(row) {
      // the Keys page reads owner from the URL (its q.owner)
      this.core.$router.push(
        `/apps/${this.instanceName}?page=keys&owner=${row.id}`
      );
    },
    async remove() {
      this.loading.remove = true;
      this.error.remove = "";
      try {
        await this.callAction("remove-tenant", {
          data: { id: this.current.id },
        });
        this.isRemoveShown = false;
        await this.load();
      } catch (err) {
        this.error.remove = this.errorText(err);
      }
      this.loading.remove = false;
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
</style>
