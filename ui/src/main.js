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
import { loadLanguage } from "./i18n";

loadI18n();

async function loadI18n() {
  const coreLang =
    window.parent &&
    window.parent.core &&
    window.parent.core.$i18n &&
    window.parent.core.$i18n.locale;
  const navigatorLang = (coreLang || navigator.language).substring(0, 2);
  const enMessages = await loadLanguage("en");
  const messages =
    navigatorLang === "en" ? enMessages : await loadLanguage(navigatorLang);
  Vue.use(VueI18n);
  const i18n = new VueI18n({
    locale: navigatorLang,
    fallbackLocale: "en",
    silentFallbackWarn: true,
    silentTranslationWarn: true,
    messages: {
      en: enMessages.default,
      ...(messages && messages.default
        ? { [navigatorLang]: messages.default }
        : {}),
    },
  });

  new Vue({
    router,
    store,
    i18n,
    render: (h) => h(App),
  }).$mount("#ns8-app");
}
