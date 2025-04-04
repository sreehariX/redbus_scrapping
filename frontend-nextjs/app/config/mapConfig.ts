/**
 * Map Configuration
 * This file contains configuration settings for Google Maps
 */

// Fallback center when no routes are available (Location: Central India)
export const FALLBACK_CENTER = { lat: 22.5937, lng: 78.9629 };

// Zoom levels for different map states
export const MAP_ZOOM = {
  default: 0, // Lower zoom level to show all of India
  selected: 6
};

// Container style for Google Map component
export const CONTAINER_STYLE = {
  width: '100%',
  height: '500px',
  borderRadius: '12px',
};

// Default options for Google Map
export const MAP_OPTIONS = {
  disableDefaultUI: false,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: true,
  // Clean styling for better route visibility
  styles: [
    {
      featureType: 'poi',
      elementType: 'labels',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'transit',
      elementType: 'labels',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'road',
      elementType: 'labels.icon',
      stylers: [{ visibility: 'off' }]
    }
  ]
};

// Marker icons for start and end points
export const MARKER_ICONS = {
  start: {
    path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
    fillColor: '#0f9d58',
    fillOpacity: 0.9,
    scale: 1.5,
    strokeColor: '#ffffff',
    strokeWeight: 1
  },
  end: {
    path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
    fillColor: '#db4437',
    fillOpacity: 0.9,
    scale: 1.5,
    strokeColor: '#ffffff',
    strokeWeight: 1
  }
};

// Route colors
export const ROUTE_COLORS = {
  selected: '#FFCC00', // Brighter yellow for selected route
  hover: '#FFC107',   // Amber for hover
  default: '#0052CC'  // Darker blue for better visibility
};

// Function to get polyline options based on selection state
export function getPolylineOptions(isSelected: boolean) {
  return {
    strokeWeight: isSelected ? 6 : 4,
    strokeColor: isSelected ? ROUTE_COLORS.selected : ROUTE_COLORS.default,
    strokeOpacity: isSelected ? 1 : 0.8,
    zIndex: isSelected ? 100 : 1,
    clickable: true,
    geodesic: true
  };
} 