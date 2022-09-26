import {createRouter, createWebHashHistory} from 'vue-router';
// import Homepage from "@/components/Homepage";
import FeedImporter from "@/components/FeedImporter";

const routes = [
    {path: '/', component: FeedImporter},
    {path: '/feed-importer', component: FeedImporter}
];

export default createRouter({
    history: createWebHashHistory(),
    routes: routes
})