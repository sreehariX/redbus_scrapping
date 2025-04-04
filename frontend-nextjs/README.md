# RedBus Route Analysis Frontend

This Next.js application provides a visual interface for analyzing RedBus routes and finding the most cost-effective bus journeys. 

## Features

- Interactive Google Maps interface to visualize bus routes
- Dynamic geocoding of locations using Google Maps Geocoding API
- Price per kilometer calculation
- Filtering and sorting by various criteria
- Responsive design for both desktop and mobile devices

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Google Maps API key with the following APIs enabled:
  - Maps JavaScript API
  - Geocoding API

### Setup

1. Clone the repository
2. Navigate to the project directory
3. Install dependencies:

```bash
npm install
```

4. Create a `.env.local` file in the root directory and add your Google Maps API key:

```
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

5. Make sure your Google Maps API key has the necessary APIs enabled:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "APIs & Services" > "Dashboard"
   - Click "ENABLE APIS AND SERVICES"
   - Search for and enable both "Maps JavaScript API" and "Geocoding API"
   - Ensure your API key is not restricted or has the appropriate restrictions set up
   - Make sure billing is enabled for your Google Cloud project

### Common API Issues

If you encounter errors like `REQUEST_DENIED`, check the following:

- Verify that your API key is correctly set in the `.env.local` file
- Ensure both Maps JavaScript API and Geocoding API are enabled
- Check if your key has any restrictions that might block the geocoding requests
- Verify that billing is set up for your Google Cloud project (required for API usage)

### Running the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### Building for Production

```bash
npm run build
```

Then, start the production server:

```bash
npm start
```

## Project Structure

- `/app` - Next.js app directory
  - `/components` - React components
  - `/services` - Service utilities
  - `/styles` - CSS modules
  - `/types` - TypeScript type definitions
  - `/config` - Configuration files
- `/public` - Static assets
  - `/data` - CSV data files

## Technologies Used

- Next.js 14
- TypeScript
- Google Maps API for map visualizations and geocoding
- Papaparse for CSV parsing
- Tailwind CSS for styling

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
