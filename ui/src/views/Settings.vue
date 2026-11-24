<!--
  Copyright (C) 2023 Nethesis S.r.l. (ns8-kickstart template)
  Copyright (C) 2026 Dan Brown
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("settings.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getConfiguration">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-configuration')"
          :description="error.getConfiguration"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-form @submit.prevent="configureModule">
            <NsTextInput
              :label="$t('settings.host')"
              v-model.trim="host"
              placeholder="dnsapi.example.com"
              :helper-text="$t('settings.host_helper')"
              :disabled="stillLoading"
              :invalid-message="error.host"
              class="mg-bottom"
              ref="host"
            />
            <NsToggle
              value="letsEncrypt"
              :label="$t('settings.lets_encrypt')"
              v-model="isLetsEncryptEnabled"
              :disabled="stillLoading"
              class="mg-bottom"
            >
              <template #tooltip>
                {{ $t("settings.lets_encrypt_tooltip") }}
              </template>
              <template slot="text-left">{{ $t("common.disabled") }}</template>
              <template slot="text-right">{{ $t("common.enabled") }}</template>
            </NsToggle>
            <NsToggle
              value="revokeCleartextKeys"
              :label="$t('settings.revoke_cleartext_keys')"
              v-model="revokeCleartextKeys"
              :disabled="stillLoading"
              class="mg-bottom"
            >
              <template #tooltip>{{
                $t("settings.revoke_cleartext_keys_tooltip")
              }}</template>
              <template slot="text-left">{{ $t("common.disabled") }}</template>
              <template slot="text-right">{{ $t("common.enabled") }}</template>
            </NsToggle>
            <cv-text-area
              :label="$t('settings.ip_allowlist')"
              v-model="ipAllowlist"
              :helper-text="$t('settings.ip_allowlist_helper')"
              placeholder="203.0.113.10, 198.51.100.0/24"
              :disabled="stillLoading"
              :invalid-message="error.ip_allowlist"
              class="mg-bottom"
              ref="ip_allowlist"
            />
            <NsTextInput
              v-model.number="rateLimit"
              type="number"
              min="1"
              max="10000"
              :label="$t('settings.rate_limit')"
              :helper-text="$t('settings.rate_limit_helper')"
              :disabled="stillLoading"
              :invalid-message="error.rate_limit"
              class="mg-bottom"
              ref="rate_limit"
            />
            <NsToggle
              value="publishHostRecord"
              :label="$t('settings.publish_host_record')"
              v-model="publishHostRecord"
              :disabled="stillLoading"
              class="mg-bottom"
            >
              <template #tooltip>{{
                $t("settings.publish_host_record_tooltip")
              }}</template>
              <template slot="text-left">{{ $t("common.disabled") }}</template>
              <template slot="text-right">{{ $t("common.enabled") }}</template>
            </NsToggle>
            <NsInlineNotification
              v-if="hostRecordNotice"
              :kind="hostRecordNotice.kind"
              :title="hostRecordNotice.title"
              :description="hostRecordNotice.description"
              :showCloseButton="false"
              class="mg-bottom"
            />
            <cv-row v-if="error.configureModule">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.configure-module')"
                  :description="error.configureModule"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule"
              :disabled="stillLoading"
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import DnsapiService from "../mixins/dnsapi";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";

export default {
  name: "Settings",
  mixins: [
    DnsapiService,
    TaskService,
    IconService,
    UtilService,
    QueryParamService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("settings.title") + " - " + this.appName;
  },
  data() {
    return {
      q: {
        page: "settings",
      },
      urlCheckInterval: null,
      host: "",
      isLetsEncryptEnabled: false,
      revokeCleartextKeys: true,
      ipAllowlist: "",
      rateLimit: 60,
      publishHostRecord: true,
      hostRecord: null,
      loading: {
        getConfiguration: false,
        configureModule: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        host: "",
        lets_encrypt: "",
        ip_allowlist: "",
        rate_limit: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    hostRecordNotice() {
      return this.hostRecordStatus(this.hostRecord);
    },
    stillLoading() {
      return this.loading.getConfiguration || this.loading.configureModule;
    },
    ipAllowlistEntries() {
      return this.ipAllowlist
        .split(/[\s,]+/)
        .map((entry) => entry.trim())
        .filter((entry) => entry);
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
    this.getConfiguration();
  },
  methods: {
    /**
     * Read the configuration. With hostRecordOnly, only the host name's DNS
     * record is updated: after a failed save, configure-module has recorded
     * what it found for it, but nothing else, and the form keeps what was typed.
     */
    async getConfiguration(hostRecordOnly = false) {
      this.loading.getConfiguration = true;
      this.error.getConfiguration = "";
      const taskAction = "get-configuration";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getConfigurationAborted
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        (taskContext, taskResult) =>
          hostRecordOnly
            ? this.hostRecordCompleted(taskResult)
            : this.getConfigurationCompleted(taskContext, taskResult)
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          extra: {
            title: this.$t("action." + taskAction),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`, err);
        this.error.getConfiguration = this.getErrorMessage(err);
        this.loading.getConfiguration = false;
        return;
      }
    },
    getConfigurationAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getConfiguration = this.$t("error.generic_error");
      this.loading.getConfiguration = false;
    },
    getConfigurationCompleted(taskContext, taskResult) {
      this.loading.getConfiguration = false;
      const config = taskResult.output;

      this.host = config.host || "";
      this.isLetsEncryptEnabled = config.lets_encrypt;
      this.revokeCleartextKeys = config.revoke_cleartext_keys;
      this.ipAllowlist = config.ip_allowlist.join("\n");
      this.rateLimit = config.rate_limit;
      this.publishHostRecord = config.publish_host_record;
      this.hostRecord = config.host_record;
      this.focusElement("host");
    },
    hostRecordCompleted(taskResult) {
      this.loading.getConfiguration = false;
      this.hostRecord = taskResult.output.host_record;
    },
    validateConfigureModule() {
      this.clearErrors(this);
      let isValidationOk = true;

      if (!this.host) {
        this.error.host = this.$t("common.required");
        this.focusElement("host");
        isValidationOk = false;
      }
      if (
        !Number.isInteger(this.rateLimit) ||
        this.rateLimit < 1 ||
        this.rateLimit > 10000
      ) {
        this.error.rate_limit = this.$t("settings.rate_limit_invalid");
        if (isValidationOk) {
          this.focusElement("rate_limit");
        }
        isValidationOk = false;
      }
      return isValidationOk;
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      // A certificate that could not be issued is reported here; the host
      // record's notice often says why (no rule for the CNAME, for example)
      this.getConfiguration(true);
      let focusAlreadySet = false;

      for (const validationError of validationErrors) {
        const field = validationError.field;

        if (field !== "(root)") {
          // set i18n error message
          // Traefik reports a certificate failure on the host field
          this.error[field] = this.$t("settings." + validationError.error, {
            value: validationError.value,
          });

          if (!focusAlreadySet) {
            this.focusElement(field);
            focusAlreadySet = true;
          }
        }
      }
    },
    async configureModule() {
      const isValidationOk = this.validateConfigureModule();
      if (!isValidationOk) {
        return;
      }

      this.loading.configureModule = true;
      const taskAction = "configure-module";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.configureModuleAborted
      );

      // register to task validation
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.configureModuleValidationFailed
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.configureModuleCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: {
            host: this.host,
            lets_encrypt: this.isLetsEncryptEnabled,
            revoke_cleartext_keys: this.revokeCleartextKeys,
            ip_allowlist: [...new Set(this.ipAllowlistEntries)],
            rate_limit: this.rateLimit,
            publish_host_record: this.publishHostRecord,
          },
          extra: {
            title: this.$t("settings.configure_instance", {
              instance: this.instanceName,
            }),
            description: this.$t("common.processing"),
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`, err);
        this.error.configureModule = this.getErrorMessage(err);
        this.loading.configureModule = false;
        return;
      }
    },
    configureModuleAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
      this.getConfiguration(true);
    },
    configureModuleCompleted() {
      this.loading.configureModule = false;

      // reload configuration
      this.getConfiguration();
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
</style>
