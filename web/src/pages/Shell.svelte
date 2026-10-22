<script lang="ts">
  import Sidebar from "../components/Sidebar.svelte";
  import { t } from "../lib/i18n.svelte";
  import { pageOf } from "../lib/pages";
  import { router } from "../lib/router.svelte";
  import { session } from "../lib/session.svelte";

  const page = $derived(pageOf(router.path));
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
      <h1 class="text-2xl font-bold">{t(page.key, page.english)}</h1>
    </main>
  </div>
</div>
