import Papa from 'papaparse';
import { BusRoute, RouteMapData, LocationCoordinates } from '../types';

// Cache for storing geocoded coordinates to minimize API calls
const geocodeCache: Record<string, LocationCoordinates> = {};

/**
 * Geocode a location name to coordinates using Google Geocoding API
 * @param locationName The name of the location to geocode
 * @returns Promise with the coordinates
 */
export async function geocodeLocation(locationName: string): Promise<LocationCoordinates> {
  // Check cache first
  if (geocodeCache[locationName]) {
    return geocodeCache[locationName];
  }
  
  try {
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    
    if (!apiKey) {
      throw new Error("Google Maps API key is missing. Please set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY in your .env.local file.");
    }
    
    const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(locationName)}&key=${apiKey}`;
    
    const response = await fetch(url);
    const data = await response.json();
    
    if (data.status === 'OK' && data.results && data.results.length > 0) {
      const location = data.results[0].geometry.location;
      const coordinates = { lat: location.lat, lng: location.lng };
      
      // Cache the result
      geocodeCache[locationName] = coordinates;
      
      return coordinates;
    } else {
      throw new Error(`Geocoding error: "${data.status}". Make sure your API key is valid and has the Geocoding API enabled.`);
    }
  } catch (error) {
    console.error('Error geocoding location:', error);
    throw error;
  }
}

// Calculate distance between two coordinates using Haversine formula
export function calculateDistance(start: LocationCoordinates, end: LocationCoordinates): number {
  if (!start || !end) {
    console.error('Invalid coordinates for distance calculation', { start, end });
    return 0;
  }

  const R = 6371; // Earth's radius in km
  const dLat = (end.lat - start.lat) * Math.PI / 180;
  const dLon = (end.lng - start.lng) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(start.lat * Math.PI / 180) * Math.cos(end.lat * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  const distance = R * c;
  
  // Round to 2 decimal places
  return Math.round(distance * 100) / 100;
}

// Parse CSV file and return structured data
export async function parseBusData(filePath: string): Promise<BusRoute[]> {
  try {
    const response = await fetch(filePath);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch CSV: ${response.status} ${response.statusText}`);
    }
    
    const csvData = await response.text();
    
    if (!csvData || csvData.trim() === '') {
      console.error('CSV data is empty');
      return [];
    }
    
    const result = Papa.parse(csvData, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: true,
    });
    
    if (result.errors && result.errors.length > 0) {
      console.error('CSV parsing errors:', result.errors);
    }
    
    return result.data.map((row: any) => {
      // Convert CSV headers to camelCase for our TypeScript interface
      return {
        busId: row['Bus ID'] || 0,
        busName: row['Bus Name'] || 'Unknown',
        busType: row['Bus Type'] || 'Standard',
        departureTime: row['Departure Time'] || '--:--',
        arrivalTime: row['Arrival Time'] || '--:--',
        journeyDuration: row['Journey Duration'] || '0h 0m',
        lowestPrice: parseFloat(row['Lowest Price(INR)']) || 0,
        highestPrice: parseFloat(row['Highest Price(INR)']) || 0,
        startingPoint: row['Starting Point'] || 'Unknown',
        destination: row['Destination'] || 'Unknown',
        startingPointParent: row['Starting Point Parent'] || 'Unknown',
        destinationPointParent: row['Destination Point Parent'] || 'Unknown',
      } as BusRoute;
    });
  } catch (error) {
    console.error('Error fetching or parsing CSV:', error);
    return [];
  }
}

/**
 * Use Google Maps Routes API to get accurate route distance and duration
 * This will give us real road distance rather than just straight-line distance
 */
export async function getRouteDetails(
  origin: string,
  destination: string
): Promise<{ distance: number; duration: string }> {
  try {
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    
    if (!apiKey) {
      throw new Error("Google Maps API key is missing");
    }
    
    // Using the Routes API instead of Distance Matrix API
    const url = `https://routes.googleapis.com/directions/v2:computeRoutes?key=${apiKey}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': apiKey,
        'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline'
      },
      body: JSON.stringify({
        origin: {
          address: origin
        },
        destination: {
          address: destination
        },
        travelMode: "DRIVE",
        routingPreference: "TRAFFIC_AWARE",
        computeAlternativeRoutes: false,
        routeModifiers: {
          avoidTolls: false,
          avoidHighways: false,
          avoidFerries: false
        },
        languageCode: "en-US",
        units: "METRIC"
      })
    });
    
    const data = await response.json();
    
    if (data.routes && data.routes.length > 0) {
      // Distance comes in meters, convert to km
      const distanceInMeters = data.routes[0].distanceMeters;
      const distanceKm = parseFloat((distanceInMeters / 1000).toFixed(2));
      
      // Duration comes in seconds, convert to hours and minutes format
      const durationSeconds = parseInt(data.routes[0].duration.replace('s', ''));
      const hours = Math.floor(durationSeconds / 3600);
      const minutes = Math.floor((durationSeconds % 3600) / 60);
      const durationStr = `${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m`;
      
      return { 
        distance: distanceKm,
        duration: durationStr
      };
    } else {
      console.warn('Failed to get route details from Google Maps Routes API');
      // Fall back to Haversine formula
      const originCoords = await geocodeLocation(origin);
      const destCoords = await geocodeLocation(destination);
      const distance = calculateDistance(originCoords, destCoords);
      return { distance, duration: '00h 00m' };
    }
  } catch (error) {
    console.error('Error getting Google Maps route details:', error);
    // Fall back to Haversine calculation if API fails
    const originCoords = await geocodeLocation(origin);
    const destCoords = await geocodeLocation(destination);
    const distance = calculateDistance(originCoords, destCoords);
    return { distance, duration: '00h 00m' };
  }
}

// Process bus data to calculate distances and price per km
export async function processBusData(busData: BusRoute[]): Promise<{ 
  routes: RouteMapData[];
  uniqueRoutes: { id: string; startLocation: string; endLocation: string }[] 
}> {
  // Group buses by origin-destination parent pair
  const routeGroups: Record<string, BusRoute[]> = {};
  
  busData.forEach(bus => {
    const routeKey = `${bus.startingPointParent}-${bus.destinationPointParent}`;
    if (!routeGroups[routeKey]) {
      routeGroups[routeKey] = [];
    }
    routeGroups[routeKey].push(bus);
  });
  
  // Create RouteMapData for each unique route
  const routes: RouteMapData[] = [];
  const uniqueRoutes: { id: string; startLocation: string; endLocation: string }[] = [];
  
  // Process routes sequentially to avoid overwhelming the APIs
  for (const [routeKey, buses] of Object.entries(routeGroups)) {
    const [startCity, endCity] = routeKey.split('-');
    
    // Get coordinates for cities using geocoding
    const startCoords = await geocodeLocation(startCity);
    const endCoords = await geocodeLocation(endCity);
    
    // Calculate distance using Google Maps Routes API for accurate road distance
    let distance;
    let routeDuration = '';
    try {
      const routeDetails = await getRouteDetails(startCity, endCity);
      distance = routeDetails.distance;
      routeDuration = routeDetails.duration;
      console.log(`Google Maps Routes API: ${startCity} to ${endCity}: ${distance} km, duration: ${routeDuration}`);
    } catch (error) {
      // Fall back to Haversine formula if API fails
      distance = calculateDistance(startCoords, endCoords);
      console.log(`Fallback distance for ${startCity} to ${endCity}: ${distance} km`);
    }
    
    // Calculate price per km for each bus
    const busesWithPricePerKm = buses.map(bus => {
      return {
        ...bus,
        distance,
        routeDuration,
        pricePerKmLow: parseFloat((bus.lowestPrice / distance).toFixed(2)),
        pricePerKmHigh: parseFloat((bus.highestPrice / distance).toFixed(2))
      };
    });
    
    // Sort buses by price per km (using highest price)
    busesWithPricePerKm.sort((a, b) => (a.pricePerKmHigh || 0) - (b.pricePerKmHigh || 0));
    
    const route = {
      id: routeKey,
      startLocation: startCity,
      endLocation: endCity,
      startCoords,
      endCoords,
      distance,
      routeDuration,
      buses: busesWithPricePerKm
    };
    
    routes.push(route);
    
    uniqueRoutes.push({
      id: routeKey,
      startLocation: startCity,
      endLocation: endCity
    });
  };
  
  return {
    routes,
    uniqueRoutes
  };
} 