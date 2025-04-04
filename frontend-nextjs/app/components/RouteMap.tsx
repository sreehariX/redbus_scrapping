'use client';

import React, { useState, useEffect } from 'react';
import { GoogleMap, useJsApiLoader, Marker, InfoWindow, Polyline } from '@react-google-maps/api';
import { RouteMapData } from '../types';
import { 
  FALLBACK_CENTER, 
  MAP_ZOOM, 
  CONTAINER_STYLE, 
  MAP_OPTIONS, 
  MARKER_ICONS,
  ROUTE_COLORS
} from '../config/mapConfig';
import styles from '../styles/RouteMap.module.css';

// Google Maps API Key from environment variables
const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";

interface RouteMapProps {
  routeMapData: RouteMapData[];
  selectedRouteId: string | null;
  geocodingInProgress: boolean;
  onSelectRoute: (routeId: string) => void;
}

export default function RouteMap({ 
  routeMapData: routes, 
  selectedRouteId, 
  onSelectRoute: onRouteClick,
  geocodingInProgress
}: RouteMapProps) {
  const [mapKey, setMapKey] = useState(Date.now());
  const [activeMarker, setActiveMarker] = useState<string | null>(null);
  const [hoveredRouteId, setHoveredRouteId] = useState<string | null>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [showMarkerAnimation, setShowMarkerAnimation] = useState(true);
  
  // Load Google Maps JavaScript API
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey
  });
  
  const onLoad = (map: google.maps.Map) => {
    setMap(map);
  };
  
  const onUnmount = () => {
    setMap(null);
  };
  
  // Force re-render of map when routes change
  useEffect(() => {
    setMapKey(Date.now());
  }, [routes.length]);
  
  // Stop marker animation after 3 seconds and reset map when route changes
  useEffect(() => {
    if (selectedRouteId) {
      // Clear any previous polylines by forcing a map re-render when route changes
      setMapKey(Date.now());
      
      // Show animation for new markers
      setShowMarkerAnimation(true);
      const timer = setTimeout(() => {
        setShowMarkerAnimation(false);
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [selectedRouteId]);
  
  // Calculate the center of the map based on the selected route or all routes
  const getMapCenter = () => {
    if (geocodingInProgress || routes.length === 0) {
      return FALLBACK_CENTER;
    }
    
    const routeToCenter = routes.find(r => r.id === selectedRouteId);
    if (routeToCenter && routeToCenter.startCoords && routeToCenter.endCoords) {
      return {
        lat: (routeToCenter.startCoords.lat + routeToCenter.endCoords.lat) / 2,
        lng: (routeToCenter.startCoords.lng + routeToCenter.endCoords.lng) / 2
      };
    }

    // Calculate average of all route centers
    const sum = routes.reduce((acc, route) => {
      if (route.startCoords && route.endCoords) {
        return {
          lat: acc.lat + (route.startCoords.lat + route.endCoords.lat) / 2,
          lng: acc.lng + (route.startCoords.lng + route.endCoords.lng) / 2
        };
      }
      return acc;
    }, { lat: 0, lng: 0 });

    const validRoutes = routes.filter(
      route => route.startCoords && route.endCoords
    ).length;

    return validRoutes > 0 
      ? { lat: sum.lat / validRoutes, lng: sum.lng / validRoutes } 
      : FALLBACK_CENTER;
  };
  
  // Determine map zoom level
  const getMapZoom = () => {
    const routeToCenter = routes.find(route => route.id === selectedRouteId);
    return routeToCenter ? MAP_ZOOM.selected : MAP_ZOOM.default;
  };
  
  // Handle marker click
  const handleMarkerClick = (markerId: string) => {
    setActiveMarker(markerId);
  };
  
  // Handle info window close
  const handleInfoWindowClose = () => {
    setActiveMarker(null);
  };
  
  // Check if we have valid coordinates for any route
  if (!isLoaded) {
    return <div className={styles.mapContainer}><div className={styles.loading}>Loading map...</div></div>;
  }

  if (loadError) {
    return (
      <div className={styles.mapContainer}>
        <div className={styles.mapError}>
          <p>Error loading Google Maps API</p>
          <p>Please check your API key configuration and ensure it has the Maps JavaScript API enabled.</p>
        </div>
      </div>
    );
  }
  
  if (geocodingInProgress) {
    return <div className={styles.mapLoading}>Geocoding locations... Please wait.</div>;
  }

  const hasValidCoordinates = routes.some(route => 
    route.startCoords && route.endCoords
  );

  if (!hasValidCoordinates) {
    return <div className={styles.mapError}>No valid coordinates available for routes.</div>;
  }

  // Find the selected route
  const selectedRoute = selectedRouteId ? routes.find(route => route.id === selectedRouteId) : null;

  return (
    <div className={styles.mapContainer}>
      <GoogleMap
        key={mapKey}
        mapContainerStyle={CONTAINER_STYLE}
        center={getMapCenter()}
        zoom={getMapZoom()}
        onLoad={onLoad}
        onUnmount={onUnmount}
        options={MAP_OPTIONS}
      >
        {/* Display all routes - thin gray lines for non-selected routes */}
        {routes.map(route => {
          if (!route.startCoords || !route.endCoords) return null;
          
          const isSelected = route.id === selectedRouteId;
          const isHovered = route.id === hoveredRouteId && !isSelected;
          
          // Skip selected route - will be rendered separately with thicker line
          if (isSelected) return null;
          
          return (
            <Polyline
              key={`line-${route.id}`}
              path={[route.startCoords, route.endCoords]}
              options={{
                strokeWeight: 4,
                strokeColor: isHovered ? ROUTE_COLORS.hover : ROUTE_COLORS.default,
                strokeOpacity: 0.8,
                zIndex: 1,
                clickable: true,
                geodesic: true
              }}
              onClick={() => onRouteClick(route.id)}
              onMouseOver={() => {
                setHoveredRouteId(route.id);
                document.body.style.cursor = 'pointer';
              }}
              onMouseOut={() => {
                setHoveredRouteId(null);
                document.body.style.cursor = 'default';
              }}
            />
          );
        })}
        
        {/* Render selected route with markers and yellow highlight */}
        {selectedRoute && selectedRoute.startCoords && selectedRoute.endCoords && (
          <React.Fragment key={`selected-${selectedRoute.id}`}>
            {/* Start marker */}
            <Marker
              position={selectedRoute.startCoords}
              onClick={() => handleMarkerClick(`start-${selectedRoute.id}`)}
              icon={MARKER_ICONS.start}
              label={{
                text: selectedRoute.startLocation,
                className: styles.markerLabel,
                fontWeight: '500',
                fontSize: '13px',
                color: '#333333'
              }}
              animation={showMarkerAnimation ? window.google?.maps.Animation.BOUNCE : undefined}
            >
              {activeMarker === `start-${selectedRoute.id}` && (
                <InfoWindow onCloseClick={handleInfoWindowClose}>
                  <div className={styles.infoWindow}>
                    <h3 className={styles.infoTitle}>{selectedRoute.startLocation}</h3>
                    <p className={styles.infoText}>Starting point for route to {selectedRoute.endLocation}</p>
                    <p className={styles.infoText}>Distance: {selectedRoute.distance.toFixed(2)} km</p>
                  </div>
                </InfoWindow>
              )}
            </Marker>
            
            {/* End marker */}
            <Marker
              position={selectedRoute.endCoords}
              onClick={() => handleMarkerClick(`end-${selectedRoute.id}`)}
              icon={MARKER_ICONS.end}
              label={{
                text: selectedRoute.endLocation,
                className: styles.markerLabel,
                fontWeight: '500',
                fontSize: '13px',
                color: '#333333'
              }}
              animation={showMarkerAnimation ? window.google?.maps.Animation.BOUNCE : undefined}
            >
              {activeMarker === `end-${selectedRoute.id}` && (
                <InfoWindow onCloseClick={handleInfoWindowClose}>
                  <div className={styles.infoWindow}>
                    <h3 className={styles.infoTitle}>{selectedRoute.endLocation}</h3>
                    <p className={styles.infoText}>Destination from {selectedRoute.startLocation}</p>
                    <p className={styles.infoText}>Distance: {selectedRoute.distance.toFixed(2)} km</p>
                  </div>
                </InfoWindow>
              )}
            </Marker>
            
            {/* Polyline for selected route - yellow and thicker */}
            <Polyline
              path={[selectedRoute.startCoords, selectedRoute.endCoords]}
              options={{
                strokeWeight: 6,
                strokeColor: ROUTE_COLORS.selected,
                strokeOpacity: 1,
                zIndex: 100,
                clickable: true,
                geodesic: true
              }}
            />
          </React.Fragment>
        )}
      </GoogleMap>
    </div>
  );
} 