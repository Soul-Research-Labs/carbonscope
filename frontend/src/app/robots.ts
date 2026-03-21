import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/dashboard/", "/settings/", "/billing/"],
      },
    ],
    sitemap: `${process.env.NEXT_PUBLIC_SITE_URL || "https://carbonscope.io"}/sitemap.xml`,
  };
}
