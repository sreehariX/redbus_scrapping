'use client';

import { useState, useCallback, useEffect } from 'react';
import { GoogleMap, useJsApiLoader, Marker, InfoWindow, Polyline } from '@react-google-maps/api';
import { RouteMapData, BusRoute } from '../types';
import styles from '../styles/RouteMap.module.css';

// Google Maps API Key - Replace with your actual API key
const googleMapsApiKey = "YOUR_GOOGLE_MAPS_API_KEY";

// Default map container style
const containerStyle = {
  width: '100%',
  height: '100%'
};

interface RouteMapProps {
  routes: RouteMapData[];
  selectedRoute: string | null;
  onRouteClick: (routeId: string) => void;
  priceCalculationMode: 'highest' | 'lowest';
}

export default function RouteMap({ 
  routes, 
  selectedRoute, 
  onRouteClick,
  priceCalculationMode 
}: RouteMapProps) {
  const [mapKey, setMapKey] = useState(Date.now());
  const [activeMarker, setActiveMarker] = useState<string | null>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  
  // Load Google Maps JavaScript API
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey
  });
  
  // Handle map load event
  const onLoad = useCallback((map: google.maps.Map) => {
    setMap(map);
  }, []);
  
  // Handle map unmount event
  const onUnmount = useCallback(() => {
    setMap(null);
  }, []);
  
  // Force re-render of map when routes change
  useEffect(() => {
    setMapKey(Date.now());
  }, [routes.length]);
  
  // Determine map center - if a route is selected, center on that route
  // otherwise use a default center
  const getMapCenter = () => {
    if (selectedRoute && routes.length > 0) {
      const route = routes.find(r => r.id === selectedRoute);
      if (route) {
        const midLat = (route.startCoords.lat + route.endCoords.lat) / 2;
        const midLng = (route.startCoords.lng + route.endCoords.lng) / 2;
        return { lat: midLat, lng: midLng };
      }
    }
    
    // Default center (India)
    return { lat: 20.5937, lng: 78.9629 };
  };
  
  // Determine map zoom level
  const getMapZoom = () => {
    return selectedRoute ? 6 : 5;
  };
  
  // Format price per km
  const formatPricePerKm = (bus: BusRoute) => {
    const price = priceCalculationMode === 'highest' ? bus.pricePerKmHigh : bus.pricePerKmLow;
    return price?.toFixed(2) || 'N/A';
  };
  
  // Handle marker click
  const handleMarkerClick = (markerId: string) => {
    setActiveMarker(markerId);
  };
  
  // Handle info window close
  const handleInfoWindowClose = () => {
    setActiveMarker(null);
  };
  
  // Don't render the map if the API is not loaded or if there's an error
  if (loadError) {
    return <div className={styles.mapContainer}><div className={styles.error}>Error loading Google Maps API</div></div>;
  }
  
  if (!isLoaded) {
    return <div className={styles.mapContainer}><div className={styles.loading}>Loading map...</div></div>;
  }

  return (
    <div className={styles.mapContainer}>
      <GoogleMap
        key={mapKey}
        mapContainerStyle={containerStyle}
        center={getMapCenter()}
        zoom={getMapZoom()}
        onLoad={onLoad}
        onUnmount={onUnmount}
        options={{
          fullscreenControl: false,
          streetViewControl: false,
          mapTypeControl: true,
          zoomControl: true
        }}
      >
        {routes.map(route => (
          <>
            {/* Start Marker */}
            <Marker
              key={`start-${route.id}`}
              position={{ lat: route.startCoords.lat, lng: route.startCoords.lng }}
              onClick={() => handleMarkerClick(`start-${route.id}`)}
              icon={{
                url: "http://maps.google.com/mapfiles/ms/icons/green-dot.png"
              }}
            >
              {activeMarker === `start-${route.id}` && (
                <InfoWindow onCloseClick={handleInfoWindowClose}>
                  <div>
                    <h3 style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{route.startLocation}</h3>
                    <p style={{ margin: '0 0 3px 0' }}>Starting point for route to {route.endLocation}</p>
                    <p style={{ margin: '0' }}>
                      <button 
                        style={{
                          padding: '5px 10px',
                          background: '#0070f3',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                        onClick={() => onRouteClick(route.id)}
                      >
                        View buses
                      </button>
                    </p>
                  </div>
                </InfoWindow>
              )}
            </Marker>
            
            {/* End Marker */}
            <Marker
              key={`end-${route.id}`}
              position={{ lat: route.endCoords.lat, lng: route.endCoords.lng }}
              onClick={() => handleMarkerClick(`end-${route.id}`)}
              icon={{
                url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png"
              }}
            >
              {activeMarker === `end-${route.id}` && (
                <InfoWindow onCloseClick={handleInfoWindowClose}>
                  <div>
                    <h3 style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{route.endLocation}</h3>
                    <p style={{ margin: '0 0 3px 0' }}>Destination from {route.startLocation}</p>
                    <p style={{ margin: '0 0 3px 0' }}>Distance: {route.distance.toFixed(2)} km</p>
                    <p style={{ margin: '0' }}>
                      <button 
                        style={{
                          padding: '5px 10px',
                          background: '#0070f3',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                        onClick={() => onRouteClick(route.id)}
                      >
                        View buses
                      </button>
                    </p>
                  </div>
                </InfoWindow>
              )}
            </Marker>
            
            {/* Route Polyline */}
            <Polyline
              key={`polyline-${route.id}`}
              path={[
                { lat: route.startCoords.lat, lng: route.startCoords.lng },
                { lat: route.endCoords.lat, lng: route.endCoords.lng }
              ]}
              options={{
                strokeColor: selectedRoute === route.id ? '#FF0000' : '#0000FF',
                strokeOpacity: 0.8,
                strokeWeight: selectedRoute === route.id ? 5 : 3,
                clickable: true
              }}
              onClick={() => onRouteClick(route.id)}
            />
          </>
        ))}
      </GoogleMap>
    </div>
  );
} 