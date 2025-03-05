#!/usr/bin/env python3
"""
Flight Planner Server using FastMCP

An MCP server that uses the fast-flights API to search for flight information,
with comprehensive airport data from a public CSV source.
"""

import sys
import os
import json
import csv
import io
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

# Print debug info to stderr (will be captured in Claude logs)
print("Starting Flight Planner server...", file=sys.stderr)

try:
    from fastmcp import FastMCP, Context
    print("Successfully imported FastMCP", file=sys.stderr)
except ImportError as e:
    print(f"Error importing FastMCP: {e}", file=sys.stderr)
    print("Please install FastMCP with: uv pip install fastmcp", file=sys.stderr)
    sys.exit(1)

# Constants
CSV_URL = "https://raw.githubusercontent.com/mborsetti/airportsdata/refs/heads/main/airportsdata/airports.csv"
DEFAULT_CONFIG = {
    "max_results": 10,
    "default_trip_days": 7,
    "default_advance_days": 30,
    "seat_classes": ["economy", "premium_economy", "business", "first"]
}
AIRPORTS_CACHE_FILE = Path(__file__).parent / "airports_cache.json"

# Global variables
airports = {}

# Fetch airport data from CSV
async def fetch_airports_csv(url: str = CSV_URL) -> Dict[str, str]:
    """Fetch airport data from a CSV URL."""
    print(f"Fetching airports from {url}", file=sys.stderr)
    
    try:
        import aiohttp
        
        airports_data = {}
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Error fetching CSV: HTTP {response.status}", file=sys.stderr)
                    return {}
                
                csv_text = await response.text()
                csv_reader = csv.DictReader(io.StringIO(csv_text))
                
                for row in csv_reader:
                    iata = row.get('iata', '')
                    name = row.get('name', '')
                    city = row.get('city', '')
                    country = row.get('country', '')
                    
                    # Only store entries with a valid IATA code (3 uppercase letters)
                    if iata and len(iata) == 3 and iata.isalpha() and iata.isupper():
                        # Include city and country in the name for better context
                        full_name = f"{name}, {city}, {country}" if city else f"{name}, {country}"
                        airports_data[iata] = full_name
                
                print(f"Loaded {len(airports_data)} airports from CSV", file=sys.stderr)
                
                # Save to cache file
                try:
                    with open(AIRPORTS_CACHE_FILE, 'w') as f:
                        json.dump(airports_data, f)
                    print(f"Saved airports to cache file: {AIRPORTS_CACHE_FILE}", file=sys.stderr)
                except Exception as cache_e:
                    print(f"Warning: Could not save airports cache: {cache_e}", file=sys.stderr)
                
                return airports_data
    except ImportError:
        print("aiohttp not installed. Cannot fetch airports CSV.", file=sys.stderr)
        print("Please install with: uv pip install aiohttp", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Error fetching airports: {e}", file=sys.stderr)
        return {}

# Load airports from cache if available
def load_airports_cache() -> Dict[str, str]:
    """Load airports from cache file if available."""
    if AIRPORTS_CACHE_FILE.exists():
        try:
            with open(AIRPORTS_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                print(f"Loaded {len(cache)} airports from cache", file=sys.stderr)
                return cache
        except Exception as e:
            print(f"Error loading airports cache: {e}", file=sys.stderr)
    return {}

# Initialize the FastMCP server with dependencies
mcp = FastMCP(
    "Flight Planner", 
    dependencies=["fast-flights", "aiohttp"]
)

@mcp.tool()
def search_flights(
    from_airport: str, 
    to_airport: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    seat_class: str = "economy",
    ctx: Context = None
) -> str:
    """
    Search for flights between two airports.

    Args:
        from_airport: Departure airport code (3-letter IATA code, e.g., 'LAX')
        to_airport: Arrival airport code (3-letter IATA code, e.g., 'JFK')
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format (optional, for round trips)
        adults: Number of adult passengers (default: 1)
        children: Number of children (default: 0)
        infants_in_seat: Number of infants in seat (default: 0)
        infants_on_lap: Number of infants on lap (default: 0)
        seat_class: Seat class (economy, premium_economy, business, first) (default: economy)

    Returns:
        Flight search results in a formatted string
    """
    if ctx:
        ctx.info(f"Searching flights from {from_airport} to {to_airport}")
    
    # Validate inputs
    try:
        # Validate dates
        departure_datetime = datetime.strptime(departure_date, "%Y-%m-%d")
        return_datetime = None
        if return_date:
            return_datetime = datetime.strptime(return_date, "%Y-%m-%d")
            if return_datetime < departure_datetime:
                return "Error: Return date cannot be before departure date."
            
        # Validate airport codes
        if len(from_airport) != 3 or len(to_airport) != 3:
            return "Error: Airport codes must be 3-letter IATA codes."
        
        # Check if airports exist in our database
        from_airport = from_airport.upper()
        to_airport = to_airport.upper()
        
        if from_airport not in airports:
            return f"Error: Departure airport code '{from_airport}' not found in our database."
        if to_airport not in airports:
            return f"Error: Arrival airport code '{to_airport}' not found in our database."
            
        # Validate passenger numbers
        if adults < 1:
            return "Error: At least one adult passenger is required."
        if any(num < 0 for num in [adults, children, infants_in_seat, infants_on_lap]):
            return "Error: Passenger numbers cannot be negative."
            
        # Validate seat class
        valid_classes = DEFAULT_CONFIG["seat_classes"]
        if seat_class.lower() not in valid_classes:
            return f"Error: Seat class must be one of {', '.join(valid_classes)}."
    
    except ValueError:
        return "Error: Invalid date format. Please use YYYY-MM-DD format."

    # Import fast_flights here to avoid startup issues
    try:
        if ctx:
            ctx.info("Importing fast_flights module")
        from fast_flights import FlightData, Passengers, Result, get_flights
    except ImportError as e:
        error_msg = f"Error importing fast_flights: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        return f"Error: Unable to import fast_flights library. Please make sure it's installed correctly. Error details: {error_msg}"
    
    # Create flight data
    try:
        if ctx:
            ctx.info("Creating flight data objects")
        
        flight_data = [FlightData(date=departure_date, from_airport=from_airport, to_airport=to_airport)]
        
        # Add return flight if return_date is provided
        if return_date:
            flight_data.append(FlightData(date=return_date, from_airport=to_airport, to_airport=from_airport))
        
        # Set trip type based on whether a return date was provided
        trip_type = "round-trip" if return_date else "one-way"
        
        # Create passengers object
        passengers = Passengers(
            adults=adults,
            children=children,
            infants_in_seat=infants_in_seat,
            infants_on_lap=infants_on_lap
        )
        
        if ctx:
            ctx.info("Calling get_flights API")
            ctx.report_progress(0.5, 1.0)
            
        # Get flight results
        result: Result = get_flights(
            flight_data=flight_data,
            trip=trip_type,
            seat=seat_class,
            passengers=passengers,
            fetch_mode="fallback",  # Use fallback mode for more reliable results
        )
        
        if ctx:
            ctx.info("Processing flight results")
            ctx.report_progress(1.0, 1.0)
            
        # Format results
        return format_flight_results(result, trip_type, DEFAULT_CONFIG["max_results"])
        
    except Exception as e:
        error_msg = f"Error searching for flights: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        return error_msg

def format_flight_results(result, trip_type: str, max_results: int) -> str:
    """Format flight results into a readable string."""
    if not result or not hasattr(result, 'flights') or not result.flights:
        return "No flights found matching your criteria."
    
    output = []
    output.append(f"Found {len(result.flights)} flight options.")
    
    if hasattr(result, 'current_price'):
        output.append(f"Price assessment: {result.current_price}")
    
    output.append("\n")
    
    for i, flight in enumerate(result.flights[:max_results], 1):  # Limit to max results
        best_tag = " [BEST OPTION]" if hasattr(flight, 'is_best') and flight.is_best else ""
        output.append(f"Option {i}{best_tag}:")
        
        if hasattr(flight, 'name'):
            output.append(f"  Airline: {flight.name}")
        
        if hasattr(flight, 'departure'):
            output.append(f"  Departure: {flight.departure}")
        
        if hasattr(flight, 'arrival'):
            output.append(f"  Arrival: {flight.arrival}")
        
        if hasattr(flight, 'arrival_time_ahead') and flight.arrival_time_ahead:
            output.append(f"  Arrives: {flight.arrival_time_ahead}")
            
        if hasattr(flight, 'duration'):
            output.append(f"  Duration: {flight.duration}")
        
        if hasattr(flight, 'stops'):
            output.append(f"  Stops: {flight.stops}")
        
        if hasattr(flight, 'delay') and flight.delay:
            output.append(f"  Delay: {flight.delay}")
            
        if hasattr(flight, 'price'):
            output.append(f"  Price: {flight.price}")
        
        output.append("")
    
    if len(result.flights) > max_results:
        output.append(f"... and {len(result.flights) - max_results} more flight options available.")
    
    if trip_type == "round-trip":
        output.append("Note: Price shown is for the entire round trip.")
    
    return "\n".join(output)

@mcp.tool()
def airport_search(query: str, ctx: Context = None) -> str:
    """
    Search for airport codes by name or city.

    Args:
        query: The search term (city name, airport name, or partial code)

    Returns:
        List of matching airports with their codes
    """
    if ctx:
        ctx.info(f"Searching for airports matching: {query}")
    
    if not query or len(query.strip()) < 2:
        return "Please provide at least 2 characters to search for airports."
    
    query = query.strip().upper()
    matches = []
    
    # Search by airport code or name
    for code, name in airports.items():
        if query in code or query.upper() in name.upper():
            matches.append(f"{name} ({code})")
    
    if not matches:
        return f"No airports found matching '{query}'."
    
    # Sort matches and format the output
    matches.sort()
    result = [f"Found {len(matches)} airports matching '{query}':"]
    result.extend(matches[:20])  # Limit to 20 results
    
    if len(matches) > 20:
        result.append(f"...and {len(matches) - 20} more. Please refine your search to see more specific results.")
        
    return "\n".join(result)

@mcp.tool()
def get_travel_dates(days_from_now: Optional[int] = None, trip_length: Optional[int] = None) -> str:
    """
    Get suggested travel dates based on days from now and trip length.

    Args:
        days_from_now: Number of days from today for departure 
                      (default: configured default_advance_days)
        trip_length: Length of the trip in days
                     (default: configured default_trip_days)

    Returns:
        Suggested travel dates in YYYY-MM-DD format
    """
    # Use configured defaults if not provided
    if days_from_now is None:
        days_from_now = DEFAULT_CONFIG["default_advance_days"]
    if trip_length is None:
        trip_length = DEFAULT_CONFIG["default_trip_days"]
    
    if days_from_now < 1:
        return "Error: Days from now must be at least 1."
    if trip_length < 1:
        return "Error: Trip length must be at least 1 day."
    
    today = datetime.now()
    departure_date = today + timedelta(days=days_from_now)
    return_date = departure_date + timedelta(days=trip_length)
    
    departure_str = departure_date.strftime("%Y-%m-%d")
    return_str = return_date.strftime("%Y-%m-%d")
    
    return f"Departure date: {departure_str}\nReturn date: {return_str}"

@mcp.tool()
async def update_airports_database(ctx: Context = None) -> str:
    """
    Update the airports database from the configured CSV source.

    Returns:
        Status message with the number of airports loaded
    """
    if ctx:
        ctx.info("Starting airport database update")
        ctx.report_progress(0.1, 1.0)
    
    try:
        if ctx:
            ctx.info(f"Fetching airports from {CSV_URL}")
            ctx.report_progress(0.3, 1.0)
        
        global airports
        fresh_airports = await fetch_airports_csv()
        
        if not fresh_airports:
            return "Error: Failed to fetch airports or no valid airports found"
        
        # Update the global airports dictionary
        airports = fresh_airports
        
        if ctx:
            ctx.report_progress(1.0, 1.0)
        
        return f"Successfully updated airports database with {len(airports)} airports"
    
    except Exception as e:
        error_msg = f"Error updating airports: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        return error_msg

@mcp.resource("airports://all")
def get_all_airports() -> str:
    """Get a list of all available airports."""
    result = [f"Available Airports ({len(airports)} total):"]
    for code, name in sorted(airports.items())[:100]:  # Limit to first 100 to avoid overwhelming
        result.append(f"{code}: {name}")
    
    if len(airports) > 100:
        result.append(f"... and {len(airports) - 100} more airports. Use airport_search tool to find specific airports.")
    
    return "\n".join(result)

@mcp.resource("airports://{code}")
def get_airport_info(code: str) -> str:
    """Get information about a specific airport by its code."""
    code = code.upper()
    if code in airports:
        return f"{code}: {airports[code]}"
    return f"Airport code '{code}' not found"

@mcp.prompt()
def plan_trip(destination: str) -> str:
    """Create a prompt for trip planning to a specific destination."""
    return f"""I'd like to plan a trip to {destination}. Can you help me with the following:

1. What's the best time of year to visit {destination}?
2. How long should I plan to stay to see the major attractions?
3. What are the must-see places in {destination}?
4. What's the typical cost range for accommodations?
5. Are there any travel advisories or cultural considerations I should be aware of?

After you answer these questions, could you help me find flights to {destination} using the flight search tool?"""

@mcp.prompt()
def compare_destinations(destination1: str, destination2: str) -> str:
    """Create a prompt for comparing two travel destinations."""
    return f"""I'm trying to decide between traveling to {destination1} and {destination2}. 
Can you help me compare these destinations on the following factors:

1. Weather and best time to visit each location
2. Cost of travel and accommodations
3. Popular attractions and activities
4. Food and cultural experiences
5. Safety and travel considerations

Based on these factors, which would you recommend and why?
After your recommendation, could you show me flight options for both destinations?"""

# Initialize airports on startup - this is crucial
async def initialize_airports():
    """Initialize airport data at startup."""
    global airports
    
    # First try to load from cache
    cache = load_airports_cache()
    if cache:
        airports = cache
    
    # If cache is empty, fetch from CSV
    if not airports:
        fresh_airports = await fetch_airports_csv()
        if fresh_airports:
            airports = fresh_airports
    
    print(f"Initialized with {len(airports)} airports", file=sys.stderr)

# Run the server
if __name__ == "__main__":
    print("Initializing airports database...", file=sys.stderr)
    # Run the initialization in an event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialize_airports())
    
    print("Starting server - waiting for connections...", file=sys.stderr)
    try:
        # This will keep the server running until interrupted
        mcp.run()
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)