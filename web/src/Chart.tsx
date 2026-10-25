import { defineComponent, useIsStreaming } from "@openuidev/react-lang";
import { useId } from "react";
import { ChevronDown } from "lucide-react";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Area, Bar, CartesianGrid, ComposedChart, XAxis, YAxis } from "recharts";
import { z } from "zod/v4";

const seriesProps = z.object({
  name: z.string().trim().min(1).max(100),
  values: z.array(z.number().finite().nullable()).min(1).max(100),
});

const chartProps = z
  .object({
    title: z.string().trim().min(1).max(200),
    type: z.enum(["line", "bar"]),
    xLabel: z.string().trim().min(1).max(100),
    yLabel: z.string().trim().min(1).max(100),
    labels: z.array(z.string().trim().min(1).max(100)).min(1).max(100),
    series: z.union([z.array(seriesProps).min(1).max(4), seriesProps]),
  })
  .refine(
    (data) => {
      const series = Array.isArray(data.series) ? data.series : [data.series];
      return series.every((series) => series.values.length <= data.labels.length);
    },
    { message: "Series values must not exceed the number of labels." },
  );

export const chart = defineComponent({
  name: "Chart",
  description:
    "A line or bar chart of real data. Include axis labels and units. Supply 1–100 labels and an array of 1–4 named series (a single series object is also accepted). Use null for missing data; omitted trailing values appear as gaps.",
  props: chartProps,
  component: ({ props }) => {
    // Wait for complete streamed props without accepting invalid finished output.
    const isStreaming = useIsStreaming();
    const chartId = useId().replace(/[^a-zA-Z0-9_-]/g, "");
    const result = chartProps.safeParse(props);
    if (!result.success) {
      if (isStreaming) return null;
      throw result.error;
    }

    // Pass only validated data to the chart library.
    const data = result.data;
    const series = Array.isArray(data.series) ? data.series : [data.series];
    const config: ChartConfig = Object.fromEntries(
      series.map((series, index) => [
        `series${index}`,
        { label: series.name, color: `var(--chart-${index + 1})` },
      ]),
    );
    const rows = data.labels.map((label, index) => ({
      label,
      ...Object.fromEntries(
        series.map((series, seriesIndex) => [`series${seriesIndex}`, series.values[index] ?? null]),
      ),
    }));

    return (
      <figure className="m-0 min-w-0 w-full space-y-5" aria-label={data.title}>
        <figcaption className="space-y-1">
          <h3 className="text-base font-semibold tracking-tight">{data.title}</h3>
          <p className="text-xs text-muted-foreground">{data.yLabel}</p>
        </figcaption>
        <ChartContainer config={config} className="h-64 w-full aspect-auto sm:h-72">
          <ComposedChart
            data={rows}
            accessibilityLayer
            margin={{ top: 8, right: 12, bottom: 8, left: 0 }}
          >
            <defs>
              {series.map((_, index) => (
                <linearGradient
                  key={index}
                  id={`${chartId}-fill-${index}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={`var(--color-series${index})`} stopOpacity={0.2} />
                  <stop
                    offset="100%"
                    stopColor={`var(--color-series${index})`}
                    stopOpacity={0.02}
                  />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tickMargin={12}
              minTickGap={32}
            />
            <YAxis
              width={48}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(value: number) =>
                value.toLocaleString(undefined, { notation: "compact", maximumFractionDigits: 1 })
              }
            />
            <ChartTooltip
              cursor={
                data.type === "bar"
                  ? { fill: "var(--muted)", opacity: 0.5 }
                  : { stroke: "var(--border)", strokeDasharray: "4 4" }
              }
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => (
                    <>
                      {data.xLabel}: {label}
                    </>
                  )}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent className="flex-wrap pt-5" />} />
            {series.map((series, index) =>
              data.type === "line" ? (
                <Area
                  key={index}
                  dataKey={`series${index}`}
                  name={series.name}
                  type="linear"
                  stroke={`var(--color-series${index})`}
                  strokeWidth={2.5}
                  fill={`url(#${chartId}-fill-${index})`}
                  fillOpacity={1}
                  dot={rows.length === 1}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--background)" }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              ) : (
                <Bar
                  key={index}
                  dataKey={`series${index}`}
                  name={series.name}
                  fill={`var(--color-series${index})`}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={48}
                  isAnimationActive={false}
                />
              ),
            )}
          </ComposedChart>
        </ChartContainer>
        <p className="text-center text-xs text-muted-foreground">{data.xLabel}</p>
        <details className="group border-t pt-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-sm text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
            {data.xLabel} / {data.yLabel}
            <ChevronDown
              className="size-4 transition-transform group-open:rotate-180"
              aria-hidden="true"
            />
          </summary>
          <Table className="mt-3 text-xs tabular-nums">
            <TableCaption className="text-xs">{data.title}</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">{data.xLabel}</TableHead>
                {series.map((series, index) => (
                  <TableHead key={index} scope="col" className="text-right">
                    {series.name} ({data.yLabel})
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.labels.map((label, index) => (
                <TableRow key={index}>
                  <TableHead scope="row" className="font-normal">
                    {label}
                  </TableHead>
                  {series.map((series, seriesIndex) => (
                    <TableCell key={seriesIndex} className="text-right">
                      {series.values[index]?.toLocaleString() ?? "—"}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </details>
      </figure>
    );
  },
});
