<!--
  Copyright (C) 2026 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("appearance.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getSettings">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-settings')"
          :description="error.getSettings"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-form @submit.prevent="save">
            <NsTextInput
              v-model.trim="settings.welcome"
              :label="$t('appearance.welcome')"
              :placeholder="$t('appearance.welcome_default')"
              :helper-text="$t('appearance.welcome_helper')"
              :disabled="loading.getSettings || loading.setSettings"
              maxlength="200"
              class="mg-bottom maxwidth"
            />
            <div class="mg-bottom">
              <div class="bx--label">{{ $t("appearance.logo") }}</div>
              <div class="logo-row">
                <img v-if="logoPreview" :src="logoPreview" alt="" class="logo-preview" />
                <img v-else-if="!logoReset && logoSet" :src="currentLogoUrl" alt="" class="logo-preview" />
                <img v-else src="../assets/module_default_logo.png" alt="" class="logo-preview" />
                <div>
                  <cv-file-uploader
                    :key="uploaderKey"
                    kind="button"
                    accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                    :multiple="false"
                    :removable="false"
                    :button-label="$t('appearance.upload_logo')"
                    @change="onLogoChange"
                  />
                  <p class="helper">{{ $t("appearance.logo_helper") }}</p>
                  <NsButton
                    v-if="logoSet && !logoReset"
                    kind="ghost"
                    size="small"
                    :icon="Reset20"
                    @click="resetLogo"
                    >{{ $t("appearance.reset_logo") }}</NsButton
                  >
                </div>
              </div>
              <p v-if="error.logo" class="invalid">{{ error.logo }}</p>
            </div>
            <NsInlineNotification
              v-if="error.setSettings"
              kind="error"
              :title="$t('action.set-settings')"
              :description="error.setSettings"
              :showCloseButton="false"
            />
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.setSettings"
              :disabled="loading.getSettings || loading.setSettings"
              >{{ $t("common.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import { mapState } from "vuex";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";
import Reset20 from "@carbon/icons-vue/es/reset/20";
import LauncherSettings from "@/mixins/LauncherSettings";

const LOGO_MAX_BYTES = 512 * 1024;

export default {
  name: "Appearance",
  mixins: [TaskService, IconService, UtilService, QueryParamService, PageTitleService, LauncherSettings],
  pageTitle() {
    return this.$t("appearance.title") + " - " + this.appName;
  },
  data() {
    return {
      q: { page: "appearance" },
      urlCheckInterval: null,
      Reset20,
      host: "",
      logoData: null,
      logoPreview: "",
      logoReset: false,
      uploaderKey: 0,
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    currentLogoUrl() {
      // Served by the launcher page itself; the cache buster follows each save
      return this.host ? `https://${this.host}/brand/logo?${this.updated}` : "";
    },
  },
  created() {
    this.$set(this.error, "logo", "");
    this.getSettings();
    this.runTask(
      "get-configuration",
      {},
      (taskContext, taskResult) => (this.host = taskResult.output.host),
      () => {}
    );
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
    onLogoChange(files) {
      this.error.logo = "";
      const file = files && files.length ? files[files.length - 1].file : null;
      if (!file) return;
      if (!["image/png", "image/jpeg"].includes(file.type)) {
        this.error.logo = this.$t("appearance.logo_invalid_format");
      } else if (file.size > LOGO_MAX_BYTES) {
        this.error.logo = this.$t("appearance.logo_too_large");
      }
      if (this.error.logo) {
        this.uploaderKey++;
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        this.logoPreview = reader.result;
        this.logoData = reader.result.split(",")[1];
        this.logoReset = false;
      };
      reader.readAsDataURL(file);
    },
    resetLogo() {
      this.logoData = "";
      this.logoPreview = "";
      this.logoReset = true;
      this.uploaderKey++;
    },
    async save() {
      const extra = this.logoData === null ? {} : { logo: this.logoData };
      await this.saveSettings(extra);
      if (!this.error.setSettings) {
        this.logoData = null;
        this.logoPreview = "";
        this.logoReset = false;
        this.uploaderKey++;
      }
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
.logo-row {
  display: flex;
  gap: $spacing-06;
  align-items: flex-start;
}
// cv-file-uploader reserves room for a file list we never show
.logo-row ::v-deep .bx--file {
  margin-bottom: 0;
}
.logo-row ::v-deep .bx--file-container:empty {
  display: none;
}
.logo-preview {
  width: 64px;
  height: 64px;
  object-fit: contain;
  border-radius: 50%;
  background: #f4f4f4;
}
.helper {
  font-size: 0.75rem;
  margin: 0 0 $spacing-03;
}
.invalid {
  color: #da1e28;
  font-size: 0.75rem;
  margin-top: $spacing-03;
}
</style>
