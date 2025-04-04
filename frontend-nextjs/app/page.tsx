'use client';

import { useState, useEffect } from 'react';
import { parseBusData, processBusData } from './services/busDataService';
import { BusRoute, RouteMapData } from './types';
import SearchForm from './components/SearchForm';
import RouteMap from './components/RouteMap';
import BusDataTable from './components/BusDataTable';
import styles from './page.module.css';

export default function Home() {
  const [busData, setBusData] = useState<BusRoute[]>([]);
  const [routes, setRoutes] = useState<RouteMapData[]>([]);
  const [uniqueRoutes, setUniqueRoutes] = useState<{id: string; startLocation: string; endLocation: string}[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [priceCalculationMode, setPriceCalculationMode] = useState<'highest' | 'lowest'>('lowest');

  // Fetch and process bus data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await parseBusData('/data/bus_data.csv');
        
        // Check if we got valid data
        if (!data || data.length === 0) {
          setError('No bus data available. Please check the CSV file.');
          setLoading(false);
          return;
        }
        
        const { routes: routesData, uniqueRoutes: uniqueRoutesData } = processBusData(data);
        
        setBusData(data);
        setRoutes(routesData);
        
        // Transform unique routes into the expected format
        const formattedUniqueRoutes = routesData.map(route => ({
          id: route.id,
          startLocation: route.startLocation,
          endLocation: route.endLocation
        }));
        
        setUniqueRoutes(formattedUniqueRoutes);
        
        // Set default selected route
        if (formattedUniqueRoutes.length > 0 && !selectedRoute) {
          setSelectedRoute(formattedUniqueRoutes[0].id);
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching bus data:', err);
        setError('Failed to load bus data. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchData();
  }, [selectedRoute]);

  // Handle route selection
  const handleRouteSelect = (routeId: string) => {
    setSelectedRoute(routeId);
  };

  // Handle price calculation mode change
  const handlePriceModeChange = (mode: 'highest' | 'lowest') => {
    setPriceCalculationMode(mode);
  };

  // Get buses for the selected route
  const getSelectedRouteBuses = (): BusRoute[] => {
    if (!selectedRoute) return [];
    
    const selectedRouteData = routes.find(route => route.id === selectedRoute);
    if (!selectedRouteData) return [];
    
    return selectedRouteData.buses;
  };

  return (
    <main className={styles.main}>
      <div className="container">
        <header className={styles.header}>
          <h1>RedBus Route Analysis</h1>
          <p>Find the most cost-effective bus routes between cities in India</p>
        </header>

        {loading ? (
          <div className="card">
            <div className={styles.loading}>Loading bus data...</div>
          </div>
        ) : error ? (
          <div className="card">
            <div className={styles.error}>{error}</div>
          </div>
        ) : (
          <>
            <SearchForm 
              uniqueRoutes={uniqueRoutes}
              onRouteSelect={handleRouteSelect}
              selectedRoute={selectedRoute}
            />
            
            <RouteMap 
              routes={routes}
              selectedRoute={selectedRoute}
              onRouteClick={handleRouteSelect}
              priceCalculationMode={priceCalculationMode}
            />
            
            <BusDataTable 
              buses={getSelectedRouteBuses()}
              priceCalculationMode={priceCalculationMode}
              onChangePriceMode={handlePriceModeChange}
            />
          </>
        )}
      </div>
    </main>
  );
}
