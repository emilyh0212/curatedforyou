import { MapPin } from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';
import { useState } from 'react';
import { RefreshCw, Check, Star, ArrowLeft, Loader2, AlertTriangle } from 'lucide-react';
import type { UIRestaurant } from '../lib/api';

interface RestaurantResultsProps {
  city: string;
  category: string;
  tried: UIRestaurant[];
  wantToTry: UIRestaurant[];
  loading: boolean;
  error: string | null;
  chatText?: string;
  onAskMore: (followUp: string) => void;
  onRefresh: () => void;
  onGoBack: () => void;
}

export function RestaurantResults({
  city,
  category,
  tried,
  wantToTry,
  loading,
  error,
  chatText,
  onAskMore,
  onRefresh,
  onGoBack,
}: RestaurantResultsProps) {
  const [selectedMode, setSelectedMode] = useState<'tried' | 'wantToTry'>('tried');
  const [followUp, setFollowUp] = useState('');

  // If the tried list is empty but want-to-try has results, default the toggle there
  // so the user sees something on first paint.
  const effectiveMode: 'tried' | 'wantToTry' =
    selectedMode === 'tried' && tried.length === 0 && wantToTry.length > 0
      ? 'wantToTry'
      : selectedMode;

  const currentRestaurants = effectiveMode === 'tried' ? tried : wantToTry;

  const renderStars = (rating: number) => {
    if (!rating) return '';
    return '⭐'.repeat(Math.floor(rating));
  };

  const handleSubmitFollowUp = () => {
    const trimmed = followUp.trim();
    if (!trimmed) return;
    onAskMore(trimmed);
    setFollowUp('');
  };

  return (
    <div className="w-full max-w-3xl px-6 py-12">
      {/* Go Back Button */}
      <button
        onClick={onGoBack}
        className="mb-6 flex items-center gap-2 text-[#FF6B35] hover:text-[#F5C543] transition-colors"
      >
        <ArrowLeft size={18} />
        <span>Go back</span>
      </button>

      {/* Category Tag */}
      {category && (
        <div className="flex justify-center mb-6">
          <div className="backdrop-blur-sm bg-[#F5C543] text-black px-6 py-2 rounded-full inline-block shadow-md shadow-[rgba(245,197,67,0.15)]">
            {category}
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mb-6 flex items-start gap-3 backdrop-blur-xl bg-[rgba(255,82,82,0.12)] border border-[rgba(255,82,82,0.4)] text-[#FFB4B4] rounded-2xl p-4">
          <AlertTriangle size={18} className="mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <div className="text-white mb-1">Couldn't load picks</div>
            <div className="opacity-90">{error}</div>
          </div>
        </div>
      )}

      {/* Section Header with Refresh */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-white">
          Picks I think you'll like
        </h2>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-2 text-[#FF6B35] hover:text-[#F5C543] transition-colors disabled:opacity-50"
        >
          {loading ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
          <span>{loading ? 'Thinking…' : 'Show me different picks'}</span>
        </button>
      </div>

      {/* Mode Toggle */}
      <div className="mb-4">
        <div className="flex gap-3 mb-3">
          <button
            onClick={() => setSelectedMode('tried')}
            className={`px-5 py-2 rounded-full transition-all ${
              effectiveMode === 'tried'
                ? 'bg-[#F5C543] text-black shadow-md shadow-[rgba(245,197,67,0.2)]'
                : 'backdrop-blur-sm bg-[rgba(40,40,40,0.6)] text-gray-300 border border-[rgba(255,255,255,0.1)] hover:border-[#F5C543]'
            }`}
          >
            <Check size={16} className="inline-block mr-1.5" />
            Tried &amp; recommended {tried.length > 0 && <span className="opacity-70">({tried.length})</span>}
          </button>
          <button
            onClick={() => setSelectedMode('wantToTry')}
            className={`px-5 py-2 rounded-full transition-all ${
              effectiveMode === 'wantToTry'
                ? 'bg-[#F5C543] text-black shadow-md shadow-[rgba(245,197,67,0.2)]'
                : 'backdrop-blur-sm bg-[rgba(40,40,40,0.6)] text-gray-300 border border-[rgba(255,255,255,0.1)] hover:border-[#F5C543]'
            }`}
          >
            <Star size={16} className="inline-block mr-1.5" />
            Want to try {wantToTry.length > 0 && <span className="opacity-70">({wantToTry.length})</span>}
          </button>
        </div>

        <p className="text-gray-400 text-sm">
          {effectiveMode === 'tried'
            ? "Places I've been to and genuinely recommend."
            : "Places I've saved and feel excited about, but haven't tried yet."}
        </p>
      </div>

      {/* Loading state when we have no data yet */}
      {loading && currentRestaurants.length === 0 && (
        <div className="backdrop-blur-xl bg-[rgba(40,40,40,0.4)] border border-[rgba(255,255,255,0.1)] rounded-3xl p-12 flex flex-col items-center justify-center text-gray-400 gap-3 mb-6">
          <Loader2 size={28} className="animate-spin text-[#F5C543]" />
          <span>Pulling picks from Emily's list…</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && currentRestaurants.length === 0 && (
        <div className="backdrop-blur-xl bg-[rgba(40,40,40,0.4)] border border-[rgba(255,255,255,0.1)] rounded-3xl p-8 text-center text-gray-400 mb-6">
          <p className="mb-2 text-white">No picks in this list for that query.</p>
          <p className="text-sm">Try a different vibe, neighborhood, or budget — or switch tabs.</p>
        </div>
      )}

      {/* Restaurant Cards */}
      <div className="space-y-4 mb-6">
        {currentRestaurants.map((restaurant) => (
          <div
            key={restaurant.id}
            className={`backdrop-blur-xl rounded-3xl p-6 flex gap-4 border transition-all hover:shadow-md ${
              restaurant.mode === 'tried'
                ? 'bg-[rgba(40,40,40,0.7)] border-[rgba(255,255,255,0.15)] hover:border-[#F5C543] hover:shadow-[rgba(245,197,67,0.15)]'
                : 'bg-[rgba(40,40,40,0.5)] border-[rgba(255,255,255,0.1)] hover:border-[#F5C543] hover:shadow-[rgba(245,197,67,0.1)]'
            }`}
          >
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-white">
                  {restaurant.name}
                </h3>
                {restaurant.mode === 'tried' ? (
                  <span className="inline-flex items-center gap-1 bg-[rgba(76,175,80,0.2)] text-[#81C784] px-2 py-0.5 rounded-full border border-[rgba(76,175,80,0.3)]" style={{ fontSize: '11px' }}>
                    <Check size={10} />
                    Tried
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 bg-[rgba(255,167,38,0.2)] text-[#FFB74D] px-2 py-0.5 rounded-full border border-[rgba(255,167,38,0.3)]" style={{ fontSize: '11px' }}>
                    <Star size={10} />
                    Want to try
                  </span>
                )}
              </div>
              <p className="text-gray-400 mb-3">
                {[restaurant.type, restaurant.location, restaurant.price,
                  restaurant.rating ? `${restaurant.rating} ${renderStars(restaurant.rating)}` : null,
                  restaurant.reviewCount ? `${restaurant.reviewCount} reviews` : null,
                ].filter(Boolean).join(' · ')}
              </p>
              {restaurant.description && (
                <p className="text-gray-300 mb-4 opacity-90">
                  {restaurant.description}
                </p>
              )}

              {restaurant.whyThisPick && (
                <div className="bg-transparent border-l-2 border-[rgba(255,107,53,0.5)] pl-3 mb-3">
                  <p className="text-gray-400 text-sm italic">
                    "{restaurant.whyThisPick}"
                  </p>
                </div>
              )}

              {restaurant.url ? (
                <a
                  href={restaurant.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#FF6B35] hover:text-[#C44569] inline-flex items-center gap-1 transition-colors"
                >
                  <MapPin size={14} />
                  View on Google Maps
                </a>
              ) : null}
            </div>
            <div className="w-32 h-32 flex-shrink-0">
              <ImageWithFallback
                src={restaurant.imageUrl}
                alt={restaurant.name}
                className="w-full h-full object-cover rounded-2xl"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Optional chat reply preview */}
      {chatText && (
        <details className="mb-6 backdrop-blur-xl bg-[rgba(30,30,30,0.5)] border border-[rgba(255,255,255,0.08)] rounded-2xl px-4 py-3 text-gray-300 text-sm">
          <summary className="cursor-pointer text-gray-400 hover:text-white">
            Show full reasoning from chatbot
          </summary>
          <pre className="whitespace-pre-wrap mt-3 text-xs leading-relaxed text-gray-300 font-sans">
            {chatText}
          </pre>
        </details>
      )}

      {/* Ask More Section */}
      <div className="backdrop-blur-xl bg-[rgba(40,40,40,0.6)] border-2 border-[#F5C543] rounded-3xl p-6 shadow-md shadow-[rgba(245,197,67,0.1)]">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={followUp}
            onChange={(e) => setFollowUp(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !loading) handleSubmitFollowUp(); }}
            placeholder={`Ask for more recommendations in ${city}`}
            className="flex-1 bg-transparent focus:outline-none text-white placeholder:text-gray-500"
            disabled={loading}
          />
          <button
            onClick={handleSubmitFollowUp}
            disabled={loading || !followUp.trim()}
            className="w-10 h-10 flex items-center justify-center bg-[#F5C543] hover:shadow-md hover:shadow-[rgba(245,197,67,0.3)] rounded-full text-black transition-all disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <span className="text-xl">↑</span>}
          </button>
        </div>
      </div>
    </div>
  );
}
