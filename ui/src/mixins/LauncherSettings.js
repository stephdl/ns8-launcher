//
// Copyright (C) 2026 Nethesis S.r.l.
// SPDX-License-Identifier: GPL-3.0-or-later
//
import to from "await-to-js";

// set-settings replaces the whole page content, so every page loads the
// full settings and sends them back with its own part changed.
export default {
  data() {
    return {
      settings: {
        welcome: "",
        support: { url: "", email: "", phone: "" },
        categories: [],
        apps: {},
        links: [],
      },
      discovered: [],
      updated: 0,
      logoSet: false,
      loading: { getSettings: false, setSettings: false },
      error: { getSettings: "", setSettings: "" },
    };
  },
  methods: {
    runTask(action, data, onCompleted, onAborted, onValidationFailed) {
      const eventId = this.getUuid();
      this.core.$root.$once(`${action}-aborted-${eventId}`, onAborted);
      this.core.$root.$once(`${action}-completed-${eventId}`, onCompleted);
      if (onValidationFailed) {
        this.core.$root.$once(
          `${action}-validation-failed-${eventId}`,
          onValidationFailed
        );
      }
      return to(
        this.createModuleTaskForApp(this.instanceName, {
          action,
          data,
          extra: {
            title: this.$t("action." + action),
            isNotificationHidden: action.startsWith("get-") || action.startsWith("list-"),
            eventId,
          },
        })
      );
    },
    async getSettings() {
      this.loading.getSettings = true;
      this.error.getSettings = "";
      const [err] = await this.runTask(
        "get-settings",
        {},
        (taskContext, taskResult) => {
          const output = taskResult.output;
          this.settings = {
            welcome: output.welcome || "",
            support: { url: "", email: "", phone: "", ...output.support },
            categories: output.categories || [],
            apps: output.apps || {},
            links: output.links || [],
          };
          this.discovered = output.discovered || [];
          this.updated = output.updated || 0;
          this.logoSet = output.logo_set;
          this.loading.getSettings = false;
          this.onSettingsLoaded && this.onSettingsLoaded();
        },
        () => {
          this.error.getSettings = this.$t("error.generic_error");
          this.loading.getSettings = false;
        }
      );
      if (err) {
        this.error.getSettings = this.getErrorMessage(err);
        this.loading.getSettings = false;
      }
    },
    async saveSettings(extra = {}) {
      this.loading.setSettings = true;
      this.error.setSettings = "";
      const [err] = await this.runTask(
        "set-settings",
        { ...this.settings, ...extra },
        () => {
          this.loading.setSettings = false;
          this.getSettings();
        },
        () => {
          this.error.setSettings = this.$t("error.generic_error");
          this.loading.setSettings = false;
        },
        (validationErrors) => {
          this.loading.setSettings = false;
          this.error.setSettings = validationErrors
            .map((e) => this.$t("settings." + e.error))
            .join(", ");
        }
      );
      if (err) {
        this.error.setSettings = this.getErrorMessage(err);
        this.loading.setSettings = false;
      }
    },
  },
};
