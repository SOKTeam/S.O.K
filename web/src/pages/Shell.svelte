<script lang="ts">
  import { onMount } from "svelte";

  import Sidebar from "../components/Sidebar.svelte";
  import { t } from "../lib/i18n.svelte";
  import { pageOf } from "../lib/pages";
  import { router } from "../lib/router.svelte";
  import { refreshRename } from "../lib/renames.svelte";
  import { listen } from "../lib/scan.svelte";
  import { session } from "../lib/session.svelte";
  import Analysis from "./Analysis.svelte";
  import History from "./History.svelte";
  import MediaTab from "./MediaTab.svelte";
  import Settings from "./Settings.svelte";

  const page = $derived(pageOf(router.path));

  // The analysis and its progress, live, for every page.
  onMount(() => {
    refreshRename().catch(() => {});
    return listen();
  });
</script>

<div class="flex h-full">
  <Sidebar />
  <div class="flex min-w-0 flex-1 flex-col">
    {#if session.current?.auth === "none"}
      <p class="border-b border-warn/30 bg-warn/10 px-6 py-2 text-sm text-warn" role="status">
        {t(
          "web_auth_off",
          "The login is turned off (SOK_AUTH=none): protect this server with your reverse proxy.",
        )}
      </p>
    {/if}
    <main class="flex-1 overflow-y-auto p-8">
      {#if page.path === "/settings"}
        <Settings />
      {:else if page.path === "/"}
        <Analysis />
      {:else if page.path === "/history"}
        <History />
      {:else if page.mediaType}
        <MediaTab {page} />
      {:else}
        <h1 class="text-2xl font-bold">{t(page.key, page.english)}</h1>
      {/if}
    </main>
  </div>
</div>
