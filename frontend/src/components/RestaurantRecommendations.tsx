import { MapPin, Star } from 'lucide-react';

interface Restaurant {
  name: string;
  emoji?: string;
  category: string;
  neighborhood: string;
  price: string;
  rating: number;
  vibe: string;
  mapsUrl: string;
  imageUrl: string;
}

interface RestaurantRecommendationsProps {
  tried: Restaurant[];
  wantToTry: Restaurant[];
}

export function RestaurantRecommendations({ tried, wantToTry }: RestaurantRecommendationsProps) {
  const renderStars = (rating: number) => {
    const fullStars = Math.floor(rating);
    const stars = [];
    for (let i = 0; i < 5; i++) {
      stars.push(
        <Star
          key={i}
          size={14}
          className={i < fullStars ? 'fill-[#f4b942] text-[#f4b942]' : 'fill-[#d4c5b5] text-[#d4c5b5]'}
        />
      );
    }
    return stars;
  };

  return (
    <div className="ml-0 mt-3">
      {/* Tried and loved section */}
      <div className="bg-[#f9f7f4] border-2 border-[#e4dad0] rounded-2xl p-5 mb-3">
        <h3 className="text-[#8b5a3c] mb-4">
          Tried and loved
        </h3>
        <div className="space-y-4">
          {tried.map((restaurant, index) => (
            <div 
              key={index} 
              className="pb-4 border-b border-[#e4dad0] last:border-0 last:pb-0"
            >
              <div className="flex gap-4">
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h4 className="text-[#5a3d2b]">
                      {restaurant.emoji && <span className="mr-1.5">{restaurant.emoji}</span>}
                      <strong>{restaurant.name}</strong>
                    </h4>
                    <a
                      href={restaurant.mapsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#a89080] hover:text-[#c89968] transition-colors shrink-0"
                      title="View on Google Maps"
                    >
                      <MapPin size={16} />
                    </a>
                  </div>
                  
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[#8b5a3c]">{restaurant.category}</span>
                    <span className="text-[#a89080]">·</span>
                    <span className="text-[#8b5a3c]">{restaurant.neighborhood}</span>
                    <span className="text-[#a89080]">·</span>
                    <span className="text-[#8b5a3c]">{restaurant.price}</span>
                    <span className="text-[#a89080]">·</span>
                    <span className="text-[#8b5a3c]">{restaurant.rating}</span>
                    <div className="flex gap-0.5">
                      {renderStars(restaurant.rating)}
                    </div>
                  </div>
                  
                  <p className="text-[#6b5444] mb-3">{restaurant.vibe}</p>
                  
                  <a
                    href={restaurant.mapsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-[#a89080] hover:text-[#c89968] transition-colors"
                  >
                    <MapPin size={14} />
                    <span>View on Google Maps</span>
                  </a>
                </div>
                
                <div className="w-28 h-28 rounded-xl overflow-hidden shrink-0 bg-[#e4dad0]">
                  <img 
                    src={restaurant.imageUrl} 
                    alt={restaurant.name}
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Want to try section */}
      <div className="bg-[#faf8f5] border-2 border-[#f4e6d5] rounded-2xl p-5">
        <h3 className="text-[#a88b6f] mb-3">
          On my want-to-try list
        </h3>
        <div>
          {wantToTry.map((restaurant, index) => (
            <div key={index} className="flex gap-4">
              <div className="flex-1">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h4 className="text-[#6b5444]">
                    {restaurant.emoji && <span className="mr-1.5">{restaurant.emoji}</span>}
                    <strong>{restaurant.name}</strong>
                  </h4>
                  <a
                    href={restaurant.mapsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#a89080] hover:text-[#c89968] transition-colors shrink-0"
                    title="View on Google Maps"
                  >
                    <MapPin size={16} />
                  </a>
                </div>
                
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[#a88b6f]">{restaurant.category}</span>
                  <span className="text-[#c5b5a3]">·</span>
                  <span className="text-[#a88b6f]">{restaurant.neighborhood}</span>
                  <span className="text-[#c5b5a3]">·</span>
                  <span className="text-[#a88b6f]">{restaurant.price}</span>
                  <span className="text-[#c5b5a3]">·</span>
                  <span className="text-[#a88b6f]">{restaurant.rating}</span>
                  <div className="flex gap-0.5">
                    {renderStars(restaurant.rating)}
                  </div>
                </div>
                
                <p className="text-[#8b7766] mb-3">{restaurant.vibe}</p>
                
                <a
                  href={restaurant.mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[#a89080] hover:text-[#c89968] transition-colors"
                >
                  <MapPin size={14} />
                  <span>View on Google Maps</span>
                </a>
              </div>
              
              <div className="w-28 h-28 rounded-xl overflow-hidden shrink-0 bg-[#e4dad0]">
                <img 
                  src={restaurant.imageUrl} 
                  alt={restaurant.name}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
