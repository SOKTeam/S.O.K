<script lang="ts">
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.svelte";
  import { ANALYSIS, MEDIA_PAGES, OTHER_PAGES, type Page } from "../lib/pages";
  import { follow, router } from "../lib/router.svelte";
  import { analysis } from "../lib/scan.svelte";
  import { logOut, session } from "../lib/session.svelte";

  // The sidebar of the desktop app: the library, then the general pages.
</script>

{#snippet link(page: Page)}
  {@const current = router.path === page.path || router.path.startsWith(`${page.path}/`)}
  {@const counts = page.mediaType ? analysis.summary?.counts[page.mediaType] : undefined}
  <a
    href={page.path}
    onclick={follow}
    aria-current={current ? "page" : undefined}
    class={[
      "flex items-center gap-3 rounded-lg px-3 py-2 text-[15px]",
      current ? "bg-selected font-medium text-selected-fg" : "text-fg hover:bg-hover",
    ]}
  >
    <Icon
      name={page.icon}
      class={["size-4.5 shrink-0", current ? "text-selected-icon" : "text-icon"].join(" ")}
    />
    <span class="flex-1 truncate">{t(page.key, page.english)}</span>
    {#if counts?.total}
      <span class={["text-xs tabular-nums", !current && "text-muted"]}>
        {#if counts.ambiguous}
          <span
            class={["font-semibold", !current && "text-warn"]}
            title={t("status_ambiguous", "Pick one")}>{counts.ambiguous}</span
          >
          ·
        {/if}
        {counts.total}
      </span>
    {/if}
  </a>
{/snippet}

<nav class="flex h-full w-60 shrink-0 flex-col border-r border-line bg-sidebar px-3 pt-5 pb-3.5">
  <div class="flex items-center gap-2.5 px-2 pb-5">
    <img src="/favicon.svg" alt="" class="size-7" />
    <span class="font-bold">S.O.K Server</span>
  </div>

  <p class="label px-3 pb-1.5">{t("library", "Library")}</p>
  <div class="flex flex-col gap-0.5">
    {@render link(ANALYSIS)}
    {#each MEDIA_PAGES as page (page.path)}
      {@render link(page)}
    {/each}
  </div>

  <div class="mt-auto flex flex-col gap-0.5">
    <p class="label px-3 pb-1.5">{t("general", "General")}</p>
    {#each OTHER_PAGES as page (page.path)}
      {@render link(page)}
    {/each}
    {#if session.current?.auth === "login"}
      <div class="mt-2 flex items-center justify-between border-t border-line px-3 pt-3 text-sm">
        <span class="truncate text-muted">{session.current.username}</span>
        <button class="font-medium text-accent hover:underline" onclick={logOut}>
          {t("web_log_out", "Log out")}
        </button>
      </div>
    {/if}
  </div>
</nav>
