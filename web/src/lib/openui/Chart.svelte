<script lang="ts">
  import { onMount } from 'svelte';

  let chartModule = $state.raw<typeof import('chart.js')>();
  onMount(() => {
    let active = true;
    void import('chart.js').then((module) => {
      if (!active) return;
      module.Chart.register(module.CategoryScale, module.LinearScale, module.BarController, module.LineController, module.PieController, module.DoughnutController, module.ArcElement, module.BarElement, module.LineElement, module.PointElement, module.Tooltip, module.Legend);
      chartModule = module;
    });
    return () => { active = false; };
  });

  let { props }: {
    props: {
      title?: string;
      type?: 'bar' | 'line' | 'pie' | 'doughnut';
      labels?: string[];
      values?: number[];
      datasetLabel?: string;
    };
  } = $props();

  let canvas = $state<HTMLCanvasElement>();
  const colors = ['#ff0000', '#171717', '#737373', '#ff8080', '#b30000', '#a3a3a3'];
  const points = $derived((props.labels ?? []).flatMap((label, index) => {
    const value = props.values?.[index];
    return typeof value === 'number' && Number.isFinite(value) ? [{ label, value }] : [];
  }));

  $effect(() => {
    if (!canvas || !chartModule || !points.length) return;
    const type = props.type ?? 'bar';
    const circular = type === 'pie' || type === 'doughnut';
    const chart = new chartModule.Chart(canvas, {
      type,
      data: {
        labels: points.map((point) => point.label),
        datasets: [{
          label: props.datasetLabel ?? props.title ?? 'Data',
          data: points.map((point) => point.value),
          backgroundColor: circular ? points.map((_, index) => colors[index % colors.length]) : colors[0],
          borderColor: circular ? '#ffffff' : colors[0],
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: circular, position: 'bottom' } },
        scales: circular ? {} : { y: { beginAtZero: true }, x: { grid: { display: false } } },
      },
    });
    return () => chart.destroy();
  });
</script>

<figure class="min-w-0 space-y-3">
  {#if props.title}<figcaption class="text-sm font-medium">{props.title}</figcaption>{/if}
  <div class="relative h-64">
    <canvas bind:this={canvas} aria-label={props.title ?? props.datasetLabel ?? 'Chart'}>
      {#each points as point}<p>{point.label}: {point.value}</p>{/each}
    </canvas>
  </div>
</figure>
