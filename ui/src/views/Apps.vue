<!--
  Copyright (C) 2026 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("apps.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getSettings || error.setSettings || error.refresh">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('error.error')"
          :description="error.getSettings || error.setSettings || error.refresh"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <div class="toolbar">
            <p class="description">{{ $t("apps.description") }}</p>
            <NsButton
              kind="secondary"
              :icon="Renew20"
              :loading="loading.refresh"
              :disabled="loading.refresh || loading.getSettings"
              @click="refreshApps"
              >{{ $t("apps.refresh") }}</NsButton
            >
          </div>
          <NsDataTable
            :allRows="rows"
            :columns="i18nTableColumns"
            :rawColumns="tableColumns"
            :sortable="true"
            :overflow-menu="true"
            :pageSizes="[10, 25, 50, 100]"
            isSearchable
            :searchPlaceholder="$t('apps.search')"
            :searchClearLabel="$t('common.clear_search')"
            :noSearchResultsLabel="$t('common.no_search_results')"
            :noSearchResultsDescription="$t('common.no_search_results_description')"
            :isLoading="loading.getSettings"
            :skeletonRows="5"
            :isErrorShown="!!error.getSettings"
            :errorTitle="error.getSettings"
            :itemsPerPageLabel="$t('pagination.items_per_page')"
            :rangeOfTotalItemsLabel="$t('pagination.range_of_total_items')"
            :ofTotalPagesLabel="$t('pagination.of_total_pages')"
            :backwardText="$t('pagination.previous_page')"
            :forwardText="$t('pagination.next_page')"
            :pageNumberLabel="$t('pagination.page_number')"
            @updatePage="tablePage = $event"
          >
            <template slot="empty-state">
              <NsEmptyState :title="$t('apps.no_apps')">
                <template #description>{{ $t("apps.no_apps_description") }}</template>
              </NsEmptyState>
            </template>
            <template slot="data">
              <cv-data-table-row
                v-for="row in tablePage"
                :key="row.id"
                :value="row.id"
              >
                <cv-data-table-cell>
                  <span :class="{ hidden: row.hidden }">{{ row.name }}</span>
                  <NsTag v-if="row.hidden" kind="gray" size="sm" :label="$t('apps.hidden')" />
                </cv-data-table-cell>
                <cv-data-table-cell>
                  <cv-link :href="row.url" target="_blank" rel="noopener">{{ row.host }}</cv-link>
                </cv-data-table-cell>
                <cv-data-table-cell>{{ row.category || "-" }}</cv-data-table-cell>
                <cv-data-table-cell>{{ row.groups.join(", ") || $t("apps.everyone") }}</cv-data-table-cell>
                <cv-data-table-cell class="table-overflow-menu-cell">
                  <cv-overflow-menu flip-menu class="table-overflow-menu">
                    <cv-overflow-menu-item @click="editApp(row)">
                      <NsMenuItem :icon="Edit20" :label="$t('common.edit')" />
                    </cv-overflow-menu-item>
                    <cv-overflow-menu-item @click="toggleHidden(row)">
                      <NsMenuItem
                        :icon="row.hidden ? View20 : ViewOff20"
                        :label="row.hidden ? $t('apps.show') : $t('apps.hide')"
                      />
                    </cv-overflow-menu-item>
                  </cv-overflow-menu>
                </cv-data-table-cell>
              </cv-data-table-row>
            </template>
          </NsDataTable>
        </cv-tile>
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <h4 class="mg-bottom">{{ $t("apps.categories") }}</h4>
          <p class="description mg-bottom">{{ $t("apps.categories_description") }}</p>
          <div class="tags mg-bottom">
            <cv-tag
              v-for="category in settings.categories"
              :key="category"
              kind="high-contrast"
              :label="category"
              filter
              :clear-aria-label="$t('common.delete')"
              @remove="removeCategory(category)"
            />
          </div>
          <cv-form class="inline-form" @submit.prevent="addCategory">
            <NsTextInput
              v-model.trim="newCategory"
              :label="$t('apps.new_category')"
              :invalid-message="error.newCategory"
              :disabled="loading.setSettings"
            />
            <NsButton kind="secondary" :icon="Add20" :disabled="!newCategory || loading.setSettings">{{
              $t("apps.add_category")
            }}</NsButton>
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
    <NsModal
      size="default"
      :visible="!!editing"
      :primary-button-disabled="loading.setSettings || loading.listGroups"
      @modal-hidden="editing = null"
      @primary-click="saveApp"
    >
      <template slot="title">{{ $t("apps.edit_app", { host: editing && editing.host }) }}</template>
      <template slot="content">
        <cv-form v-if="editing" class="modal-form" @submit.prevent="saveApp">
          <NsTextInput
            v-model.trim="editing.name"
            :label="$t('apps.name')"
            :helper-text="$t('apps.name_helper', { name: editing.discoveredName })"
            :placeholder="editing.discoveredName"
            class="mg-bottom"
          />
          <cv-select v-model="editing.category" :label="$t('apps.category')" class="mg-bottom">
            <cv-select-option value="">{{ $t("apps.no_category") }}</cv-select-option>
            <cv-select-option v-for="category in settings.categories" :key="category" :value="category">{{
              category
            }}</cv-select-option>
          </cv-select>
          <NsMultiSelect
            v-if="authMode === 'ldap'"
            v-model="editing.groups"
            :options="groupOptions"
            :title="$t('apps.groups')"
            :label="$t('apps.groups_placeholder')"
            :helper-text="$t('apps.groups_helper')"
            :disabled="loading.listGroups"
            :invalid-message="error.listGroups"
            selectionFeedback="top-after-reopen"
            filterable
            auto-filter
            auto-highlight
            class="mg-bottom"
          />
          <NsToggle
            value="hidden"
            v-model="editing.hidden"
            :label="$t('apps.hide_app')"
          >
            <template slot="text-left">{{ $t("common.no") }}</template>
            <template slot="text-right">{{ $t("common.yes") }}</template>
          </NsToggle>
        </cv-form>
        <NsInlineNotification
          v-if="error.setSettings"
          kind="error"
          :title="$t('action.set-settings')"
          :description="error.setSettings"
          :showCloseButton="false"
        />
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
import Renew20 from "@carbon/icons-vue/es/renew/20";
import View20 from "@carbon/icons-vue/es/view/20";
import ViewOff20 from "@carbon/icons-vue/es/view--off/20";
import LauncherSettings from "@/mixins/LauncherSettings";

export default {
  name: "Apps",
  mixins: [TaskService, IconService, UtilService, QueryParamService, PageTitleService, LauncherSettings],
  pageTitle() {
    return this.$t("apps.title") + " - " + this.appName;
  },
  data() {
    return {
      q: { page: "apps" },
      urlCheckInterval: null,
      Renew20,
      View20,
      ViewOff20,
      tablePage: [],
      tableColumns: ["name", "host", "category", "groups"],
      editing: null,
      newCategory: "",
      authMode: "public",
      groups: [],
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    i18nTableColumns() {
      return this.tableColumns.map((column) => this.$t("apps.column_" + column));
    },
    rows() {
      return this.discovered.map((app) => {
        const override = this.settings.apps[app.id] || {};
        return {
          ...app,
          discoveredName: app.name,
          name: override.name || app.name,
          category: override.category || "",
          groups: override.groups || [],
          hidden: !!override.hidden,
        };
      });
    },
    groupOptions() {
      return this.groups.map((g) => ({ name: g.group, label: g.group, value: g.group, description: g.description }));
    },
  },
  created() {
    this.$set(this.loading, "refresh", false);
    this.$set(this.loading, "listGroups", false);
    this.$set(this.error, "refresh", "");
    this.$set(this.error, "listGroups", "");
    this.$set(this.error, "newCategory", "");
    this.getSettings();
    this.getAuthMode();
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
    async getAuthMode() {
      await this.runTask(
        "get-configuration",
        {},
        (taskContext, taskResult) => {
          this.authMode = taskResult.output.auth_mode;
          if (this.authMode === "ldap") {
            this.listGroups();
          }
        },
        () => {}
      );
    },
    async listGroups() {
      this.loading.listGroups = true;
      this.error.listGroups = "";
      const [err] = await this.runTask(
        "list-groups",
        {},
        (taskContext, taskResult) => {
          this.groups = taskResult.output.groups;
          this.loading.listGroups = false;
        },
        () => {
          this.error.listGroups = this.$t("apps.cannot_list_groups");
          this.loading.listGroups = false;
        }
      );
      if (err) {
        this.error.listGroups = this.getErrorMessage(err);
        this.loading.listGroups = false;
      }
    },
    async refreshApps() {
      this.loading.refresh = true;
      this.error.refresh = "";
      const [err] = await this.runTask(
        "refresh-apps",
        {},
        () => {
          this.loading.refresh = false;
          this.getSettings();
        },
        () => {
          this.error.refresh = this.$t("error.generic_error");
          this.loading.refresh = false;
        }
      );
      if (err) {
        this.error.refresh = this.getErrorMessage(err);
        this.loading.refresh = false;
      }
    },
    editApp(row) {
      this.error.setSettings = "";
      this.editing = {
        id: row.id,
        host: row.host,
        discoveredName: row.discoveredName,
        name: (this.settings.apps[row.id] || {}).name || "",
        category: row.category,
        groups: [...row.groups],
        hidden: row.hidden,
      };
    },
    storeOverride(id, override) {
      const clean = {};
      if (override.hidden) clean.hidden = true;
      if (override.name) clean.name = override.name;
      if (override.category) clean.category = override.category;
      if (override.groups && override.groups.length) clean.groups = override.groups;
      const apps = { ...this.settings.apps };
      if (Object.keys(clean).length) apps[id] = clean;
      else delete apps[id];
      this.settings.apps = apps;
    },
    async saveApp() {
      const { id, name, category, groups, hidden } = this.editing;
      this.storeOverride(id, { name, category, groups, hidden });
      await this.saveSettings();
      if (!this.error.setSettings) {
        this.editing = null;
      }
    },
    toggleHidden(row) {
      const current = this.settings.apps[row.id] || {};
      this.storeOverride(row.id, { ...current, hidden: !row.hidden });
      this.saveSettings();
    },
    addCategory() {
      this.error.newCategory = "";
      if (this.settings.categories.includes(this.newCategory)) {
        this.error.newCategory = this.$t("apps.category_exists");
        return;
      }
      this.settings.categories = [...this.settings.categories, this.newCategory];
      this.newCategory = "";
      this.saveSettings();
    },
    removeCategory(category) {
      this.settings.categories = this.settings.categories.filter((c) => c !== category);
      const apps = {};
      for (const [id, override] of Object.entries(this.settings.apps)) {
        apps[id] = override.category === category ? { ...override, category: undefined } : override;
      }
      this.settings.apps = JSON.parse(JSON.stringify(apps));
      this.settings.links = this.settings.links.map((link) =>
        link.category === category ? { ...link, category: "" } : link
      );
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
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-05;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-06;
}
.description {
  max-width: 48rem;
}
.hidden {
  opacity: 0.6;
  margin-right: $spacing-03;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-02;
}
.inline-form {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-05;
  align-items: flex-end;
  max-width: 38rem;
}
// NsTextInput keeps a bottom margin that pushes the button below the field
.inline-form .bx--form-item {
  flex: 1;
  margin-bottom: 0;
}
// Carbon gives dropdowns and text inputs different widths: line them up
.modal-form .bx--form-item,
.modal-form .bx--select-input__wrapper,
.modal-form .bx--select-input,
.modal-form .bx--list-box,
.modal-form .bx--text-input,
.modal-form .bx--multi-select {
  width: 100%;
  max-width: 38rem;
}
</style>
