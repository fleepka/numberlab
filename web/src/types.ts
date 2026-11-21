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
  xp: number;
  level: number;
  xp_to_next: number;
  is_admin: boolean;
  spins: number;
  duels_won: number;
  duels_lost: number;
  best_score: number;
  streak: number;
  spin_ready_in: number;
};

export type MeResponse = {
  user: UserT;
  garage_count: number;
  top: PlateT[];
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

export type Tx = {
  id: number;
  currency: string;
  delta: number;
  reason: string;
  ref: string | null;
  created_at: string | null;
};
