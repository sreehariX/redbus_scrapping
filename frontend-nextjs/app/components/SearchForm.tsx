'use client';

import React, { useState, useEffect } from 'react';
import styles from '../styles/SearchForm.module.css';

interface RouteOption {
  id: string;
  startLocation: string;
  endLocation: string;
}

interface SearchFormProps {
  uniqueRoutes: RouteOption[];
  selectedRoute: string | null;
  onRouteSelect: (routeId: string) => void;
  priceCalculationMode: 'highest' | 'lowest';
  onPriceCalculationModeChange: (mode: 'highest' | 'lowest') => void;
}

export default function SearchForm({ 
  uniqueRoutes, 
  selectedRoute,
  onRouteSelect,
  priceCalculationMode,
  onPriceCalculationModeChange
}: SearchFormProps) {
  const handleRouteChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onRouteSelect(e.target.value);
  };

  const handlePriceModeChange = (mode: 'highest' | 'lowest') => {
    onPriceCalculationModeChange(mode);
  };

  // Get the display text for each route
  const getRouteDisplayText = (route: RouteOption) => {
    return `${route.startLocation} → ${route.endLocation}`;
  };

  return (
    <div className={styles.formContainer}>
      <h2 className={styles.formTitle}>Search Bus Routes</h2>
      <form className={styles.form}>
        <div className={styles.inputGroup}>
          <label htmlFor="routeSelection" className={styles.inputLabel}>
            <span className={styles.routeIcon}>🚍</span> Select Route:
          </label>
          <div className={styles.selectWrapper}>
            <select 
              id="routeSelection" 
              value={selectedRoute || ''}
              onChange={handleRouteChange}
              className={styles.select}
            >
              <option value="" disabled>Select a route</option>
              {uniqueRoutes.map(route => (
                <option key={route.id} value={route.id}>
                  {getRouteDisplayText(route)}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>
            <span className={styles.routeIcon}>💰</span> Price Calculation:
          </label>
          <div className={styles.toggleGroup}>
            <button 
              type="button"
              className={`${styles.toggleButton} ${priceCalculationMode === 'lowest' ? styles.active : ''}`}
              onClick={() => handlePriceModeChange('lowest')}
            >
              Lowest Price
            </button>
            <button 
              type="button"
              className={`${styles.toggleButton} ${priceCalculationMode === 'highest' ? styles.active : ''}`}
              onClick={() => handlePriceModeChange('highest')}
            >
              Highest Price
            </button>
          </div>
        </div>
      </form>
    </div>
  );
} 