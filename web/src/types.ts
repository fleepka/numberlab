export type Factor = { title: string; points: number };

export type PlateT = {
  id: number;
  code: string;
  rarity: string;
  rarity_label?: string;
  score: number;
  price: number;
  stars: number;
  is_paid: boolean;
  source: string;
  factors?: Factor[];
  created_at: string | null;
};

export type UserT = {
  id: number;
  tg_id: number;
  username: string | null;
  first_name: string;
  photo_url: string | null;
  coins: number;
  gems: number;
  energy: number;
  energy_max: number;
  energy_in: number;
  xp: number;
  level: number;
  xp_to_next: number;
  is_admin: boolean;
  spins: number;
  duels_won: number;
  duels_lost: number;
  best_score: number;
  streak: number;
};

export type ChatMessage = {
  id: number;
  user_id: number;
  username: string | null;
  first_name: string | null;
  text: string;
  created_at: string;
};

export type PassReward = {
  coins: number;
  gems: number;
  energy: number;
  ticket: string;
  claimed: boolean;
};

export type PassLevel = {
  level: number;
  unlocked: boolean;
  free: PassReward;
  premium: PassReward;
};

export type PassData = {
  points: number;
  level: number;
  max_level: number;
  points_per_level: number;
  premium: boolean;
  price_stars: number;
  levels: PassLevel[];
};

export type HuntT = {
  title: string;
  kind: string;
  value: string;
  day: string;
  done: boolean;
  claimed: boolean;
  reward_coins: number;
  reward_energy: number;
  reward_ticket: string | null;
};

export type TicketT = {
  rarity: string;
  label: string;
  count: number;
};

export type GarageIncome = {
  rate: number;
  available: number;
  total: number;
  plates: number;
  cap_hours: number;
  hours: number;
};

export type GarageData = {
  plates: PlateT[];
  income: GarageIncome;
};

export type MeResponse = {
  user: UserT;
  garage_count: number;
  top: PlateT[];
  stakes: Record<string, number>;
};

export type DuelT = {
  id: number;
  bet: number;
  status: string;
  creator_id: number;
  creator: string | null;
  opponent_id: number | null;
  winner_id: number | null;
  created_at: string | null;
  plates?: PlateT[];
};

export type JoinResult = {
  duel: DuelT;
  plates: PlateT[];
  winner_id: number | null;
  you_won: boolean;
  payout: number;
  coins: number;
};

export type Offer = {
  code: string;
  rarity: string;
  score: number;
  price: number;
  stars: number;
};

export type CollectionT = {
  id: number;
  code: string;
  title: string;
  description: string;
  target: number;
  progress: number;
  done: boolean;
  claimed: boolean;
  reward_coins: number;
  reward_gems: number;
  reward_xp: number;
};

export type TaskT = {
  code: string;
  title: string;
  description: string;
  kind: string;
  target: number;
  progress: number;
  done: boolean;
  claimed: boolean;
  reward_coins: number;
  reward_energy: number;
  reward_gems: number;
};

export type RatingItem = {
  user_id: number;
  username: string | null;
  first_name: string | null;
  total: number;
  plates: number;
};

export type RatingData = {
  period?: string;
  items: RatingItem[];
  me: { rank: number; total: number; plates: number };
};

export type LadderStep = {
  need: number;
  title: string;
  coins: number;
  gems: number;
  energy: number;
  done: boolean;
};

export type FriendsData = {
  invites: number;
  link: string;
  ladder: LadderStep[];
};

export type Tx = {
  id: number;
  currency: string;
  delta: number;
  reason: string;
  ref: string | null;
  created_at: string | null;
};
