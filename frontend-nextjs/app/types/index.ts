export interface BusRoute {
  busId: number;
  busName: string;
  busType: string;
  departureTime: string;
  arrivalTime: string;
  journeyDuration: string;
  lowestPrice: number;
  highestPrice: number;
  startingPoint: string;
  destination: string;
  startingPointParent: string;
  destinationPointParent: string;
  distance?: number;
  pricePerKmLow?: number;
  pricePerKmHigh?: number;
  routeDuration?: string;
}

export interface LocationCoordinates {
  lat: number;
  lng: number;
}

export interface RouteMapData {
  id: string;
  startLocation: string;
  endLocation: string;
  startCoords: LocationCoordinates;
  endCoords: LocationCoordinates;
  distance: number;
  routeDuration: string;
  buses: BusRoute[];
}

export interface BusDataState {
  rawBusData: BusRoute[];
  routes: RouteMapData[];
  uniqueRoutes: string[];
  selectedRoute: string | null;
  priceCalculationMode: 'highest' | 'lowest';
} 