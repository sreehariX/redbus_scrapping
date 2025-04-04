'use client';

import { useState } from 'react';
import { BusRoute } from '../types';
import styles from '../styles/BusDataTable.module.css';

interface BusDataTableProps {
  buses: BusRoute[];
  priceCalculationMode: 'highest' | 'lowest';
  onChangePriceMode: (mode: 'highest' | 'lowest') => void;
}

export default function BusDataTable({ 
  buses, 
  priceCalculationMode, 
  onChangePriceMode 
}: BusDataTableProps) {
  const [sortField, setSortField] = useState<keyof BusRoute | 'pricePerKm'>('pricePerKm');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Handle sort direction change
  const handleSort = (field: keyof BusRoute | 'pricePerKm') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Get price per km based on price calculation mode
  const getPricePerKm = (bus: BusRoute) => {
    return priceCalculationMode === 'highest' 
      ? bus.pricePerKmHigh 
      : bus.pricePerKmLow;
  };

  // Sort buses based on the selected field and direction
  const sortedBuses = [...buses].sort((a, b) => {
    let valueA: number | string;
    let valueB: number | string;

    if (sortField === 'pricePerKm') {
      valueA = getPricePerKm(a) || 0;
      valueB = getPricePerKm(b) || 0;
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
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', 
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  return (
    <div className={styles.tableContainer}>
      <div className={styles.tableHeader}>
        <h2>Available Buses</h2>
        <div className={styles.priceModeSelector}>
          <span>Price calculation:</span>
          <div className={styles.toggleContainer}>
            <button 
              className={`${styles.toggleButton} ${priceCalculationMode === 'lowest' ? styles.active : ''}`}
              onClick={() => onChangePriceMode('lowest')}
            >
              Lowest Price
            </button>
            <button 
              className={`${styles.toggleButton} ${priceCalculationMode === 'highest' ? styles.active : ''}`}
              onClick={() => onChangePriceMode('highest')}
            >
              Highest Price
            </button>
          </div>
        </div>
      </div>

      {buses.length > 0 ? (
        <div className={styles.tableWrapper}>
          <table className={styles.busTable}>
            <thead>
              <tr>
                <th onClick={() => handleSort('busName')}>
                  Bus Name
                  {sortField === 'busName' && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
                <th onClick={() => handleSort('busType')}>
                  Type
                  {sortField === 'busType' && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
                <th onClick={() => handleSort('departureTime')}>
                  Departure
                  {sortField === 'departureTime' && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
                <th onClick={() => handleSort('arrivalTime')}>
                  Arrival
                  {sortField === 'arrivalTime' && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
                <th onClick={() => handleSort('journeyDuration')}>
                  Duration
                  {sortField === 'journeyDuration' && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
                <th onClick={() => handleSort(priceCalculationMode === 'highest' ? 'highestPrice' : 'lowestPrice')}>
                  Price
                  {(sortField === 'highestPrice' || sortField === 'lowestPrice') && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
                <th onClick={() => handleSort('pricePerKm')}>
                  Price/km
                  {sortField === 'pricePerKm' && (
                    <span className={styles.sortIcon}>
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedBuses.map((bus) => (
                <tr key={bus.busId}>
                  <td>{bus.busName}</td>
                  <td>{bus.busType}</td>
                  <td>{bus.departureTime}</td>
                  <td>{bus.arrivalTime}</td>
                  <td>{bus.journeyDuration}</td>
                  <td>
                    {priceCalculationMode === 'highest' 
                      ? formatPrice(bus.highestPrice) 
                      : formatPrice(bus.lowestPrice)}
                  </td>
                  <td>
                    ₹{getPricePerKm(bus).toFixed(2)}/km
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className={styles.noData}>
          <p>No buses found for the selected route.</p>
        </div>
      )}
    </div>
  );
} 