// API client for the FastAPI backend (server.py).
//
// Uses VITE_API_URL when set (recommended for dev/prod). Falls back to
// http://localhost:8000 to match the default backend port.
const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

// ---------- Types matching server.py response models ----------

export interface BackendRestaurant {
  name: string;
  note: string;
  url: string;
  status: 'tried' | 'want' | 'want_to_try' | string;
  city: string;
  neighborhood?: string | null;
  why_picked?: string | null;
  restaurant_id?: string | null;
  final_score?: number | null;
  why?: string | null;
  price_tier?: string | null;
  public_rating?: string | null;
  public_review_count?: string | null;
  public_vibe?: string | null;
  public_vibe_source?: string | null;
  public_vibe_model?: string | null;
  distance_km?: number | null;
  match_score?: number | null;
  taste_score?: number | null;
  public_score?: number | null;
  confidence?: string | null;
  matched_tags?: string[] | null;
}

export interface BackendRestaurantBundle {
  tried: BackendRestaurant[];
  want: BackendRestaurant[];
  category?: string | null;
}

export interface ChatResponse {
  response: string;
  restaurants: BackendRestaurantBundle | null;
}

// ---------- Frontend-friendly view model ----------

export interface UIRestaurant {
  id: string;
  name: string;
  type: string;
  location: string;
  price: string;
  rating: number;
  description: string;
  imageUrl: string;
  mode: 'tried' | 'wantToTry';
  whyThisPick: string;
  url: string;
  publicVibe?: string;
  reviewCount?: string;
  distanceKm?: number | null;
}

// ---------- Helpers ----------

function priceTierToSymbol(tier?: string | null): string {
  if (!tier) return '$$';
  const n = parseInt(tier, 10);
  if (Number.isNaN(n)) return '$$';
  if (n <= 1) return '$';
  if (n === 2) return '$$';
  if (n === 3) return '$$$';
  return '$$$$';
}

function deriveType(r: BackendRestaurant): string {
  // The backend doesn't carry a structured cuisine field for every restaurant.
  // Try matched_tags first, then sniff Emily's note for common cuisines, then
  // fall back to a neutral label.
  const tagPriority = ['italian', 'japanese', 'thai', 'french', 'mexican', 'korean',
                       'pizza', 'sushi', 'ramen', 'brunch', 'cocktails'];
  if (r.matched_tags && r.matched_tags.length) {
    for (const want of tagPriority) {
      if (r.matched_tags.some(t => t.toLowerCase().includes(want))) {
        return want.charAt(0).toUpperCase() + want.slice(1);
      }
    }
  }
  const note = (r.note || '').toLowerCase();
  for (const want of tagPriority) {
    if (note.includes(want)) {
      return want.charAt(0).toUpperCase() + want.slice(1);
    }
  }
  return 'Restaurant';
}

function deriveLocation(r: BackendRestaurant): string {
  if (r.neighborhood && r.neighborhood.trim()) {
    return `${r.neighborhood}, ${r.city}`;
  }
  return r.city || '';
}

function deriveDescription(r: BackendRestaurant): string {
  const note = (r.note || '').trim();
  if (note) return note;
  if (r.public_vibe && r.public_vibe.trim()) return r.public_vibe.trim();
  return '';
}

function deriveWhy(r: BackendRestaurant): string {
  return (r.why_picked || r.why || '').trim();
}

function deriveRating(r: BackendRestaurant): number {
  if (!r.public_rating) return 0;
  const n = parseFloat(r.public_rating);
  return Number.isNaN(n) ? 0 : n;
}

export function toUIRestaurant(r: BackendRestaurant, mode: 'tried' | 'wantToTry'): UIRestaurant {
  return {
    id: r.restaurant_id || `${r.city}_${r.name}`.toLowerCase().replace(/\s+/g, '_'),
    name: r.name,
    type: deriveType(r),
    location: deriveLocation(r),
    price: priceTierToSymbol(r.price_tier),
    rating: deriveRating(r),
    description: deriveDescription(r),
    imageUrl: '', // backend doesn't supply images; ImageWithFallback shows a placeholder
    mode,
    whyThisPick: deriveWhy(r),
    url: r.url || '',
    publicVibe: r.public_vibe || undefined,
    reviewCount: r.public_review_count || undefined,
    distanceKm: r.distance_km ?? null,
  };
}

export function bundleToUI(bundle: BackendRestaurantBundle | null): {
  tried: UIRestaurant[];
  wantToTry: UIRestaurant[];
} {
  if (!bundle) return { tried: [], wantToTry: [] };
  return {
    tried: bundle.tried.map(r => toUIRestaurant(r, 'tried')),
    wantToTry: bundle.want.map(r => toUIRestaurant(r, 'wantToTry')),
  };
}

// ---------- API calls ----------

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function chat(message: string, city?: string | null): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, city: city ?? null }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ApiError(text || `HTTP ${res.status}`, res.status);
  }
  return res.json();
}

export interface SwapArgs {
  excludeName: string;
  excludeAll: string[];
  city: string;
  isTried: boolean;
}

export async function swap(args: SwapArgs): Promise<BackendRestaurantBundle> {
  const res = await fetch(`${API_BASE}/swap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      exclude_restaurant: args.excludeName,
      exclude_all: args.excludeAll,
      city: args.city,
      is_tried: args.isTried,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new ApiError(text || `HTTP ${res.status}`, res.status);
  }
  return res.json();
}

export async function health(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new ApiError(`HTTP ${res.status}`, res.status);
  return res.json();
}
