export interface Airport {
  city: string;
  code: string;
  country: string;
}

const AIRPORTS: Airport[] = [
  // North America
  { city: "New York", code: "JFK", country: "US" },
  { city: "New York", code: "EWR", country: "US" },
  { city: "New York", code: "LGA", country: "US" },
  { city: "Los Angeles", code: "LAX", country: "US" },
  { city: "San Francisco", code: "SFO", country: "US" },
  { city: "Chicago", code: "ORD", country: "US" },
  { city: "Chicago", code: "MDW", country: "US" },
  { city: "Miami", code: "MIA", country: "US" },
  { city: "Dallas", code: "DFW", country: "US" },
  { city: "Houston", code: "IAH", country: "US" },
  { city: "Atlanta", code: "ATL", country: "US" },
  { city: "Denver", code: "DEN", country: "US" },
  { city: "Seattle", code: "SEA", country: "US" },
  { city: "Boston", code: "BOS", country: "US" },
  { city: "Washington", code: "IAD", country: "US" },
  { city: "Washington", code: "DCA", country: "US" },
  { city: "Las Vegas", code: "LAS", country: "US" },
  { city: "Orlando", code: "MCO", country: "US" },
  { city: "Phoenix", code: "PHX", country: "US" },
  { city: "Philadelphia", code: "PHL", country: "US" },
  { city: "Minneapolis", code: "MSP", country: "US" },
  { city: "Detroit", code: "DTW", country: "US" },
  { city: "San Diego", code: "SAN", country: "US" },
  { city: "Honolulu", code: "HNL", country: "US" },
  { city: "Portland", code: "PDX", country: "US" },
  { city: "Nashville", code: "BNA", country: "US" },
  { city: "Austin", code: "AUS", country: "US" },
  { city: "Toronto", code: "YYZ", country: "CA" },
  { city: "Vancouver", code: "YVR", country: "CA" },
  { city: "Montreal", code: "YUL", country: "CA" },
  { city: "Mexico City", code: "MEX", country: "MX" },
  { city: "Cancun", code: "CUN", country: "MX" },

  // Europe
  { city: "London", code: "LHR", country: "GB" },
  { city: "London", code: "LGW", country: "GB" },
  { city: "London", code: "STN", country: "GB" },
  { city: "Paris", code: "CDG", country: "FR" },
  { city: "Paris", code: "ORY", country: "FR" },
  { city: "Amsterdam", code: "AMS", country: "NL" },
  { city: "Frankfurt", code: "FRA", country: "DE" },
  { city: "Munich", code: "MUC", country: "DE" },
  { city: "Berlin", code: "BER", country: "DE" },
  { city: "Madrid", code: "MAD", country: "ES" },
  { city: "Barcelona", code: "BCN", country: "ES" },
  { city: "Rome", code: "FCO", country: "IT" },
  { city: "Milan", code: "MXP", country: "IT" },
  { city: "Lisbon", code: "LIS", country: "PT" },
  { city: "Zurich", code: "ZRH", country: "CH" },
  { city: "Vienna", code: "VIE", country: "AT" },
  { city: "Dublin", code: "DUB", country: "IE" },
  { city: "Copenhagen", code: "CPH", country: "DK" },
  { city: "Stockholm", code: "ARN", country: "SE" },
  { city: "Oslo", code: "OSL", country: "NO" },
  { city: "Helsinki", code: "HEL", country: "FI" },
  { city: "Athens", code: "ATH", country: "GR" },
  { city: "Istanbul", code: "IST", country: "TR" },
  { city: "Prague", code: "PRG", country: "CZ" },
  { city: "Warsaw", code: "WAW", country: "PL" },
  { city: "Budapest", code: "BUD", country: "HU" },

  // Asia
  { city: "Tokyo", code: "NRT", country: "JP" },
  { city: "Tokyo", code: "HND", country: "JP" },
  { city: "Osaka", code: "KIX", country: "JP" },
  { city: "Seoul", code: "ICN", country: "KR" },
  { city: "Beijing", code: "PEK", country: "CN" },
  { city: "Shanghai", code: "PVG", country: "CN" },
  { city: "Hong Kong", code: "HKG", country: "HK" },
  { city: "Singapore", code: "SIN", country: "SG" },
  { city: "Bangkok", code: "BKK", country: "TH" },
  { city: "Taipei", code: "TPE", country: "TW" },
  { city: "Kuala Lumpur", code: "KUL", country: "MY" },
  { city: "Manila", code: "MNL", country: "PH" },
  { city: "Bali", code: "DPS", country: "ID" },
  { city: "Jakarta", code: "CGK", country: "ID" },
  { city: "Delhi", code: "DEL", country: "IN" },
  { city: "Mumbai", code: "BOM", country: "IN" },
  { city: "Bangalore", code: "BLR", country: "IN" },
  { city: "Hanoi", code: "HAN", country: "VN" },
  { city: "Ho Chi Minh City", code: "SGN", country: "VN" },

  // Middle East
  { city: "Dubai", code: "DXB", country: "AE" },
  { city: "Abu Dhabi", code: "AUH", country: "AE" },
  { city: "Doha", code: "DOH", country: "QA" },
  { city: "Tel Aviv", code: "TLV", country: "IL" },

  // Oceania
  { city: "Sydney", code: "SYD", country: "AU" },
  { city: "Melbourne", code: "MEL", country: "AU" },
  { city: "Auckland", code: "AKL", country: "NZ" },

  // Africa
  { city: "Cairo", code: "CAI", country: "EG" },
  { city: "Cape Town", code: "CPT", country: "ZA" },
  { city: "Johannesburg", code: "JNB", country: "ZA" },
  { city: "Nairobi", code: "NBO", country: "KE" },
  { city: "Marrakech", code: "RAK", country: "MA" },

  // South America
  { city: "Sao Paulo", code: "GRU", country: "BR" },
  { city: "Rio de Janeiro", code: "GIG", country: "BR" },
  { city: "Buenos Aires", code: "EZE", country: "AR" },
  { city: "Lima", code: "LIM", country: "PE" },
  { city: "Bogota", code: "BOG", country: "CO" },
  { city: "Santiago", code: "SCL", country: "CL" },
];

/** Return a set of popular hub airports for initial display when field is empty */
export function popularAirports(limit = 6): Airport[] {
  const hubs = ["JFK", "LAX", "SFO", "LHR", "ORD", "ATL", "DXB", "SIN", "NRT", "CDG"];
  return AIRPORTS.filter((a) => hubs.includes(a.code)).slice(0, limit);
}

/** Find the best matching airport for a city name (for pre-fill resolution) */
export function resolveAirport(cityName: string): Airport | null {
  if (!cityName) return null;
  const q = cityName.toLowerCase().trim();
  const exact = AIRPORTS.find((a) => a.city.toLowerCase() === q);
  if (exact) return exact;
  const code = AIRPORTS.find((a) => a.code.toLowerCase() === q);
  if (code) return code;
  const starts = AIRPORTS.find((a) => a.city.toLowerCase().startsWith(q));
  if (starts) return starts;
  return null;
}

export function searchAirports(query: string, limit = 5): Airport[] {
  if (!query || query.length < 1) return [];
  const q = query.toLowerCase().trim();
  if (!q) return [];

  // Score each airport: code prefix match ranks higher than city match
  const scored: { airport: Airport; score: number }[] = [];

  for (const airport of AIRPORTS) {
    const codeLower = airport.code.toLowerCase();
    const cityLower = airport.city.toLowerCase();

    if (codeLower === q) {
      scored.push({ airport, score: 100 }); // exact code match
    } else if (codeLower.startsWith(q)) {
      scored.push({ airport, score: 80 }); // code prefix
    } else if (cityLower === q) {
      scored.push({ airport, score: 70 }); // exact city match
    } else if (cityLower.startsWith(q)) {
      scored.push({ airport, score: 60 }); // city starts with
    } else if (cityLower.includes(q)) {
      scored.push({ airport, score: 40 }); // city contains
    }
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit).map((s) => s.airport);
}
