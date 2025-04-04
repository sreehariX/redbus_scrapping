'use client';

import { useState, useEffect } from 'react';
import { parseBusData, processBusData } from './services/busDataService';
import { BusRoute, RouteMapData } from './types';
import SearchForm from './components/SearchForm';
import RouteMap from './components/RouteMap';
import BusDataTable from './components/BusDataTable';
import styles from './page.module.css';

export default function Home() {
  const [rawBusData, setRawBusData] = useState<BusRoute[]>([]);
  const [routeMapData, setRouteMapData] = useState<RouteMapData[]>([]);
  const [uniqueRoutes, setUniqueRoutes] = useState<string[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [priceCalculationMode, setPriceCalculationMode] = useState<'highest' | 'lowest'>('lowest');
  const [geocodingInProgress, setGeocodingInProgress] = useState<boolean>(false);
  const [geocodingProgress, setGeocodingProgress] = useState<string>('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Fetch and parse CSV data
        const busData = await parseBusData('/data/bus_data.csv');
        
        if (!busData || busData.length === 0) {
          setError('No bus data available');
          setIsLoading(false);
          return;
        }
        
        setRawBusData(busData);
        
        // Process bus data with geocoding
        setGeocodingInProgress(true);
        setGeocodingProgress('Geocoding locations... This may take a moment.');
        
        try {
          const { routes, uniqueRoutes } = await processBusData(busData);
          
          setRouteMapData(routes);
          setUniqueRoutes(uniqueRoutes.map(route => route.id));
          
          // Set default selected route if available
          if (uniqueRoutes.length > 0) {
            setSelectedRoute(uniqueRoutes[0].id);
          }
        } catch (geocodingError: any) {
          console.error('Geocoding error:', geocodingError);
          
          // Check for specific error messages related to API access
          const errorMessage = geocodingError.message || '';
          if (errorMessage.includes('NOT_FOUND') || errorMessage.includes('ZERO_RESULTS')) {
            setError('Could not find locations. Please check location names in your data.');
          } else if (errorMessage.includes('REQUEST_DENIED') || errorMessage.includes('INVALID_REQUEST')) {
            setError('API request was denied. Make sure your Google Maps API key is valid and has the necessary APIs enabled (Maps JavaScript API, Geocoding API, and Routes API).');
          } else if (errorMessage.includes('OVER_QUERY_LIMIT')) {
            setError('Google Maps API query limit exceeded. Try again later or upgrade your API plan.');
          } else {
            setError(`${errorMessage}. Please check your Google Maps API key and ensure all required APIs are enabled.`);
          }
        } finally {
          setGeocodingInProgress(false);
        }
      } catch (err: any) {
        console.error('Error fetching data:', err);
        setError(`Failed to load bus data: ${err.message || ''}`);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, []);

  const handleRouteSelect = (routeId: string) => {
    setSelectedRoute(routeId);
  };

  const handlePriceCalculationModeChange = (mode: 'highest' | 'lowest') => {
    console.log(`Changing price calculation mode to: ${mode}`);
    setPriceCalculationMode(mode);
  };

  return (
    <main className={styles.main}>
      <h1 className={styles.title}>
        <span className={styles.titleIcon}>🚌</span>
        RedBus Route Analysis
      </h1>
      
      {isLoading && <div className={styles.loading}>Loading bus data...</div>}
      
      {geocodingInProgress && (
        <div className={styles.loading}>{geocodingProgress}</div>
      )}
      
      {error && (
        <div className={styles.error}>
          <p>{error}</p>
          <p className={styles.errorHint}>
            Check your API key in the .env.local file and make sure all required APIs are enabled:
            <ul className={styles.errorList}>
              <li>Maps JavaScript API</li>
              <li>Geocoding API</li>
              <li>Routes API</li>
            </ul>
          </p>
        </div>
      )}
      
      {!isLoading && !error && (
        <>
          <SearchForm 
            uniqueRoutes={routeMapData.map(route => ({
              id: route.id,
              startLocation: route.startLocation,
              endLocation: route.endLocation
            }))}
            selectedRoute={selectedRoute}
            onRouteSelect={handleRouteSelect}
            priceCalculationMode={priceCalculationMode}
            onPriceCalculationModeChange={handlePriceCalculationModeChange}
          />
          
          <div className={styles.mapContainer}>
            <RouteMap 
              routeMapData={routeMapData}
              selectedRouteId={selectedRoute}
              onSelectRoute={handleRouteSelect}
              geocodingInProgress={geocodingInProgress}
            />
          </div>
          
          <BusDataTable 
            busData={rawBusData}
            selectedRoute={selectedRoute}
            priceCalculationMode={priceCalculationMode}
            routeMapData={routeMapData}
          />
        </>
      )}
    </main>
  );
}
