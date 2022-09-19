<template>
  <v-container class="mt-3">
    <v-row>
      <h4>Feed Importer</h4>
    </v-row>
    <!--    Subreddit Feed Load -->
    <v-form ref="form">
      <v-row>
        <v-col cols="3">
          <v-text-field
              v-model="feedSubreddit"
              label="Subreddit"
              required
              id="feedSubreddit"
          ></v-text-field>
        </v-col>
        <v-col cols="2">
          <v-select v-model="feedSortType" id="feedSortTypeSelect" :items="sortTypes" label="Sort by.."
                    item-text="sortType"></v-select>
        </v-col>

        <v-btn @click="loadSubredditFeed" color="info" class="mt-5">
          <v-icon>mdi-refresh</v-icon>
          Load
        </v-btn>
      </v-row>

      <v-row>
        <v-list density="compact" max-height="500px">
          <v-list-item v-for="(item, i) in subredditFeedItems" :prepend-avatar="item.url" :key="i">
            <v-list-item-title v-text="item.title"></v-list-item-title>
            <v-badge color="success">
              <v-icon size="12">mdi-arrow-up</v-icon>
              {{ item.score }}
            </v-badge>
            <v-badge color="info" >
              <span class="text-grey-darken-1">{{formatTime(item.created_utc)}}</span>
            </v-badge>

          </v-list-item>
        </v-list>
      </v-row>
    </v-form>
  </v-container>

</template>

<script>
import axios from "axios";
import {formatDistance} from "date-fns";

export default {
  name: "feed-importer",
  data: () => ({
    feedSubreddit: "rapmemes",
    feedSortType: "hot",
    sortTypes: ['hot', 'new', 'top', 'rising', 'controversial'],
    subredditFeedItems: []
  }),
  methods: {
    async loadSubredditFeed() {
      console.log("Loading feed for " + this.feedSubreddit + " sorted by " + this.feedSortType);

      axios.post("http://127.0.0.1:5000/feed-importer/load/", {
        subreddit: this.feedSubreddit,
        sortType: this.feedSortType
      }).then(response => {
        this.subredditFeedItems = response.data['posts']
      }).catch(error => {
        console.log(error);
      });
    },
    formatTime(time) {
      const timeformat = formatDistance(new Date(time * 1000), new Date(), {addSuffix: true});
      return timeformat
    }
  }
}
</script>

<style scoped>

</style>