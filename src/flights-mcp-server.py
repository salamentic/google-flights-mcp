# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

from mcp.server.fastmcp import FastMCP, Context
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

try:
    from fast_flights import FlightData, Passengers, Result, get_flights
except ImportError:
    print("fast-flights package not installed. Install with: pip install fast-flights")
    
# Create an MCP server
mcp = FastMCP("FlightPlanner")

class FlightPlanningTool:
    """Helper class to deal with the flight planning tools"""
    
    @staticmethod
    def format_flight_result(result: Result) -> str:
        """Format a flight result object into a readable string"""
        if not result or not result.flights:
            return "No flights found."
            
        output = []
        output.append(f"Current price trend: {result.current_price}")
        
        for i, flight in enumerate(result.flights[:10]):  # Limit to 10 flights for readability
            output.append(f"\nFlight {i+1}:")
            output.append(f"  {'✓ BEST OPTION' if flight.is_best else ''}")
            output.append(f"  Name: {flight.name}")
            output.append(f"  Departure: {flight.departure}")
            output.append(f"  Arrival: {flight.arrival}")
            output.append(f"  {'Arrives ahead: ' + str(flight.arrival_time_ahead) if flight.arrival_time_ahead else ''}")
            output.append(f"  Duration: {flight.duration}")
            output.append(f"  Stops: {flight.stops}")
            output.append(f"  Price: {flight.price}")
            
            if hasattr(flight, 'delay') and flight.delay:
                output.append(f"  Delay: {flight.delay}")
                
        return "\n".join(output)

@mcp.tool()
def search_one_way_flights(
    from_airport: str, 
    to_airport: str, 
    departure_date: str, 
    adults: int = 1, 
    children: int = 0, 
    infants_in_seat: int = 0, 
    infants_on_lap: int = 0,
    seat_class: str = "economy"
) -> str:
    """
    Search for one-way flights using the fast-flights API.
    
    Args:
        from_airport: Departure airport code (e.g., "NYC", "LAX", "TPE")
        to_airport: Arrival airport code (e.g., "MYJ", "SFO", "LHR")
        departure_date: Departure date in YYYY-MM-DD format
        adults: Number of adult passengers (default: 1)
        children: Number of children passengers (default: 0)
        infants_in_seat: Number of infants in seat (default: 0)
        infants_on_lap: Number of infants on lap (default: 0)
        seat_class: Class of seat, one of "economy", "premium-economy", "business", "first" (default: "economy")
    
    Returns:
        String with formatted flight information
    """
    try:
        # Validate date format
        datetime.strptime(departure_date, "%Y-%m-%d")
        
        # Validate seat class
        valid_seat_classes = ["economy", "premium-economy", "business", "first"]
        if seat_class not in valid_seat_classes:
            return f"Invalid seat class. Must be one of: {', '.join(valid_seat_classes)}"
            
        # Create flight data object
        flight_data = [
            FlightData(date=departure_date, from_airport=from_airport, to_airport=to_airport)
        ]
        
        # Create passengers object
        passengers = Passengers(
            adults=adults,
            children=children,
            infants_in_seat=infants_in_seat,
            infants_on_lap=infants_on_lap
        )
        
        # Get flights
        result = get_flights(
            flight_data=flight_data,
            trip="one-way",
            seat=seat_class,
            passengers=passengers,
            fetch_mode="fallback"
        )
        
        # Format the result
        return FlightPlanningTool.format_flight_result(result)
        
    except Exception as e:
        return f"Error searching for flights: {str(e)}"

@mcp.tool()
def search_round_trip_flights(
    from_airport: str, 
    to_airport: str, 
    departure_date: str,
    return_date: str,
    adults: int = 1, 
    children: int = 0, 
    infants_in_seat: int = 0, 
    infants_on_lap: int = 0,
    seat_class: str = "economy"
) -> str:
    """
    Search for round-trip flights using the fast-flights API.
    
    Args:
        from_airport: Departure airport code (e.g., "NYC", "LAX", "TPE")
        to_airport: Arrival airport code (e.g., "MYJ", "SFO", "LHR")
        departure_date: Outbound departure date in YYYY-MM-DD format
        return_date: Return departure date in YYYY-MM-DD format
        adults: Number of adult passengers (default: 1)
        children: Number of children passengers (default: 0)
        infants_in_seat: Number of infants in seat (default: 0)
        infants_on_lap: Number of infants on lap (default: 0)
        seat_class: Class of seat, one of "economy", "premium-economy", "business", "first" (default: "economy")
    
    Returns:
        String with formatted flight information
    """
    try:
        # Validate date format
        datetime.strptime(departure_date, "%Y-%m-%d")
        datetime.strptime(return_date, "%Y-%m-%d")
        
        # Validate return date is after departure date
        if departure_date >= return_date:
            return "Return date must be after departure date."
        
        # Validate seat class
        valid_seat_classes = ["economy", "premium-economy", "business", "first"]
        if seat_class not in valid_seat_classes:
            return f"Invalid seat class. Must be one of: {', '.join(valid_seat_classes)}"
            
        # Create flight data objects for both directions
        flight_data = [
            FlightData(date=departure_date, from_airport=from_airport, to_airport=to_airport),
            FlightData(date=return_date, from_airport=to_airport, to_airport=from_airport)
        ]
        
        # Create passengers object
        passengers = Passengers(
            adults=adults,
            children=children,
            infants_in_seat=infants_in_seat,
            infants_on_lap=infants_on_lap
        )
        
        # Get flights
        result = get_flights(
            flight_data=flight_data,
            trip="round-trip",
            seat=seat_class,
            passengers=passengers,
            fetch_mode="fallback"
        )
        
        # Format the result
        return FlightPlanningTool.format_flight_result(result)
        
    except Exception as e:
        return f"Error searching for flights: {str(e)}"

@mcp.tool()
def create_travel_plan(
    from_airport: str,
    to_airport: str,
    departure_date: str,
    return_date: Optional[str] = None,
    trip_purpose: str = "vacation",
    budget_level: str = "moderate",
    interests: str = "",
    ctx: Context = None
) -> str:
    """
    Create a comprehensive travel plan including flight options and recommendations.
    
    Args:
        from_airport: Departure airport code (e.g., "NYC", "LAX", "TPE")
        to_airport: Arrival airport code (e.g., "MYJ", "SFO", "LHR")
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format (Optional for one-way trips)
        trip_purpose: Purpose of the trip (e.g., "vacation", "business", "family visit")
        budget_level: Budget level, one of "budget", "moderate", "luxury"
        interests: Comma-separated list of interests for activity recommendations
        
    Returns:
        A comprehensive travel plan with flight options and recommendations
    """
    try:
        is_round_trip = return_date is not None
        trip_type = "round-trip" if is_round_trip else "one-way"
        seat_class_recommendation = "economy"
        
        # Adjust seat class based on trip purpose and budget
        if trip_purpose.lower() == "business" and budget_level.lower() == "luxury":
            seat_class_recommendation = "business"
        elif budget_level.lower() == "luxury":
            seat_class_recommendation = "premium-economy"
            
        # Progress tracking
        if ctx:
            ctx.info("Starting travel plan creation...")
            ctx.report_progress(0, 2)
            
        # Get flight options
        if is_round_trip:
            if ctx:
                ctx.info("Searching for round-trip flights...")
            flight_result = search_round_trip_flights(
                from_airport=from_airport,
                to_airport=to_airport,
                departure_date=departure_date,
                return_date=return_date,
                seat_class=seat_class_recommendation
            )
        else:
            if ctx:
                ctx.info("Searching for one-way flights...")
            flight_result = search_one_way_flights(
                from_airport=from_airport,
                to_airport=to_airport,
                departure_date=departure_date,
                seat_class=seat_class_recommendation
            )
            
        if ctx:
            ctx.report_progress(1, 2)
            ctx.info("Creating travel recommendations...")
            
        # Format the travel plan
        plan_parts = [
            f"# Travel Plan: {from_airport} to {to_airport}",
            f"\n## Trip Details",
            f"- Trip Type: {trip_type}",
            f"- Departure: {departure_date}",
        ]
        
        if is_round_trip:
            plan_parts.append(f"- Return: {return_date}")
            
        plan_parts.extend([
            f"- Purpose: {trip_purpose}",
            f"- Budget Level: {budget_level}",
            f"\n## Flight Options",
            flight_result,
            f"\n## Travel Recommendations",
            f"Based on your {trip_purpose} trip and {budget_level} budget, here are some recommendations:",
        ])
        
        # Add custom recommendations based on trip parameters
        if budget_level.lower() == "budget":
            plan_parts.append("- Consider booking economy flights at least 6 weeks in advance")
            plan_parts.append("- Look for accommodations with kitchenettes to save on meal costs")
            plan_parts.append("- Research free activities and attractions at your destination")
        elif budget_level.lower() == "moderate":
            plan_parts.append("- Premium economy seats offer better comfort for the price")
            plan_parts.append("- Consider mid-range hotels or vacation rentals")
            plan_parts.append("- Mix of paid attractions and free experiences recommended")
        else:  # luxury
            plan_parts.append("- Business or first-class seats recommended for maximum comfort")
            plan_parts.append("- Luxury hotels or private villas will enhance your experience")
            plan_parts.append("- Consider private tours and exclusive experiences")
            
        # Add interest-based recommendations if provided
        if interests:
            plan_parts.append(f"\n## Interest-Based Recommendations")
            interests_list = [i.strip() for i in interests.split(",")]
            for interest in interests_list:
                plan_parts.append(f"- For {interest}: Customized activities will be recommended by your AI assistant")
                
        if ctx:
            ctx.report_progress(2, 2)
            ctx.info("Travel plan creation complete!")
                
        return "\n".join(plan_parts)
        
    except Exception as e:
        return f"Error creating travel plan: {str(e)}"

@mcp.resource("airport_codes://{query}")
def get_airport_codes(query: str) -> str:
    """
    Get airport codes that match a search query.
    This is a simplified implementation that returns common airport codes.
    
    Args:
        query: A search string (city name, airport name, or partial code)
        
    Returns:
        A list of matching airport codes with descriptions
    """
    # Simplified database of common airports
    airports = {
        "nyc": "NYC - New York City (all airports)",
        "jfk": "JFK - John F. Kennedy International Airport, New York",
        "lga": "LGA - LaGuardia Airport, New York",
        "ewr": "EWR - Newark Liberty International Airport, New Jersey",
        "lax": "LAX - Los Angeles International Airport, California",
        "sfo": "SFO - San Francisco International Airport, California",
        "ord": "ORD - O'Hare International Airport, Chicago",
        "dfw": "DFW - Dallas/Fort Worth International Airport, Texas",
        "mia": "MIA - Miami International Airport, Florida",
        "sea": "SEA - Seattle-Tacoma International Airport, Washington",
        "las": "LAS - Harry Reid International Airport, Las Vegas",
        "atl": "ATL - Hartsfield-Jackson Atlanta International Airport, Georgia",
        "den": "DEN - Denver International Airport, Colorado",
        "bos": "BOS - Boston Logan International Airport, Massachusetts",
        "lhr": "LHR - London Heathrow Airport, United Kingdom",
        "cdg": "CDG - Charles de Gaulle Airport, Paris, France",
        "fra": "FRA - Frankfurt Airport, Germany",
        "ams": "AMS - Amsterdam Airport Schiphol, Netherlands",
        "hnd": "HND - Tokyo Haneda Airport, Japan",
        "nrt": "NRT - Narita International Airport, Tokyo, Japan",
        "pek": "PEK - Beijing Capital International Airport, China",
        "pvg": "PVG - Shanghai Pudong International Airport, China",
        "syd": "SYD - Sydney Airport, Australia",
        "sin": "SIN - Singapore Changi Airport, Singapore",
        "dxb": "DXB - Dubai International Airport, United Arab Emirates",
        "tpe": "TPE - Taiwan Taoyuan International Airport, Taiwan",
        "myj": "MYJ - Matsuyama Airport, Japan"
    }
    
    query = query.lower()
    
    # Search the airports dictionary
    results = []
    for code, description in airports.items():
        if query in code.lower() or query in description.lower():
            results.append(description)
            
    if not results:
        return "No matching airports found. Try a different search term."
        
    return "\n".join(results)

@mcp.prompt()
def flight_search_prompt(from_airport: str, to_airport: str, date: str) -> str:
    """
    Create a prompt for searching flights between two airports on a specific date.
    
    Args:
        from_airport: Departure airport code
        to_airport: Arrival airport code
        date: Travel date in YYYY-MM-DD format
        
    Returns:
        A formatted prompt for the AI assistant
    """
    return f"""Please search for flights from {from_airport} to {to_airport} on {date}.
    
I'd like to see options for departure times, prices, and any recommendations you have about the best value flights."""

@mcp.prompt()
def travel_plan_prompt(
    from_airport: str, 
    to_airport: str, 
    dates: str, 
    purpose: str, 
    interests: str
) -> str:
    """
    Create a prompt for generating a comprehensive travel plan.
    
    Args:
        from_airport: Departure airport code
        to_airport: Arrival airport code
        dates: Travel dates range in format "YYYY-MM-DD to YYYY-MM-DD"
        purpose: Purpose of the trip (e.g., vacation, business)
        interests: Comma-separated list of interests
        
    Returns:
        A formatted prompt for the AI assistant
    """
    return f"""Please create a comprehensive travel plan for my trip from {from_airport} to {to_airport} on {dates}.

Trip Purpose: {purpose}
Interests: {interests}

I'd like information about:
1. Flight options and recommendations
2. Accommodation suggestions
3. Activities and attractions based on my interests
4. Local transportation options
5. Budget considerations
6. Any travel tips specific to my destination

Thank you!"""

# Run the server with stdio transport
if __name__ == "__main__":
    try:
        # Try importing fast_flights to verify it's installed
        import fast_flights
        print("Starting Flight Planner MCP Server...")
        mcp.run(transport="stdio")
    except ImportError:
        print("""
ERROR: The fast-flights package is not installed.
Please install it with: pip install fast-flights
        """)
