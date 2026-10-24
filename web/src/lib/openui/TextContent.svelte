<script lang="ts">
  let { props }: { props: { text?: string } } = $props();
</script>

<p class="whitespace-pre-wrap break-words text-[15px] leading-7">{props.text ?? ''}</p>
