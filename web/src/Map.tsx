import { defineComponent, useIsStreaming } from "@openuidev/react-lang";
import { Heading } from "@astryxdesign/core/Heading";
import { HStack } from "@astryxdesign/core/HStack";
import { Text } from "@astryxdesign/core/Text";
import { Annotation, ComposableMap, Geographies, Geography, Marker } from "react-simple-maps/core";
import { z } from "zod/v4";
import cantons from "./cantons.json";

const cantonCode = z.enum([
  "AG",
  "AI",
  "AR",
  "BE",
  "BL",
  "BS",
  "FR",
  "GE",
  "GL",
  "GR",
  "JU",
  "LU",
  "NE",
  "NW",
  "OW",
  "SG",
  "SH",
  "SO",
  "SZ",
  "TG",
  "TI",
  "UR",
  "VD",
  "VS",
  "ZG",
  "ZH",
]);
const mapProps = z
  .object({
    title: z.string().trim().min(1).max(200),
    unit: z.string().trim().max(100),
    cantons: z
      .array(
        z.object({
          code: cantonCode,
          label: z.string().trim().min(1).max(100),
          value: z.number().finite().nullable(),
        }),
      )
      .max(26),
    markers: z
      .array(
        z.object({
          label: z.string().trim().min(1).max(100),
          longitude: z.number().min(5.9).max(10.6),
          latitude: z.number().min(45.8).max(47.9),
        }),
      )
      .max(20),
  })
  .refine((data) => data.cantons.length > 0 || data.markers.length > 0, {
    message: "Supply at least one canton or marker.",
  })
  .refine(
    (data) => new Set(data.cantons.map((canton) => canton.code)).size === data.cantons.length,
    {
      message: "Canton codes must be unique.",
    },
  );

const boundaries = { ...cantons, type: "FeatureCollection" as const };

export const map = defineComponent({
  name: "Map",
  description:
    "A Swiss canton map with optional numeric canton shading and labeled location markers. Supply up to 26 unique two-letter canton codes and 20 markers. Coordinates are WGS84 longitude/latitude within Switzerland's bounding box. Use null for missing canton values; pass empty arrays for unused layers. Boundaries are generalized historical outlines, not current administrative or navigation data.",
  props: mapProps,
  component: ({ props }) => {
    // Wait for complete streamed props without accepting invalid finished output.
    const isStreaming = useIsStreaming();
    const result = mapProps.safeParse(props);
    if (!result.success) {
      if (isStreaming) return null;
      throw result.error;
    }

    // Derive a shared sequential color scale from validated values.
    const data = result.data;
    const values = data.cantons.flatMap((canton) => (canton.value === null ? [] : [canton.value]));
    const minimum = values.length ? Math.min(...values) : 0;
    const maximum = values.length ? Math.max(...values) : 0;

    return (
      <figure className="m-0 min-w-0 w-full">
        <Heading level={3}>{data.title}</Heading>
        <ComposableMap
          className="block h-auto w-full"
          width={800}
          height={520}
          projection="geoMercator"
          projectionConfig={{ center: [8.25, 46.85], scale: 9000 }}
          role="img"
          aria-label={data.title}
        >
          <title>{data.title}</title>
          <Geographies geography={boundaries}>
            {({ geographies }) =>
              geographies.map((geography) => {
                // Keep source identifiers and the corresponding data lookup together.
                const code = cantonCode.parse(
                  z.string().parse(geography.properties?.code_hasc).slice(3),
                );
                const canton = data.cantons.find((entry) => entry.code === code);
                const value = canton?.value;
                const intensity =
                  value == null
                    ? null
                    : maximum === minimum
                      ? 0.6
                      : 0.2 + 0.65 * ((value - minimum) / (maximum - minimum));

                return (
                  <Geography
                    key={geography.rsmKey}
                    geography={geography}
                    fill={
                      intensity === null
                        ? "color-mix(in srgb, var(--color-text-secondary) 30%, var(--color-background-surface))"
                        : `hsl(210 65% ${95 - intensity * 60}%)`
                    }
                    stroke="var(--color-text-secondary)"
                    strokeWidth={1}
                  >
                    <title>
                      {canton?.label ?? code}: {value ?? "—"} {data.unit}
                    </title>
                  </Geography>
                );
              })
            }
          </Geographies>
          {data.markers.map((marker, index) => (
            <Marker key={index} coordinates={[marker.longitude, marker.latitude]}>
              <circle r={5} fill="#b00000" stroke="#fff" strokeWidth={1.5} />
              <title>{marker.label}</title>
            </Marker>
          ))}
          {data.markers.map((marker, index) => (
            <Annotation
              key={index}
              subject={[marker.longitude, marker.latitude]}
              dx={marker.longitude > 8.25 ? -18 : 18}
              dy={index % 2 === 0 ? -18 : 22}
              connectorProps={{ stroke: "#525252", strokeWidth: 1 }}
            >
              <text
                textAnchor={marker.longitude > 8.25 ? "end" : "start"}
                fontSize={13}
                fill="#171717"
                stroke="#fff"
                strokeWidth={3}
                paintOrder="stroke"
              >
                {marker.label}
              </text>
            </Annotation>
          ))}
        </ComposableMap>
        {values.length > 0 && (
          <HStack gap={3} vAlign="center" className="text-base" aria-label={data.unit}>
            <Text type="inherit">
              {minimum} {data.unit}
            </Text>
            <HStack as="span" className="map-scale h-3 flex-1" aria-hidden="true" />
            <Text type="inherit">
              {maximum} {data.unit}
            </Text>
          </HStack>
        )}
        <dl>
          {data.cantons.map((canton) => (
            <HStack
              key={canton.code}
              wrap="wrap"
              hAlign="between"
              vAlign="stretch"
              gap={2}
              className="border-b border-border"
            >
              <dt>
                {canton.label} ({canton.code})
              </dt>
              <dd className="m-0">
                {canton.value ?? "—"} {data.unit}
              </dd>
            </HStack>
          ))}
          {data.markers.map((marker, index) => (
            <HStack
              key={index}
              wrap="wrap"
              hAlign="between"
              vAlign="stretch"
              gap={2}
              className="border-b border-border"
            >
              <dt>{marker.label}</dt>
              <dd className="m-0">
                {marker.latitude}° N, {marker.longitude}° E
              </dd>
            </HStack>
          ))}
        </dl>
      </figure>
    );
  },
});
