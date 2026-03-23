/**
 * Curated species registry for the Species Spotlight view.
 *
 * Defines charisma groups (visual sections) and rarity tiers (ranking weights).
 * Matching is case-insensitive substring against the `matchPatterns` array,
 * which handles canonical names, common variants, and plural forms.
 */

export interface SpotlightSpecies {
  /** Display name */
  name: string;
  /** Patterns to match against sighting species strings (case-insensitive substring) */
  matchPatterns: string[];
  /** Rarity tier */
  tier: RarityTier;
}

export interface SpotlightGroup {
  /** Machine key */
  key: string;
  /** Display label */
  label: string;
  /** Group emoji */
  emoji: string;
  /** Species in this group */
  species: SpotlightSpecies[];
}

export type RarityTier = 'once' | 'thrill' | 'notable' | 'regulars';

export const TIER_LABELS: Record<RarityTier, string> = {
  once: 'Once in a Lifetime',
  thrill: 'Always a Thrill',
  notable: 'Notable',
  regulars: 'The Regulars',
};

/** Lower = higher priority */
export const TIER_WEIGHT: Record<RarityTier, number> = {
  once: 0,
  thrill: 1,
  notable: 2,
  regulars: 3,
};

export const SPOTLIGHT_GROUPS: SpotlightGroup[] = [
  {
    key: 'giants',
    label: 'The Giants',
    emoji: '🐋',
    species: [
      { name: 'Blue Whale', matchPatterns: ['blue whale'], tier: 'once' },
      { name: 'Orca', matchPatterns: ['orca', 'killer whale'], tier: 'once' },
      { name: 'Fin Whale', matchPatterns: ['fin whale'], tier: 'thrill' },
      { name: 'Humpback Whale', matchPatterns: ['humpback whale'], tier: 'thrill' },
      { name: 'Sperm Whale', matchPatterns: ['sperm whale'], tier: 'thrill' },
      { name: 'Gray Whale', matchPatterns: ['gray whale', 'grey whale'], tier: 'notable' },
      { name: 'Minke Whale', matchPatterns: ['minke whale'], tier: 'notable' },
    ],
  },
  {
    key: 'frequent-flyers',
    label: 'The Frequent Flyers',
    emoji: '🐬',
    species: [
      { name: 'Dall\'s Porpoise', matchPatterns: ["dall's porpoise", 'dalls porpoise'], tier: 'thrill' },
      { name: 'Pacific White-Sided Dolphin', matchPatterns: ['pacific white-sided dolphin', 'pacific white sided dolphin'], tier: 'notable' },
      { name: "Risso's Dolphin", matchPatterns: ["risso's dolphin", 'rissos dolphin'], tier: 'notable' },
      { name: 'Common Dolphin', matchPatterns: ['common dolphin'], tier: 'regulars' },
      { name: 'Bottlenose Dolphin', matchPatterns: ['bottlenose dolphin'], tier: 'regulars' },
    ],
  },
  {
    key: 'predators',
    label: 'The Predators',
    emoji: '🦈',
    species: [
      { name: 'White Shark', matchPatterns: ['white shark', 'great white shark'], tier: 'once' },
      { name: 'Mako Shark', matchPatterns: ['mako shark'], tier: 'thrill' },
      { name: 'Thresher Shark', matchPatterns: ['thresher shark'], tier: 'thrill' },
      { name: 'Blue Shark', matchPatterns: ['blue shark'], tier: 'notable' },
    ],
  },
  {
    key: 'bucket-list',
    label: 'The Bucket List',
    emoji: '🌟',
    species: [
      { name: 'Octopus', matchPatterns: ['octopus', 'lilliput'], tier: 'once' },
      { name: 'Sea Otter', matchPatterns: ['sea otter', 'otter'], tier: 'once' },
      { name: 'Mola Mola', matchPatterns: ['mola mola', 'sunfish'], tier: 'once' },
      { name: 'Sea Turtle', matchPatterns: ['sea turtle', 'turtle'], tier: 'once' },
      { name: 'Moray Eel', matchPatterns: ['moray eel', 'moray'], tier: 'thrill' },
      { name: 'Garibaldi', matchPatterns: ['garibaldi'], tier: 'notable' },
    ],
  },
  {
    key: 'haul-out',
    label: 'The Haul-Out Crew',
    emoji: '🦭',
    species: [
      { name: 'Elephant Seal', matchPatterns: ['elephant seal'], tier: 'thrill' },
      { name: 'California Sea Lion', matchPatterns: ['california sea lion'], tier: 'regulars' },
      { name: 'Harbor Seal', matchPatterns: ['harbor seal'], tier: 'regulars' },
    ],
  },
  {
    key: 'sea-birds',
    label: 'The Sea Birds',
    emoji: '🦅',
    species: [
      { name: 'Albatross', matchPatterns: ['albatross'], tier: 'thrill' },
      { name: 'Black-vented Shearwater', matchPatterns: ['shearwater'], tier: 'notable' },
      { name: 'Brown Pelican', matchPatterns: ['brown pelican', 'pelican'], tier: 'regulars' },
      { name: 'Double-crested Cormorant', matchPatterns: ['double-crested cormorant', 'cormorant'], tier: 'regulars' },
    ],
  },
];

/**
 * Build a flat lookup from species name to its group + tier info.
 * Useful for quick matching in the aggregation hook.
 */
export const SPECIES_BY_NAME = new Map<string, { group: SpotlightGroup; species: SpotlightSpecies }>();

for (const group of SPOTLIGHT_GROUPS) {
  for (const sp of group.species) {
    SPECIES_BY_NAME.set(sp.name, { group, species: sp });
  }
}
