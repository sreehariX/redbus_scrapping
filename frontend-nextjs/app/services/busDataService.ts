import Papa from 'papaparse';
import { BusRoute, RouteMapData, LocationCoordinates } from '../types';

// Hard-coded mapping of city names to coordinates for demo purposes
const cityCoordinates: Record<string, LocationCoordinates> = {
  'Delhi': { lat: 28.7041, lng: 77.1025 },
  'Manali': { lat: 32.2432, lng: 77.1892 },
  'Shimla': { lat: 31.1048, lng: 77.1734 },
  'Rishikesh': { lat: 30.0869, lng: 78.2676 },
  'Nainital': { lat: 29.3919, lng: 79.4542 },
  'Katra': { lat: 32.9916, lng: 74.9507 },
  'Bangalore': { lat: 12.9716, lng: 77.5946 },
  'Goa': { lat: 15.2993, lng: 74.1240 },
  'Hyderabad': { lat: 17.3850, lng: 78.4867 },
  'Tirupathi': { lat: 13.6288, lng: 79.4192 },
  'Chennai': { lat: 13.0827, lng: 80.2707 },
  'Pondicherry': { lat: 11.9416, lng: 79.8083 },
  'Mumbai': { lat: 19.0760, lng: 72.8777 },
  'Pune': { lat: 18.5204, lng: 73.8567 },
  'Nagpur': { lat: 21.1458, lng: 79.0882 },
  'Kolhapur': { lat: 16.7050, lng: 74.2433 },
  'Nashik': { lat: 19.9975, lng: 73.7898 },
  'Shirdi': { lat: 19.7005, lng: 74.4767 },
  'Mahabaleshwar': { lat: 17.9307, lng: 73.6477 }
};

// Calculate distance between two coordinates using Haversine formula
export function calculateDistance(start: LocationCoordinates, end: LocationCoordinates): number {
  const R = 6371; // Earth's radius in km
  const dLat = (end.lat - start.lat) * Math.PI / 180;
  const dLon = (end.lng - start.lng) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(start.lat * Math.PI / 180) * Math.cos(end.lat * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
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

// Process bus data to calculate distances and price per km
export function processBusData(busData: BusRoute[]): { 
  routes: RouteMapData[],
  uniqueRoutes: { id: string; startLocation: string; endLocation: string }[] 
} {
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
  
  Object.entries(routeGroups).forEach(([routeKey, buses]) => {
    const [startCity, endCity] = routeKey.split('-');
    
    // Get coordinates for cities
    const startCoords = cityCoordinates[startCity] || { lat: 0, lng: 0 };
    const endCoords = cityCoordinates[endCity] || { lat: 0, lng: 0 };
    
    // If either coordinate is missing, we can use fallback coordinates to avoid errors
    if (startCoords && endCoords) {
      // Calculate distance
      const distance = calculateDistance(startCoords, endCoords);
      
      // Calculate price per km for each bus
      const busesWithPricePerKm = buses.map(bus => {
        return {
          ...bus,
          distance,
          pricePerKmLow: bus.lowestPrice / distance,
          pricePerKmHigh: bus.highestPrice / distance
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
        buses: busesWithPricePerKm
      };
      
      routes.push(route);
      
      uniqueRoutes.push({
        id: routeKey,
        startLocation: startCity,
        endLocation: endCity
      });
    }
  });
  
  return {
    routes,
    uniqueRoutes
  };
} 