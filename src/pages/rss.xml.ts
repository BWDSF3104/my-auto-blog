import type { APIRoute } from 'astro';

export const GET: APIRoute = async (context) => {
  const postImports = import.meta.glob<{
    file: string;
    frontmatter: {
      title: string;
      pubDate: string;
      description?: string;
      author?: string;
      tags?: string[];
      [key: string]: any;
    };
  }>('../content/posts/*.md', { eager: true });

  const siteUrl = context.site ? new URL(context.site) : new URL('https://BWDSF3104.github.io/my-auto-blog/');
  const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');

  const items = Object.entries(postImports).map(([path, module]) => {
    const filename = path.split('/').pop()?.replace('.md', '') || '';
    const { title, pubDate, description = '', author = 'AI Writer' } = module.frontmatter;

    let pubDateObj = new Date(pubDate);
    if (isNaN(pubDateObj.getTime())) {
      pubDateObj = new Date();
    }

    const postPath = `${basePath}/posts/${filename}`;
    const fullUrl = new URL(postPath, siteUrl).href;

    return {
      title,
      link: fullUrl,
      description,
      pubDate: pubDateObj.toUTCString(),
      author,
      rawDate: pubDateObj.getTime(),
    };
  });

  items.sort((a, b) => b.rawDate - a.rawDate);

  const homePath = basePath ? `${basePath}/` : '/';
  const homeUrl = new URL(homePath, siteUrl).href;

  const escapeXml = (unsafe: string) => {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  };

  const rssFeedUrl = new URL(`${basePath}/rss.xml`, siteUrl).href;

  const rssXml = `<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>BWD&apos;s AI Auto Blog</title>
    <link>${homeUrl}</link>
    <description>Gemini API × GitHub Actions による自動生成技術＆ストーリーブログ</description>
    <language>ja</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${rssFeedUrl}" rel="self" type="application/rss+xml" />
    ${items
      .map(
        (item) => `
    <item>
      <title>${escapeXml(item.title)}</title>
      <link>${item.link}</link>
      <guid isPermaLink="true">${item.link}</guid>
      <description>${escapeXml(item.description)}</description>
      <pubDate>${item.pubDate}</pubDate>
    </item>`
      )
      .join('')}
  </channel>
</rss>`;

  return new Response(rssXml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
    },
  });
};

