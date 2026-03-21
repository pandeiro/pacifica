/**
 * Emoji mapping for wildlife species.
 *
 * Two-tier lookup:
 * 1. Exact species name (case-insensitive) — checked first
 * 2. Substring match against an ordered list — first match short-circuits
 *
 * To add a new mapping, put the most specific substring first.
 */

/** Exact matches (case-insensitive, full species name) */
const EXACT_SPECIES: Record<string, string> = {
  // Whales
  'gray whale': '🐋',
  'grey whale': '🐋',
  'humpback whale': '🐋',
  'blue whale': '🐋',
  'fin whale': '🐋',
  'minke whale': '🐋',
  'sperm whale': '🐋',
  'orca': '🐋',
  'killer whale': '🐋',

  // Dolphins
  'bottlenose dolphin': '🐬',
  'common dolphin': '🐬',
  'pacific white-sided dolphin': '🐬',
  'risso\'s dolphin': '🐬',

  // Sharks
  'white shark': '🦈',
  'great white shark': '🦈',

  // Pinnipeds
  'california sea lion': '🦭',
  'harbor seal': '🦭',

  // Birds
  'brown pelican': '🦅',
  'double-crested cormorant': '🦅',
  'brandt\'s cormorant': '🦅',

  // Fish
  'garibaldi': '🐠',
  'mola mola': '🐟',
};

/**
 * Substring matches — first match wins, order matters.
 * Put more specific patterns before generic ones.
 */
const SUBSTRING_RULES: [string, string][] = [
  // Fish — specific before generic
  ['garibaldi', '🐠'],
  ['mola mola', '🐟'],
  ['mola', '🐟'],
  ['sunfish', '🐟'],
  ['sheephead', '🐟'],
  ['grunion', '🐟'],
  ['trout', '🐟'],
  ['surfperch', '🐟'],
  ['silverside', '🐟'],
  ['sargo', '🐟'],
  ['opaleye', '🐟'],
  ['halibut', '🐟'],
  ['croaker', '🐟'],
  ['sea chub', '🐟'],
  ['kelp bass', '🐟'],
  ['flying fish', '🐟'],
  ['marlin', '🐟'],
  ['swordfish', '🐟'],
  ['shark', '🦈'],

  // Whales
  ['orca', '🐋'],
  ['killer whale', '🐋'],
  ['whale', '🐋'],

  // Dolphins / porpoises
  ['dolphin', '🐬'],
  ['porpoise', '🐬'],

  // Pinnipeds
  ['sea lion', '🦭'],
  ['elephant seal', '🦭'],
  ['seal', '🦭'],

  // Birds
  ['pelican', '🦅'],
  ['cormorant', '🦅'],
  ['albatross', '🦅'],
  ['tern', '🐦'],
  ['gull', '🐦'],
  ['murre', '🐦'],
  ['puffin', '🐦'],
  ['shearwater', '🐦'],
  ['falcon', '🐦'],

  // Reptiles
  ['turtle', '🐢'],
];

/**
 * Get emoji for a species name.
 * @param species - Species name
 * @returns Emoji character, or '🐾' as fallback
 */
export function getSpeciesEmoji(species: string): string {
  const key = species.toLowerCase();

  // Tier 1: exact match
  if (EXACT_SPECIES[key]) {
    return EXACT_SPECIES[key];
  }

  // Tier 2: first substring match wins
  for (const [substr, emoji] of SUBSTRING_RULES) {
    if (key.includes(substr)) {
      return emoji;
    }
  }

  return '🐾';
}
