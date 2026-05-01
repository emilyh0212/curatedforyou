import { useState } from 'react';
import { ArrowUp, Menu, X, Loader2 } from 'lucide-react';
import { RestaurantResults } from './components/RestaurantResults';
import { chat, bundleToUI, ApiError, type UIRestaurant } from './lib/api';

type City = 'nyc' | 'milan';

export default function App() {
  const [selectedCity, setSelectedCity] = useState<City>('nyc');
  const [inputValue, setInputValue] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Backend-driven state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tried, setTried] = useState<UIRestaurant[]>([]);
  const [wantToTry, setWantToTry] = useState<UIRestaurant[]>([]);
  const [category, setCategory] = useState<string>('');
  const [lastQuery, setLastQuery] = useState<string>('');
  const [chatText, setChatText] = useState<string>('');

  const examplePrompts = [
    "Cheap eats near Williamsburg",
    "Romantic date spot that's not too fancy",
    "Solo dinner somewhere cozy",
    "Late night noodles in Manhattan",
    "A place I'd take visiting friends",
    "Best pasta under $30"
  ];

  const favorites = [
    {
      label: "Brunch restaurants",
      description: "Easy, reliable spots for slow mornings",
      query: "brunch restaurants",
    },
    {
      label: "Romantic dinner",
      description: "Places that feel intimate and intentional",
      query: "romantic dinner",
    },
    {
      label: "My favorite Thai restaurants",
      description: "Comfort food I always crave",
      query: "Thai food",
    },
  ];

  const savedSpots = [
    "That Japanese place in East Village",
    "The wine bar you recommended last week",
    "Cozy Italian spot from our Milan chat"
  ];

  const handleCityChange = (city: City) => {
    setSelectedCity(city);
    const cityName = city === 'nyc' ? 'New York City' : 'Milan';
    setInputValue(`Recommend me restaurants in ${cityName}`);
  };

  const cityName = selectedCity === 'nyc' ? 'New York City' : 'Milan';
  const cityForApi = selectedCity === 'nyc' ? 'New York' : 'Milan';

  async function runQuery(query: string) {
    const trimmed = query.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setLastQuery(trimmed);
    try {
      const resp = await chat(trimmed, cityForApi);
      const ui = bundleToUI(resp.restaurants);
      setTried(ui.tried);
      setWantToTry(ui.wantToTry);
      setCategory(resp.restaurants?.category ?? '');
      setChatText(resp.response ?? '');
      setShowResults(true);
    } catch (err) {
      const msg = err instanceof ApiError
        ? `Backend error (${err.status}). Is the FastAPI server running on port 8000?`
        : err instanceof Error
          ? err.message
          : 'Could not reach the backend. Is server.py running?';
      setError(msg);
      setShowResults(true);
    } finally {
      setLoading(false);
    }
  }

  const handleSearch = () => {
    void runQuery(inputValue);
  };

  const handleGoBack = () => {
    setShowResults(false);
    setError(null);
  };

  const handleAskMore = (followUp: string) => {
    void runQuery(followUp);
  };

  const handleRefresh = () => {
    if (lastQuery) void runQuery(lastQuery);
  };

  if (showResults) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0f0f0f]">
        <RestaurantResults
          city={cityName}
          category={category || lastQuery}
          tried={tried}
          wantToTry={wantToTry}
          loading={loading}
          error={error}
          chatText={chatText}
          onAskMore={handleAskMore}
          onRefresh={handleRefresh}
          onGoBack={handleGoBack}
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#0f0f0f]">
      {/* Sidebar */}
      <div className={`fixed top-0 left-0 h-screen backdrop-blur-xl bg-[rgba(25,25,25,0.8)] border-r border-[rgba(255,255,255,0.08)] flex-shrink-0 transition-all duration-300 ease-in-out overflow-y-auto ${
        sidebarOpen ? 'w-64 p-6' : 'w-0 p-0 border-r-0 overflow-hidden'
      }`}>
        {sidebarOpen && (
          <button
            className="absolute top-6 right-6 w-8 h-8 flex items-center justify-center bg-transparent hover:bg-[#e8d0c8] rounded-full text-[#5c3a2e] transition-colors"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        )}

        <div className={`transition-opacity duration-300 ${sidebarOpen ? 'opacity-100' : 'opacity-0'}`}>
          <div className="mb-6">
            <h2 className="text-white mb-1">Saved</h2>
            <p className="text-gray-400 text-xs">
              From past conversations
            </p>
          </div>

          <div className="space-y-1">
            {savedSpots.map((spot, index) => (
              <div
                key={index}
                className="backdrop-blur-sm bg-[rgba(255,107,53,0.1)] rounded-lg px-3 py-3 text-white cursor-pointer hover:bg-[rgba(255,107,53,0.2)] transition-all text-sm border border-[rgba(255,255,255,0.1)] hover:border-[rgba(255,107,53,0.5)]"
              >
                {spot}
              </div>
            ))}
          </div>
        </div>
      </div>

      {!sidebarOpen && (
        <button
          className="fixed top-6 left-8 z-50 w-10 h-10 flex items-center justify-center bg-[#F5C543] hover:shadow-md hover:shadow-[rgba(245,197,67,0.3)] rounded-full text-black transition-all"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu size={20} />
        </button>
      )}

      {/* Main Content */}
      <div className={`flex-1 flex items-center justify-center transition-all duration-300 ease-in-out ${
        sidebarOpen ? 'ml-64' : 'ml-0'
      }`}>
        <div className="w-full max-w-3xl px-6 py-16 mt-12">
          <h1 className="text-center text-[#F5C543] mb-4 text-3xl">
            Emily's Restaurant Recommendations
          </h1>

          <p className="text-center text-gray-400 mb-12">
            Thoughtful restaurant picks, curated for your mood and your city
          </p>

          {/* Main Input Box */}
          <div className="backdrop-blur-xl bg-[rgba(30,30,30,0.6)] border border-[rgba(255,255,255,0.1)] rounded-3xl p-8 mb-6 shadow-md shadow-[rgba(255,107,53,0.08)]">
            <div className="flex items-center gap-3 mb-4">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !loading) handleSearch(); }}
                placeholder="Tell me what you're craving..."
                className="flex-1 bg-transparent focus:outline-none text-white text-lg placeholder:text-gray-500"
                disabled={loading}
              />
              <button
                className="w-12 h-12 flex items-center justify-center bg-[#F5C543] hover:shadow-md hover:shadow-[rgba(245,197,67,0.3)] rounded-full text-black transition-all disabled:opacity-50"
                onClick={handleSearch}
                disabled={loading || !inputValue.trim()}
              >
                {loading ? <Loader2 size={22} className="animate-spin" /> : <ArrowUp size={22} />}
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleCityChange('nyc')}
                className={`px-4 py-1.5 rounded-full transition-all ${
                  selectedCity === 'nyc'
                    ? 'bg-[#F5C543] text-black shadow-md shadow-[rgba(245,197,67,0.2)]'
                    : 'backdrop-blur-sm bg-[rgba(255,107,53,0.1)] text-gray-300 border border-[rgba(255,255,255,0.1)] hover:border-[#F5C543]'
                }`}
              >
                New York City
              </button>
              <button
                onClick={() => handleCityChange('milan')}
                className={`px-4 py-1.5 rounded-full transition-all ${
                  selectedCity === 'milan'
                    ? 'bg-[#F5C543] text-black shadow-md shadow-[rgba(245,197,67,0.2)]'
                    : 'backdrop-blur-sm bg-[rgba(255,107,53,0.1)] text-gray-300 border border-[rgba(255,255,255,0.1)] hover:border-[#F5C543]'
                }`}
              >
                Milan
              </button>
            </div>
          </div>

          {/* Example Prompts */}
          <div className="mb-10">
            <p className="text-gray-500 mb-4">
              Try asking...
            </p>
            <div className="flex flex-wrap gap-2">
              {examplePrompts.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => setInputValue(prompt)}
                  className="px-4 py-2 backdrop-blur-sm bg-[rgba(30,30,30,0.6)] border border-[rgba(255,255,255,0.1)] rounded-full text-gray-300 hover:border-[#FF6B35] hover:text-[#FF6B35] transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Favorites Section */}
          <div className="mb-10">
            <p className="text-gray-400 mb-5">
              Curated lists I come back to
            </p>
            <div className="space-y-4">
              {favorites.map((favorite, index) => (
                <div
                  key={index}
                  onClick={() => { setInputValue(favorite.query); void runQuery(favorite.query); }}
                  className="backdrop-blur-xl bg-[rgba(30,30,30,0.6)] border border-[rgba(255,255,255,0.1)] rounded-2xl p-5 cursor-pointer hover:border-[#FF6B35] hover:shadow-md hover:shadow-[rgba(255,107,53,0.15)] transition-all"
                >
                  <div className="text-white mb-1">
                    {favorite.label}
                  </div>
                  <div className="text-gray-400 text-sm">
                    {favorite.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
