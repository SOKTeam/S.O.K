<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import type { Rename } from "../lib/renames.svelte";
  import { follow, href } from "../lib/router.svelte";

  // The rename running, or the result of the last one, above the rows.
  let { rename, ondismiss }: { rename: Rename; ondismiss: () => void } = $props();

  const result = $derived(rename.result);
  const left = $derived([
    ...(result?.skipped ?? []).map((s) => ({ file: s.file, why: s.reason })),
    ...(result?.errors ?? []).map((e) => ({ file: e.file, why: e.error })),
  ]);

  function fileName(path: string): string {
    return path.split("/").pop() ?? path;
  }
</script>

<div
  class={[
    "mt-4 rounded-xl border p-4 text-sm",
    rename.status === "failed" || left.length ? "border-warn/30 bg-warn/5" : "border-line bg-card",
  ]}
  role="status"
>
  {#if rename.status === "running"}
    {@const progress = rename.progress}
    <p class="font-semibold">
      {progress?.total
        ? t("web_renaming_progress", "Renaming… {done} / {total}", {
            done: progress.done,
            total: progress.total,
          })
        : t("web_renaming", "Renaming…")}
    </p>
    <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-hover">
      <div
        class="h-full rounded-full bg-accent transition-all"
        style:width={progress?.total ? `${(100 * progress.done) / progress.total}%` : "10%"}
      ></div>
    </div>
  {:else}
    <div class="flex items-start justify-between gap-4">
      <div>
        {#if rename.status === "failed"}
          <p class="font-semibold text-error">
            {t("web_rename_failed", "The rename failed: {message}", {
              message: rename.error?.message ?? rename.error?.code ?? "",
            })}
          </p>
        {:else}
          <p class="font-semibold">
            {t("web_renamed_count", "{n} files renamed.", { n: result?.renamed ?? 0 })}
            {#if result?.subtitles}
              <span class="font-normal text-muted">
                {t("with_subtitles", "With {0} subtitle(s).", { 0: result.subtitles })}
              </span>
            {/if}
          </p>
        {/if}
        {#if left.length}
          <p class="mt-2 text-warn">
            {t("web_rename_left", "{n} files stay on their row:", { n: left.length })}
          </p>
          <ul class="mt-1 flex flex-col gap-0.5 text-xs">
            {#each left as item (item.file)}
              <li>
                <span class="font-mono">{fileName(item.file)}</span>
                <span class="text-muted">· {item.why}</span>
              </li>
            {/each}
          </ul>
        {/if}
        {#if result?.renamed}
          <a
            href={href("/history")}
            onclick={follow}
            class="mt-2 inline-block text-accent hover:underline"
          >
            {t("web_see_history", "See the history, to undo it")}
          </a>
        {/if}
      </div>
      <button
        type="button"
        class="rounded p-1 text-muted hover:bg-hover hover:text-fg"
        aria-label={t("web_close", "Close")}
        onclick={ondismiss}
      >
        ✕
      </button>
    </div>
  {/if}
</div>
