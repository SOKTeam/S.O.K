<script lang="ts">
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.svelte";
  import { ANALYSIS, MEDIA_PAGES, OTHER_PAGES, type Page } from "../lib/pages";
  import { follow, router } from "../lib/router.svelte";
  import { analysis } from "../lib/scan.svelte";
  import { logOut, session } from "../lib/session.svelte";
</script>

{#snippet link(page: Page)}
  {@const current = router.path === page.path || router.path.startsWith(`${page.path}/`)}
  {@const counts = page.mediaType ? analysis.summary?.counts[page.mediaType] : undefined}
  <a
    href={page.path}
    onclick={follow}
    aria-current={current ? "page" : undefined}
    class={[
      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
      current ? "bg-selected text-fg" : "text-muted hover:bg-hover hover:text-fg",
    ]}
  >
    <Icon name={page.icon} class={["size-4.5", current && "text-accent"].join(" ")} />
    <span class="flex-1 truncate">{t(page.key, page.english)}</span>
    {#if counts?.ambiguous}
      <span
        class="rounded-full bg-warn/15 px-1.5 text-xs font-semibold text-warn tabular-nums"
        title={t("status_ambiguous", "Pick one")}>{counts.ambiguous}</span
      >
    {/if}
    {#if counts?.total}
      <span class="text-xs text-muted tabular-nums">{counts.total}</span>
    {/if}
  </a>
{/snippet}

<nav class="flex h-full w-60 shrink-0 flex-col gap-6 border-r border-line bg-sidebar p-4">
  <div class="flex items-center gap-2.5 px-2 pt-1">
    <img src="/favicon.svg" alt="" class="size-7" />
    <span class="font-bold">S.O.K Server</span>
  </div>

  <div class="flex flex-col gap-1">
    {@render link(ANALYSIS)}
  </div>

  <div class="flex flex-col gap-1">
    {#each MEDIA_PAGES as page (page.path)}
      {@render link(page)}
    {/each}
  </div>

  <div class="mt-auto flex flex-col gap-1">
    {#each OTHER_PAGES as page (page.path)}
      {@render link(page)}
    {/each}
    {#if session.current?.auth === "login"}
      <div class="mt-3 flex items-center justify-between border-t border-line px-3 pt-3 text-sm">
        <span class="truncate text-muted">{session.current.username}</span>
        <button class="font-medium text-accent hover:underline" onclick={logOut}>
          {t("web_log_out", "Log out")}
        </button>
      </div>
    {/if}
  </div>
</nav>
