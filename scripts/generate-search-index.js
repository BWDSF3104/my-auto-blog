import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as yaml from 'js-yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const postsDir = resolve(projectRoot, 'src', 'content', 'posts');
const publicDir = resolve(projectRoot, 'public');

function stripHtml(html) {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function parseFrontmatter(content) {
  const match = content.match(/^\uFEFF?---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return { data: {}, body: content };
  const data = yaml.load(match[1], { schema: yaml.JSON_SCHEMA }) || {};
  const body = content.slice(match[0].length);
  return { data, body };
}

function slugFromFilename(filename) {
  return basename(filename, '.md');
}

const index = [];

const files = readdirSync(postsDir).filter(f => f.endsWith('.md'));

for (const file of files) {
  const filePath = resolve(postsDir, file);
  if (!statSync(filePath).isFile()) continue;

  const content = readFileSync(filePath, 'utf-8');
  const { data, body } = parseFrontmatter(content);
  const bodyText = stripHtml(body);

  index.push({
    title: data.title || '',
    slug: slugFromFilename(file),
    pubDate: data.pubDate || '',
    tags: data.tags || [],
    excerpt: bodyText.slice(0, 200),
    body: bodyText,
  });
}

index.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime());

writeFileSync(
  resolve(publicDir, 'search-index.json'),
  JSON.stringify(index, null, 2),
  'utf-8'
);

console.log(`Search index generated: ${index.length} posts`);
