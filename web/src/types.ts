export type Factor = { title: string; points: number };

export type PlateT = {
  id: number;
  code: string;
  rarity: string;
  rarity_label?: string;
  country?: string;
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
  garage_slots: number;
  season_points: number;
  pass_premium: boolean;
  vip_until: string | null;
  frame: string;
  plate_skin: string;
  theme: string;
};

export type ThemeItem = {
  code: string;
  title: string;
  bg: string;
  surface: string;
  accent: string;
  accent2: string;
  text: string;
  muted: string;
};

export type NickT = {
  holding: boolean;
  days: number;
  claimed7: boolean;
  claimed14: boolean;
  next: number | null;
};

export type AdminUser = {
  id: number;
  tg_id: number;
  name: string;
  username: string | null;
  coins: number;
  gems: number;
  energy: number;
  level: number;
  spins: number;
  invites: number;
  is_banned: boolean;
  is_admin: boolean;
  garage_slots: number;
  vip_until: string | null;
  created_at: string | null;
  garage_count?: number;
  garage_value?: number;
  history?: { delta: number; currency: string; reason: string; created_at: string | null }[];
};

export type AdminMeta = {
  rarities: { code: string; label: string }[];
  countries: { code: string; title: string; flag: string }[];
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
  slots: number;
};

export type Country = {
  code: string;
  title: string;
  flag: string;
};

export type RankT = {
  title: string;
  index: number;
  total: number;
  next: number | null;
  next_title: string | null;
  progress: number;
};

export type MeResponse = {
  user: UserT;
  garage_count: number;
  rank: RankT;
  top: PlateT[];
  stakes: Record<string, number>;
  energy_costs: Record<string, number>;
  countries: Country[];
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

export type EnergyPack = {
  code: string;
  energy: number;
  price: number;
};

export type Product = {
  code: string;
  title: string;
  stars: number;
  kind: string;
  color: string | null;
};

export type AuctionData = {
  code: string;
  rarity: string;
  ends_at: string;
  top_bid: number;
  min_bid: number;
  step: number;
  leader: string | null;
  mine: boolean;
};

export type ShopData = {
  offers: Offer[];
  ticket_prices: Record<string, number>;
  frames: { code: string; title: string; price: number; color: string }[];
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

export type FriendItem = {
  name: string;
  level: number;
  joined: string;
};

export type ContestData = {
  items: { user_id: number; name: string; invites: number }[];
  me: { place: number; invites: number };
};

export type FriendsData = {
  invites: number;
  link: string;
  ladder: LadderStep[];
  friends: FriendItem[];
  contest: ContestData;
};

export type Tx = {
  id: number;
  currency: string;
  delta: number;
  reason: string;
  ref: string | null;
  created_at: string | null;
};
