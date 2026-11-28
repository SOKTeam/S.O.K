<script lang="ts">
  import { t } from "../../lib/i18n.svelte";

  // The folders of a role (the sources, or the destinations of a type), as a
  // group of the Folders block: its name, the paths (the first one is the
  // default), a cross to remove each, and "Parcourir…", which opens the
  // folder browser in the scene. The paths are those the server sees.
  let {
    label,
    paths,
    browsing = false,
    error = "",
    onbrowse,
    onremove,
  }: {
    label: string;
    paths: string[];
    /** The browser of the scene is open for this role. */
    browsing?: boolean;
    error?: string;
    onbrowse: () => void;
    onremove: (path: string) => void;
  } = $props();
</script>

<div class="group grid grid-cols-[90px_minmax(0,1fr)_auto] items-start gap-x-3.5 gap-y-1 py-[7px]">
  <span class={["pt-[3px] text-[14px]", browsing ? "text-ink" : "text-muted"]}>{label}</span>
  <div class="grid gap-1">
    {#each paths as path, index (path)}
      <div class="flex min-w-0 items-center gap-2.5 font-mono text-[13px] leading-6 text-ink">
        <!-- Cut at the start: the end of a path tells it apart. -->
        <span class="min-w-0 truncate [direction:rtl]" title={path}><bdi>{path}</bdi></span>
        {#if index === 0 && paths.length > 1}
          <span class="shrink-0 font-sans text-[12px] text-faint"
            >{t("web_default_folder", "default")}</span
          >
        {/if}
        <button
          type="button"
          class="ml-auto shrink-0 cursor-pointer px-1 font-sans text-[15px] text-faint opacity-0 group-hover:opacity-100 hover:text-ink focus-visible:opacity-100"
          title={t("web_remove", "Remove")}
          aria-label={t("web_remove_folder", "Remove {path}", { path })}
          onclick={() => onremove(path)}
        >
          ×
        </button>
      </div>
    {/each}
    {#if !paths.length}
      <div class="text-[13px] leading-6 text-faint">{t("web_no_folder", "No folder")}</div>
    {/if}
    {#if error}
      <p class="text-[13px] leading-[1.45] text-danger" role="alert">{error}</p>
    {/if}
  </div>
  <button type="button" class="key key-sm -mt-0.5" aria-pressed={browsing} onclick={onbrowse}>
    {t("web_browse", "Browse…")}
  </button>
</div>
