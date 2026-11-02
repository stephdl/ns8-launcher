//
// Copyright (C) 2023 Nethesis S.r.l.
// SPDX-License-Identifier: GPL-3.0-or-later
//
import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import store from "./store";

import CarbonComponentsVue from "@carbon/vue";
Vue.use(CarbonComponentsVue);

import axios from "axios";
axios.defaults.timeout = 10000;
import VueAxios from "vue-axios";
Vue.use(VueAxios, axios);

import ns8Lib from "@nethserver/ns8-ui-lib";
Vue.use(ns8Lib);

import VueDateFns from "vue-date-fns";
Vue.use(VueDateFns);

import LottieAnimation from "lottie-web-vue";
Vue.use(LottieAnimation);

import vueDebounce from "vue-debounce";
Vue.use(vueDebounce);

// filters
import { Filters } from "@nethserver/ns8-ui-lib";
for (const f in Filters) {
  Vue.filter(f, Filters[f]);
}

Vue.config.productionTip = false;

// i18n
import VueI18n from "vue-i18n";
import { loadLanguage, pickLanguage } from "./i18n";

loadI18n();

async function loadI18n() {
  // Follow the language chosen in the NS8 admin, not the browser one
  const core = window.parent.core;
  const coreLocale = core && core.$i18n && core.$i18n.locale;
  const lang = pickLanguage(coreLocale || navigator.language);
  const english = await loadLanguage("en");
  const messages = lang === "en" ? english : await loadLanguage(lang);
  Vue.use(VueI18n);
  // A key not translated yet shows in English instead of its raw name
  const i18n = new VueI18n({ fallbackLocale: "en", silentFallbackWarn: true });
  i18n.setLocaleMessage("en", english.default);
  i18n.setLocaleMessage(lang, messages.default);
  i18n.locale = lang;

  new Vue({
    router,
    store,
    i18n,
    render: (h) => h(App),
  }).$mount("#ns8-app");
}
