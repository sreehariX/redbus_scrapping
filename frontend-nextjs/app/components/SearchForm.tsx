'use client';

import { useState, useEffect } from 'react';
import styles from '../styles/SearchForm.module.css';

interface SearchFormProps {
  uniqueRoutes: { id: string; startLocation: string; endLocation: string }[];
  onRouteSelect: (routeId: string) => void;
  selectedRoute: string | null;
}

export default function SearchForm({ 
  uniqueRoutes, 
  onRouteSelect, 
  selectedRoute 
}: SearchFormProps) {
  const [startLocations, setStartLocations] = useState<string[]>([]);
  const [endLocations, setEndLocations] = useState<string[]>([]);
  const [selectedStart, setSelectedStart] = useState<string>('');
  const [selectedEnd, setSelectedEnd] = useState<string>('');

  // Extract unique start and end locations
  useEffect(() => {
    if (uniqueRoutes.length > 0) {
      const starts = [...new Set(uniqueRoutes.map(route => route.startLocation))];
      setStartLocations(starts);
      
      // If a start location is already selected, filter end locations
      if (selectedStart) {
        const ends = [...new Set(
          uniqueRoutes
            .filter(route => route.startLocation === selectedStart)
            .map(route => route.endLocation)
        )];
        setEndLocations(ends);
      } else {
        // If no start location is selected, set the first one
        setSelectedStart(starts[0] || '');
      }
    }
  }, [uniqueRoutes, selectedStart]);

  // Update end locations when start location changes
  useEffect(() => {
    if (selectedStart) {
      const ends = [...new Set(
        uniqueRoutes
          .filter(route => route.startLocation === selectedStart)
          .map(route => route.endLocation)
      )];
      setEndLocations(ends);
      
      // Set first end location as default
      if (ends.length > 0 && (!selectedEnd || !ends.includes(selectedEnd))) {
        setSelectedEnd(ends[0]);
      } else if (ends.length === 0) {
        setSelectedEnd('');
      }
    } else {
      setEndLocations([]);
      setSelectedEnd('');
    }
  }, [selectedStart, uniqueRoutes, selectedEnd]);

  // Find route ID based on selected start and end locations
  useEffect(() => {
    if (selectedStart && selectedEnd) {
      const route = uniqueRoutes.find(
        r => r.startLocation === selectedStart && r.endLocation === selectedEnd
      );
      
      if (route) {
        onRouteSelect(route.id);
      }
    }
  }, [selectedStart, selectedEnd, uniqueRoutes, onRouteSelect]);

  // Update selected start and end when route changes
  useEffect(() => {
    if (selectedRoute) {
      const route = uniqueRoutes.find(r => r.id === selectedRoute);
      if (route) {
        setSelectedStart(route.startLocation);
        setSelectedEnd(route.endLocation);
      }
    }
  }, [selectedRoute, uniqueRoutes]);

  const handleStartChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedStart(e.target.value);
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedEnd(e.target.value);
  };

  return (
    <div className={styles.formContainer}>
      <h2>Search Bus Routes</h2>
      <form className={styles.form}>
        <div className={styles.inputGroup}>
          <label htmlFor="startLocation">From:</label>
          <select 
            id="startLocation" 
            value={selectedStart}
            onChange={handleStartChange}
            className={styles.select}
          >
            {startLocations.map(location => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
        </div>
        
        <div className={styles.inputGroup}>
          <label htmlFor="endLocation">To:</label>
          <select 
            id="endLocation" 
            value={selectedEnd}
            onChange={handleEndChange}
            className={styles.select}
            disabled={endLocations.length === 0}
          >
            {endLocations.map(location => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
        </div>
      </form>
    </div>
  );
} 