import {createApp} from 'vue'
import App from './App.vue'
import vuetify from './plugins/vuetify'
import {loadFonts} from './plugins/webfontloader'
import router from './plugins/router'
import 'v-calendar/dist/style.css';

import VCalendar from 'v-calendar';

loadFonts();
createApp(App)
    .use(vuetify)
    .use(router)
    .use(VCalendar)
    .mount('#app')
