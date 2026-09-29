import type { APIRoute } from 'astro';

export const GET: APIRoute = async (context) => {
  const postImports = import.meta.glob<{
    file: string;
    frontmatter: {
      title: string;
      pubDate: string;
      slug?: string;
      description?: string;
      tags?: string[];
      [key: string]: any;
    };
  }>('../content/posts/*.md', { eager: true });

  const siteUrl = context.site ? new URL(context.site) : new URL('https://BWDSF3104.github.io/my-auto-blog/');
  const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');

  const posts = Object.entries(postImports).map(([path, module]) => {
    const filename = path.split('/').pop()?.replace('.md', '') || '';
    const slug = module.frontmatter.slug || filename;
    const dateStr = module.frontmatter.pubDate;
    let isoDate: string;
    try {
      isoDate = new Date(dateStr).toISOString();
    } catch {
      isoDate = new Date().toISOString();
    }

    const postPath = `${basePath}/posts/${slug}`;
    const fullUrl = new URL(postPath, siteUrl).href;

    return {
      url: fullUrl,
      lastmod: isoDate,
    };
  });

  posts.sort((a, b) => new Date(b.lastmod).getTime() - new Date(a.lastmod).getTime());

  const homePath = basePath ? `${basePath}/` : '/';
  const homeUrl = new URL(homePath, siteUrl).href;

  const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${homeUrl}</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
${posts
  .map(
    (post) => `  <url>
    <loc>${post.url}</loc>
    <lastmod>${post.lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`
  )
  .join('\n')}
</urlset>`;

  return new Response(sitemapXml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
    },
  });
};
