<script lang="ts">
  import { getTriggerAction } from '@openuidev/svelte-lang';
  import { Button } from '#lib/components/ui/button/index.js';
  let { props }: { props: { label?: string } } = $props();
  const triggerAction = getTriggerAction();
</script>

<div><Button variant="outline" class="h-auto whitespace-normal py-2 text-left" onclick={() => triggerAction(props.label ?? 'Tell me more')}>{props.label ?? 'Tell me more'}</Button></div>
