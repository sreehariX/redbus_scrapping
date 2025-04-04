'use client';

import React from 'react';
import { useState } from 'react';
import { BusRoute, RouteMapData } from '../types';
import styles from '../styles/BusDataTable.module.css';

interface BusDataTableProps {
  busData: BusRoute[];
  selectedRoute: string | null;
  priceCalculationMode: 'highest' | 'lowest';
  routeMapData: RouteMapData[];
}

// Helper function to parse duration strings like "05h 30m" into milliseconds
function parseDuration(durationStr: string): number {
  const match = durationStr.match(/(\d+)h\s*(\d+)m/);
  if (!match) return 0;
  
  const hours = parseInt(match[1]);
  const minutes = parseInt(match[2]);
  
  return (hours * 60 * 60 * 1000) + (minutes * 60 * 1000);
}

export default function BusDataTable({ 
  busData, 
  selectedRoute,
  priceCalculationMode,
  routeMapData
}: BusDataTableProps) {
  const [sortField, setSortField] = useState<keyof BusRoute | 'pricePerKm' | 'distance'>('pricePerKm');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Find the route distance and duration from routeMapData
  const getRouteInfo = (): { distance: number; duration: string } => {
    if (!selectedRoute) return { distance: 0, duration: '00h 00m' };
    
    const selectedRouteData = routeMapData.find(route => route.id === selectedRoute);
    return { 
      distance: selectedRouteData?.distance || 0,
      duration: selectedRouteData?.routeDuration || '00h 00m'
    };
  };

  const routeInfo = getRouteInfo();

  // Get price per km based on price calculation mode (now with 2 decimal places)
  const getPricePerKm = (bus: BusRoute) => {
    if (!selectedRoute || routeInfo.distance === 0) {
      return 0;
    }
    
    const price = priceCalculationMode === 'highest' 
      ? bus.highestPrice
      : bus.lowestPrice;
      
    // Keep exact decimal value with 2 places
    return parseFloat((price / routeInfo.distance).toFixed(2));
  };

  // Get price based on calculation mode
  const getPrice = (bus: BusRoute) => {
    return priceCalculationMode === 'highest'
      ? bus.highestPrice
      : bus.lowestPrice;
  };

  // Filter buses based on selected route
  const filteredBuses = selectedRoute 
    ? busData.filter(bus => {
        const routeKey = `${bus.startingPointParent}-${bus.destinationPointParent}`;
        return routeKey === selectedRoute;
      })
    : busData;

  // Sort buses based on the selected field and direction
  const sortedBuses = [...filteredBuses].sort((a, b) => {
    let valueA: number | string;
    let valueB: number | string;

    if (sortField === 'pricePerKm') {
      valueA = getPricePerKm(a) || 0;
      valueB = getPricePerKm(b) || 0;
    } else if (sortField === 'distance') {
      valueA = routeInfo.distance || 0;
      valueB = routeInfo.distance || 0;
    } else {
      valueA = a[sortField] || '';
      valueB = b[sortField] || '';
    }

    if (typeof valueA === 'number' && typeof valueB === 'number') {
      return sortDirection === 'asc' ? valueA - valueB : valueB - valueA;
    } else {
      valueA = valueA.toString();
      valueB = valueB.toString();
      return sortDirection === 'asc' 
        ? valueA.localeCompare(valueB) 
        : valueB.localeCompare(valueA);
    }
  });

  // Format price to INR
  const formatPrice = (price: number, isPerKm = false) => {
    if (isPerKm) {
      // For price/km, show exact 2 decimal places
      return `₹${price.toFixed(2)}/km`;
    }
    // For regular prices, keep existing formatting with no decimals
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', 
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  // Handle sort direction change
  const handleSort = (field: keyof BusRoute | 'pricePerKm' | 'distance') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Add this helper function before the return statement
  const getSortIcon = (field: keyof BusRoute | 'pricePerKm' | 'distance') => {
    if (sortField === field) {
      return <span className={styles.sortIcon}>{sortDirection === 'asc' ? '↑' : '↓'}</span>;
    }
    return null;
  };

  // Replace the responsive table with traditional table that includes horizontal scrolling
  return (
    <div className={styles.tableContainer}>
      <div className={styles.tableHeader}>
        <h2>Available Buses</h2>
        <div className={styles.priceModeSelector}>
          <span>Price calculation: {priceCalculationMode === 'lowest' ? 'Lowest Price' : 'Highest Price'}</span>
        </div>
      </div>

      {selectedRoute && (
        <div className={styles.routeInfo}>
          <div className={styles.routeDetails}>
            <div className={styles.routeDistance}>
              <span className={styles.routeInfoLabel}>Route distance:</span>
              <span className={styles.routeInfoValue}>{routeInfo.distance.toFixed(2)} km</span>
            </div>
          </div>
        </div>
      )}

      {filteredBuses.length === 0 ? (
        <div className={styles.noData}>No bus data available for this route.</div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.busTable}>
            <thead>
              <tr>
                <th onClick={() => handleSort('busName')}>
                  Bus Name {getSortIcon('busName')}
                </th>
                <th onClick={() => handleSort('busType')}>
                  Type {getSortIcon('busType')}
                </th>
                <th onClick={() => handleSort('pricePerKm')}>
                  Price/km {getSortIcon('pricePerKm')}
                </th>
                <th onClick={() => handleSort(priceCalculationMode === 'lowest' ? 'lowestPrice' : 'highestPrice')}>
                  Price {getSortIcon(priceCalculationMode === 'lowest' ? 'lowestPrice' : 'highestPrice')}
                </th>
                <th onClick={() => handleSort('distance')}>
                  Distance {getSortIcon('distance')}
                </th>
                <th onClick={() => handleSort('departureTime')}>
                  Departure {getSortIcon('departureTime')}
                </th>
                <th onClick={() => handleSort('arrivalTime')}>
                  Arrival {getSortIcon('arrivalTime')}
                </th>
                <th onClick={() => handleSort('journeyDuration')}>
                  Duration {getSortIcon('journeyDuration')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedBuses.map((bus) => {
                // Find best price and fastest buses
                const isBestPrice = priceCalculationMode === 'lowest' 
                  ? bus.lowestPrice === Math.min(...filteredBuses.map(b => b.lowestPrice))
                  : bus.highestPrice === Math.min(...filteredBuses.map(b => b.highestPrice));
                  
                const isFastest = bus.journeyDuration === 
                  filteredBuses.reduce((fastest, current) => {
                    // Convert duration string to minutes for comparison
                    const getFastestMinutes = (duration: string) => {
                      const match = duration.match(/(\d+)h\s*(\d+)m/);
                      if (match) {
                        return parseInt(match[1]) * 60 + parseInt(match[2]);
                      }
                      return 0;
                    };
                    
                    const fastestMinutes = getFastestMinutes(fastest.journeyDuration);
                    const currentMinutes = getFastestMinutes(current.journeyDuration);
                    
                    return currentMinutes < fastestMinutes ? current : fastest;
                  }, filteredBuses[0]).journeyDuration;
                
                return (
                  <tr key={bus.busId}>
                    <td className={styles.nameCell}>
                      {bus.busName}
                      <div className={styles.badgeContainer}>
                        {isBestPrice && <span className={styles.bestPriceBadge}>Best Value</span>}
                        {isFastest && <span className={styles.fastestBadge}>Fastest</span>}
                      </div>
                    </td>
                    <td>
                      <span className={styles.busTypeChip}>{bus.busType}</span>
                    </td>
                    <td className={styles.pricePerKmCell}>
                      {formatPrice(getPricePerKm(bus), true)}
                    </td>
                    <td className={styles.priceCell}>
                      {formatPrice(getPrice(bus))}
                    </td>
                    <td>{routeInfo.distance.toFixed(2)} km</td>
                    <td className={styles.timeCell}>{bus.departureTime}</td>
                    <td className={styles.timeCell}>{bus.arrivalTime}</td>
                    <td className={styles.durationCell}>{bus.journeyDuration}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
} 