const PALETTE = [
  { bg: 'bg-blue-50', darkBg: 'dark:bg-blue-900/30', text: 'text-blue-600', darkText: 'dark:text-blue-400', hover: 'hover:bg-blue-100', darkHover: 'dark:hover:bg-blue-900/50' },
  { bg: 'bg-emerald-50', darkBg: 'dark:bg-emerald-900/30', text: 'text-emerald-600', darkText: 'dark:text-emerald-400', hover: 'hover:bg-emerald-100', darkHover: 'dark:hover:bg-emerald-900/50' },
  { bg: 'bg-violet-50', darkBg: 'dark:bg-violet-900/30', text: 'text-violet-600', darkText: 'dark:text-violet-400', hover: 'hover:bg-violet-100', darkHover: 'dark:hover:bg-violet-900/50' },
  { bg: 'bg-amber-50', darkBg: 'dark:bg-amber-900/30', text: 'text-amber-600', darkText: 'dark:text-amber-400', hover: 'hover:bg-amber-100', darkHover: 'dark:hover:bg-amber-900/50' },
  { bg: 'bg-rose-50', darkBg: 'dark:bg-rose-900/30', text: 'text-rose-600', darkText: 'dark:text-rose-400', hover: 'hover:bg-rose-100', darkHover: 'dark:hover:bg-rose-900/50' },
  { bg: 'bg-cyan-50', darkBg: 'dark:bg-cyan-900/30', text: 'text-cyan-600', darkText: 'dark:text-cyan-400', hover: 'hover:bg-cyan-100', darkHover: 'dark:hover:bg-cyan-900/50' },
  { bg: 'bg-orange-50', darkBg: 'dark:bg-orange-900/30', text: 'text-orange-600', darkText: 'dark:text-orange-400', hover: 'hover:bg-orange-100', darkHover: 'dark:hover:bg-orange-900/50' },
  { bg: 'bg-pink-50', darkBg: 'dark:bg-pink-900/30', text: 'text-pink-600', darkText: 'dark:text-pink-400', hover: 'hover:bg-pink-100', darkHover: 'dark:hover:bg-pink-900/50' },
  { bg: 'bg-teal-50', darkBg: 'dark:bg-teal-900/30', text: 'text-teal-600', darkText: 'dark:text-teal-400', hover: 'hover:bg-teal-100', darkHover: 'dark:hover:bg-teal-900/50' },
  { bg: 'bg-indigo-50', darkBg: 'dark:bg-indigo-900/30', text: 'text-indigo-600', darkText: 'dark:text-indigo-400', hover: 'hover:bg-indigo-100', darkHover: 'dark:hover:bg-indigo-900/50' },
  { bg: 'bg-lime-50', darkBg: 'dark:bg-lime-900/30', text: 'text-lime-600', darkText: 'dark:text-lime-400', hover: 'hover:bg-lime-100', darkHover: 'dark:hover:bg-lime-900/50' },
  { bg: 'bg-fuchsia-50', darkBg: 'dark:bg-fuchsia-900/30', text: 'text-fuchsia-600', darkText: 'dark:text-fuchsia-400', hover: 'hover:bg-fuchsia-100', darkHover: 'dark:hover:bg-fuchsia-900/50' },
];

export function getTagColor(tag: string): typeof PALETTE[0] {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = (hash * 31 + tag.charCodeAt(i)) & 0x7fffffff;
  }
  return PALETTE[hash % PALETTE.length];
}
