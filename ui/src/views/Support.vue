<!--
  Copyright (C) 2026 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("support.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getSettings || error.setSettings">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('error.error')"
          :description="error.getSettings || error.setSettings"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <h4 class="mg-bottom">{{ $t("support.contacts") }}</h4>
          <cv-form class="maxwidth" @submit.prevent="saveContacts">
            <NsTextInput
              v-model.trim="settings.support.url"
              :label="$t('support.url')"
              placeholder="https://support.example.org"
              :invalid-message="error.supportUrl"
              :disabled="loading.getSettings || loading.setSettings"
              maxlength="500"
              class="mg-bottom"
            />
            <NsTextInput
              v-model.trim="settings.support.email"
              :label="$t('support.email')"
              placeholder="support@example.org"
              :disabled="loading.getSettings || loading.setSettings"
              maxlength="200"
              class="mg-bottom"
            />
            <NsTextInput
              v-model.trim="settings.support.phone"
              :label="$t('support.phone')"
              :disabled="loading.getSettings || loading.setSettings"
              maxlength="50"
              class="mg-bottom"
            />
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.setSettings"
              :disabled="loading.getSettings || loading.setSettings || !!error.supportUrl"
              >{{ $t("common.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <div class="toolbar">
            <div>
              <h4>{{ $t("support.links") }}</h4>
              <p class="description">{{ $t("support.links_description") }}</p>
            </div>
            <NsButton kind="secondary" :icon="Add20" @click="editLink(-1)">{{
              $t("support.add_link")
            }}</NsButton>
          </div>
          <NsDataTable
            :allRows="linkRows"
            :columns="[$t('support.link_name'), $t('support.link_url'), $t('apps.column_category')]"
            :rawColumns="['name', 'url', 'category']"
            :sortable="true"
            :overflow-menu="true"
            :pageSizes="[10, 25, 50]"
            :isLoading="loading.getSettings"
            :skeletonRows="3"
            :itemsPerPageLabel="$t('pagination.items_per_page')"
            :rangeOfTotalItemsLabel="$t('pagination.range_of_total_items')"
            :ofTotalPagesLabel="$t('pagination.of_total_pages')"
            :backwardText="$t('pagination.previous_page')"
            :forwardText="$t('pagination.next_page')"
            :pageNumberLabel="$t('pagination.page_number')"
            @updatePage="tablePage = $event"
          >
            <template slot="empty-state">
              <NsEmptyState :title="$t('support.no_links')" />
            </template>
            <template slot="data">
              <cv-data-table-row v-for="row in tablePage" :key="row.index" :value="String(row.index)">
                <cv-data-table-cell>{{ row.name }}</cv-data-table-cell>
                <cv-data-table-cell>
                  <cv-link :href="row.url" target="_blank" rel="noopener">{{ row.url }}</cv-link>
                </cv-data-table-cell>
                <cv-data-table-cell>{{ row.category || "-" }}</cv-data-table-cell>
                <cv-data-table-cell class="table-overflow-menu-cell">
                  <cv-overflow-menu flip-menu class="table-overflow-menu">
                    <cv-overflow-menu-item @click="editLink(row.index)">
                      <NsMenuItem :icon="Edit20" :label="$t('common.edit')" />
                    </cv-overflow-menu-item>
                    <cv-overflow-menu-item danger @click="deleteLink(row.index)">
                      <NsMenuItem :icon="TrashCan20" :label="$t('common.delete')" />
                    </cv-overflow-menu-item>
                  </cv-overflow-menu>
                </cv-data-table-cell>
              </cv-data-table-row>
            </template>
          </NsDataTable>
        </cv-tile>
      </cv-column>
    </cv-row>
    <NsModal
      size="default"
      :visible="!!editing"
      :primary-button-disabled="loading.setSettings"
      @modal-hidden="editing = null"
      @primary-click="saveLink"
    >
      <template slot="title">{{
        editing && editing.index >= 0 ? $t("support.edit_link") : $t("support.add_link")
      }}</template>
      <template slot="content">
        <cv-form v-if="editing" class="modal-form" @submit.prevent="saveLink">
          <NsTextInput
            v-model.trim="editing.name"
            :label="$t('support.link_name')"
            :invalid-message="error.linkName"
            maxlength="100"
            class="mg-bottom"
          />
          <NsTextInput
            v-model.trim="editing.url"
            :label="$t('support.link_url')"
            placeholder="https://"
            :invalid-message="error.linkUrl"
            maxlength="500"
            class="mg-bottom"
          />
          <cv-select v-model="editing.category" :label="$t('apps.column_category')" class="mg-bottom">
            <cv-select-option value="">{{ $t("apps.no_category") }}</cv-select-option>
            <cv-select-option v-for="category in settings.categories" :key="category" :value="category">{{
              category
            }}</cv-select-option>
          </cv-select>
        </cv-form>
      </template>
      <template slot="secondary-button">{{ $t("common.cancel") }}</template>
      <template slot="primary-button">{{ $t("common.save") }}</template>
    </NsModal>
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
import LauncherSettings from "@/mixins/LauncherSettings";

const URL_PATTERN = /^https?:\/\/\S+$/;

export default {
  name: "Support",
  mixins: [TaskService, IconService, UtilService, QueryParamService, PageTitleService, LauncherSettings],
  pageTitle() {
    return this.$t("support.title") + " - " + this.appName;
  },
  data() {
    return {
      q: { page: "support" },
      urlCheckInterval: null,
      tablePage: [],
      editing: null,
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    linkRows() {
      return this.settings.links.map((link, index) => ({ ...link, index }));
    },
  },
  created() {
    for (const key of ["supportUrl", "linkName", "linkUrl"]) {
      this.$set(this.error, key, "");
    }
    this.getSettings();
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
  watch: {
    "settings.support.url"(value) {
      this.error.supportUrl = value && !URL_PATTERN.test(value) ? this.$t("support.invalid_url") : "";
    },
  },
  methods: {
    saveContacts() {
      if (this.error.supportUrl) return;
      this.saveSettings();
    },
    editLink(index) {
      this.error.linkName = "";
      this.error.linkUrl = "";
      const link = index >= 0 ? this.settings.links[index] : { name: "", url: "", category: "" };
      this.editing = { index, name: link.name, url: link.url, category: link.category || "" };
    },
    async saveLink() {
      const { index, name, url, category } = this.editing;
      this.error.linkName = name ? "" : this.$t("common.required");
      this.error.linkUrl = URL_PATTERN.test(url) ? "" : this.$t("support.invalid_url");
      if (this.error.linkName || this.error.linkUrl) return;
      const link = { name, url, category };
      const links = [...this.settings.links];
      if (index >= 0) links.splice(index, 1, { ...links[index], ...link });
      else links.push(link);
      this.settings.links = links;
      await this.saveSettings();
      if (!this.error.setSettings) this.editing = null;
    },
    deleteLink(index) {
      this.settings.links = this.settings.links.filter((link, i) => i !== index);
      this.saveSettings();
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
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-05;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: $spacing-06;
}
.description {
  margin-top: $spacing-03;
}
// Carbon gives dropdowns and text inputs different widths: line them up
.modal-form .bx--form-item,
.modal-form .bx--select-input__wrapper,
.modal-form .bx--select-input,
.modal-form .bx--list-box,
.modal-form .bx--text-input {
  width: 100%;
  max-width: 38rem;
}
</style>
