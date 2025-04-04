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
  onSelectRoute: (routeId: string) => void;
  priceCalculationMode: 'highest' | 'lowest';
  onPriceCalculationModeChange: (mode: 'highest' | 'lowest') => void;
}

export default function SearchForm({ 
  uniqueRoutes, 
  selectedRoute, 
  onSelectRoute, 
  priceCalculationMode, 
  onPriceCalculationModeChange
}: SearchFormProps) {
  return (
    <div className={styles.formContainer}>
      <h2 className={styles.formTitle}>Search Bus Routes</h2>
      
      <div className={styles.form}>
        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>
            <span className={styles.routeIcon}>🚌</span>
            Select Route:
          </label>
          <div className={styles.selectWrapper}>
            <select 
              className={styles.select}
              value={selectedRoute || ''}
              onChange={(e) => onSelectRoute(e.target.value)}
            >
              <option value="" disabled>Select a route</option>
              {uniqueRoutes.map((route) => {
                const [start, end] = route.id.split('-');
                return (
                  <option key={route.id} value={route.id}>
                    {start} → {end}
                  </option>
                );
              })}
            </select>
          </div>
        </div>
        
        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>
            <span className={styles.routeIcon}>💰</span>
            Price Calculation:
          </label>
          <div className={styles.priceToggle}>
            <button
              className={`${styles.priceButton} ${priceCalculationMode === 'lowest' ? styles.active : ''}`}
              onClick={() => onPriceCalculationModeChange('lowest')}
            >
              Lowest Price
            </button>
            <button
              className={`${styles.priceButton} ${priceCalculationMode === 'highest' ? styles.active : ''}`}
              onClick={() => onPriceCalculationModeChange('highest')}
            >
              Highest Price
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 