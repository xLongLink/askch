import { defineComponent } from "@openuidev/react-lang";
import { Heading } from "@astryxdesign/core/Heading";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { z } from "zod/v4";

const chartProps = z
  .object({
    title: z.string().trim().min(1).max(200),
    type: z.enum(["line", "bar"]),
    xLabel: z.string().trim().min(1).max(100),
    yLabel: z.string().trim().min(1).max(100),
    labels: z.array(z.string().trim().min(1).max(100)).min(1).max(100),
    series: z
      .array(
        z.object({
          name: z.string().trim().min(1).max(100),
          values: z.array(z.number().finite().nullable()).min(1).max(100),
        }),
      )
      .min(1)
      .max(4),
  })
  .refine((data) => data.series.every((series) => series.values.length === data.labels.length), {
    message: "Each series must have one value per label; use null for missing values.",
  });

const colors = ["#b00000", "#2563eb", "#15803d", "#9333ea"];

export const chart = defineComponent({
  name: "Chart",
  description:
    "A line or bar chart of real data. Include axis labels and units. Supply 1–100 labels and 1–4 named series, each with one numeric value per label (null for missing data).",
  props: chartProps,
  component: ({ props }) => {
    // Validate generated data before passing it to the chart library.
    const data = chartProps.parse(props);
    const rows = data.labels.map((label, index) => ({
      label,
      ...Object.fromEntries(
        data.series.map((series, seriesIndex) => [seriesIndex, series.values[index]]),
      ),
    }));

    return (
      <figure className="chart">
        <Heading level={3}>{data.title}</Heading>
        <div className="chart-plot">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <ComposedChart
              data={rows}
              accessibilityLayer
              margin={{ top: 16, right: 16, bottom: 24, left: 16 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" label={{ value: data.xLabel, position: "bottom" }} />
              <YAxis
                width={70}
                label={{ value: data.yLabel, angle: -90, position: "insideLeft" }}
              />
              <Tooltip />
              <Legend verticalAlign="top" />
              {data.series.map((series, index) =>
                data.type === "line" ? (
                  <Line
                    key={index}
                    dataKey={String(index)}
                    name={series.name}
                    stroke={colors[index]}
                    isAnimationActive={false}
                  />
                ) : (
                  <Bar
                    key={index}
                    dataKey={String(index)}
                    name={series.name}
                    fill={colors[index]}
                    isAnimationActive={false}
                  />
                ),
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <details className="chart-data">
          <summary>
            {data.xLabel} / {data.yLabel}
          </summary>
          <table>
            <caption>{data.title}</caption>
            <thead>
              <tr>
                <th scope="col">{data.xLabel}</th>
                {data.series.map((series, index) => (
                  <th key={index} scope="col">
                    {series.name} ({data.yLabel})
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.labels.map((label, index) => (
                <tr key={index}>
                  <th scope="row">{label}</th>
                  {data.series.map((series, seriesIndex) => (
                    <td key={seriesIndex}>{series.values[index] ?? "—"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </figure>
    );
  },
});
