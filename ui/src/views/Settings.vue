<!--
  Copyright (C) 2026 Nethesis S.r.l.
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
            <cv-text-input
              :label="$t('settings.launcher_fqdn')"
              placeholder="home.example.org"
              v-model.trim="host"
              class="mg-bottom"
              :invalid-message="$t(error.host)"
              :disabled="loading.getConfiguration || loading.configureModule"
              ref="host"
            >
            </cv-text-input>
            <NsToggle
              value="letsEncrypt"
              :label="core.$t('apps_lets_encrypt.request_https_certificate')"
              v-model="isLetsEncryptEnabled"
              :disabled="stillLoading"
              class="mg-bottom"
            >
              <template #tooltip>
                <div class="mg-bottom-sm">
                  {{ core.$t("apps_lets_encrypt.lets_encrypt_tips") }}
                </div>
                <div class="mg-bottom-sm">
                  <cv-link @click="goToCertificates">
                    {{ core.$t("apps_lets_encrypt.go_to_tls_certificates") }}
                  </cv-link>
                </div>
              </template>
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </NsToggle>
            <cv-row
              v-if="isLetsEncryptCurrentlyEnabled && !isLetsEncryptEnabled"
            >
              <cv-column>
                <NsInlineNotification
                  kind="warning"
                  :title="
                    core.$t('apps_lets_encrypt.lets_encrypt_disabled_warning')
                  "
                  :description="
                    core.$t(
                      'apps_lets_encrypt.lets_encrypt_disabled_warning_description',
                      {
                        node: this.status.node_ui_name
                          ? this.status.node_ui_name
                          : this.status.node,
                      }
                    )
                  "
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <cv-radio-group
              :legend="$t('settings.auth_mode')"
              vertical
              class="mg-bottom"
            >
              <cv-radio-button
                v-model="authMode"
                name="auth_mode"
                value="public"
                :label="$t('settings.auth_mode_public')"
                :disabled="stillLoading"
              />
              <cv-radio-button
                v-model="authMode"
                name="auth_mode"
                value="ldap"
                :label="$t('settings.auth_mode_ldap')"
                :disabled="stillLoading"
              />
            </cv-radio-group>
            <NsComboBox
              v-if="authMode === 'ldap'"
              v-model="ldapDomain"
              :options="domainOptions"
              :title="$t('settings.ldap_domain')"
              :label="$t('settings.choose_ldap_domain')"
              :invalid-message="error.ldap_domain"
              :helper-text="$t('settings.ldap_domain_helper')"
              :disabled="stillLoading"
              auto-filter
              auto-highlight
              class="mg-bottom maxwidth"
              ref="ldap_domain"
            />
            <template v-if="authMode === 'ldap'">
              <NsToggle
                value="passwordPortal"
                :label="$t('settings.password_portal')"
                v-model="isPasswordPortalEnabled"
                :disabled="stillLoading"
                class="mg-bottom"
              >
                <template #tooltip>
                  {{ $t("settings.password_portal_tips") }}
                </template>
                <template slot="text-left">{{
                  $t("settings.disabled")
                }}</template>
                <template slot="text-right">{{
                  $t("settings.enabled")
                }}</template>
              </NsToggle>
              <NsTextInput
                v-if="isPasswordPortalEnabled"
                v-model.trim="passwordPortalUrl"
                :label="$t('settings.password_portal_url')"
                placeholder="https://node.example.org/users-admin/example.org/"
                :helper-text="passwordPortalHelper"
                :invalid-message="error.password_portal_url"
                :disabled="stillLoading || loading.suggestPasswordPortal"
                class="mg-bottom maxwidth"
                ref="password_portal_url"
              />
            </template>
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
            <cv-row v-if="error.getStatus">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.get-status')"
                  :description="error.getStatus"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <cv-row v-if="validationErrorDetails.length">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="
                    core.$t('apps_lets_encrypt.cannot_obtain_certificate')
                  "
                  :showCloseButton="false"
                >
                  <template #description>
                    <div class="flex flex-col gap-2">
                      <div
                        v-for="(detail, index) in validationErrorDetails"
                        :key="index"
                      >
                        {{ detail }}
                      </div>
                    </div>
                  </template>
                </NsInlineNotification>
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule"
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                loading.suggestPasswordPortal
              "
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
      status: {},
      validationErrorDetails: [],
      urlCheckInterval: null,
      host: "",
      isLetsEncryptEnabled: false,
      isLetsEncryptCurrentlyEnabled: false,
      authMode: "public",
      ldapDomain: "",
      ldapDomainList: [],
      isPasswordPortalEnabled: false,
      passwordPortalUrl: "",
      passwordPortalHelper: "",
      configured: { ldapDomain: "", passwordPortalUrl: "" },
      loading: {
        getConfiguration: false,
        configureModule: false,
        getStatus: false,
        suggestPasswordPortal: false,
      },
      suggestToken: 0,
      error: {
        getConfiguration: "",
        configureModule: "",
        host: "",
        lets_encrypt: "",
        auth_mode: "",
        ldap_domain: "",
        password_portal_url: "",
        getStatus: "",
      },
    };
  },
  watch: {
    isPasswordPortalEnabled(enabled) {
      if (enabled && !this.passwordPortalUrl) {
        this.suggestPasswordPortal();
      }
    },
    ldapDomain(domain) {
      // Drop any suggestion still running for the previous domain
      this.suggestToken++;
      this.loading.suggestPasswordPortal = false;
      if (!this.isPasswordPortalEnabled || !domain) {
        return;
      }
      // A portal URL belongs to one domain: propose a new one when the domain changes
      if (
        domain === this.configured.ldapDomain &&
        this.configured.passwordPortalUrl
      ) {
        this.passwordPortalUrl = this.configured.passwordPortalUrl;
      } else {
        this.suggestPasswordPortal();
      }
    },
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    domainOptions() {
      return this.ldapDomainList.map((domain) => ({
        name: domain,
        label: domain,
        value: domain,
      }));
    },
    stillLoading() {
      return (
        this.loading.getConfiguration ||
        this.loading.configureModule ||
        this.loading.getStatus
      );
    },
  },
  created() {
    this.getConfiguration();
    this.getStatus();
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
  methods: {
    goToCertificates() {
      this.core.$router.push("/settings/tls-certificates");
    },
    taskOutput(createTask, action) {
      return new Promise((resolve, reject) => {
        const eventId = this.getUuid();
        const events = ["completed", "aborted", "validation-failed"].map(
          (state) => `${action}-${state}-${eventId}`
        );
        // Only one of the events fires: remove the other listeners too
        const settle =
          (callback) =>
          (...args) => {
            events.forEach((event) => this.core.$root.$off(event));
            callback(...args);
          };
        const fail = settle(() => reject(new Error(action)));
        this.core.$root.$once(
          events[0],
          settle((taskContext, taskResult) => resolve(taskResult.output))
        );
        this.core.$root.$once(events[1], fail);
        this.core.$root.$once(events[2], fail);
        createTask({
          action,
          extra: {
            title: this.$t("action." + action),
            isNotificationHidden: true,
            eventId,
          },
        }).catch(fail);
      });
    },
    // Same URL as the "User portal" link of the core domain page:
    // the FQDN of the node running the first provider of the domain
    async suggestPasswordPortal() {
      const domain = this.ldapDomain;
      if (!domain) {
        return;
      }
      const token = ++this.suggestToken;
      this.loading.suggestPasswordPortal = true;
      this.passwordPortalHelper = "";
      let url = "";
      try {
        const output = await this.taskOutput(
          (task) => this.createClusterTaskForApp(task),
          "list-user-domains"
        );
        const found = output.domains.find((d) => d.name === domain);
        const provider =
          found &&
          found.location === "internal" &&
          found.providers.find((p) => p.node);
        if (provider) {
          const fqdn = await this.taskOutput(
            (task) => this.createNodeTaskForApp(provider.node, task),
            "get-fqdn"
          );
          url = `https://${fqdn.hostname}.${fqdn.domain}/users-admin/${domain}/`;
        }
      } catch (err) {
        console.error("cannot suggest the password portal", err);
      }
      // The admin may have picked another domain meanwhile
      if (token !== this.suggestToken) {
        return;
      }
      this.loading.suggestPasswordPortal = false;
      this.passwordPortalUrl = url;
      this.passwordPortalHelper = url
        ? this.$t("settings.password_portal_suggested")
        : this.$t("settings.password_portal_no_suggestion");
    },
    async getStatus() {
      this.loading.getStatus = true;
      this.error.getStatus = "";
      const taskAction = "get-status";
      const eventId = this.getUuid();
      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getStatusAborted
      );
      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.getStatusCompleted
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
        this.error.getStatus = this.getErrorMessage(err);
        this.loading.getStatus = false;
        return;
      }
    },
    getStatusAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getStatus = this.$t("error.generic_error");
      this.loading.getStatus = false;
    },
    getStatusCompleted(taskContext, taskResult) {
      this.status = taskResult.output;
      this.loading.getStatus = false;
    },
    async getConfiguration() {
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
        this.getConfigurationCompleted
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
      const config = taskResult.output;
      this.host = config.host;
      this.isLetsEncryptEnabled = config.lets_encrypt;
      this.isLetsEncryptCurrentlyEnabled = config.lets_encrypt;
      this.authMode = config.auth_mode;
      this.ldapDomain = config.ldap_domain;
      this.ldapDomainList = config.ldap_domain_list;
      this.configured = {
        ldapDomain: config.ldap_domain,
        passwordPortalUrl: config.password_portal_url || "",
      };
      this.passwordPortalUrl = this.configured.passwordPortalUrl;
      this.isPasswordPortalEnabled = !!this.passwordPortalUrl;
      this.passwordPortalHelper = "";

      this.loading.getConfiguration = false;
      this.focusElement("host");
    },
    validateConfigureModule() {
      this.clearErrors(this);
      this.validationErrorDetails = [];
      let isValidationOk = true;
      if (!this.host) {
        this.error.host = "common.required";

        if (isValidationOk) {
          this.focusElement("host");
        }
        isValidationOk = false;
      }
      if (this.authMode === "ldap" && !this.ldapDomain) {
        this.error.ldap_domain = this.$t("common.required");
        if (isValidationOk) {
          this.focusElement("ldap_domain");
        }
        isValidationOk = false;
      }
      if (this.authMode === "ldap" && this.isPasswordPortalEnabled) {
        if (!this.passwordPortalUrl) {
          this.error.password_portal_url = this.$t("common.required");
        } else if (!/^https:\/\/\S+$/.test(this.passwordPortalUrl)) {
          this.error.password_portal_url = this.$t(
            "settings.password_portal_url_pattern"
          );
        }
        if (this.error.password_portal_url) {
          if (isValidationOk) {
            this.focusElement("password_portal_url");
          }
          isValidationOk = false;
        }
      }
      return isValidationOk;
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;
      for (const validationError of validationErrors) {
        const param = validationError.parameter;
        if (validationError.details) {
          // show inline error notification with details
          this.validationErrorDetails = validationError.details
            .split("\n")
            .filter((detail) => detail.trim() !== "");
        } else {
          // set i18n error message
          this.error[param] = this.$t("settings." + validationError.error);
          if (!focusAlreadySet) {
            this.focusElement(param);
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
            auth_mode: this.authMode,
            ldap_domain: this.authMode === "ldap" ? this.ldapDomain : "",
            password_portal_url:
              this.authMode === "ldap" && this.isPasswordPortalEnabled
                ? this.passwordPortalUrl
                : "",
          },
          extra: {
            title: this.$t("settings.instance_configuration", {
              instance: this.instanceName,
            }),
            description: this.$t("settings.configuring"),
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
.mg-bottom {
  margin-bottom: $spacing-06;
}

.maxwidth {
  max-width: 38rem;
}
</style>
