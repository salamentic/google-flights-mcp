# Flight Planner MCP Server

A Model Context Protocol server that creates travel agent-level flight plans using the fast-flights API.

## Features

- Search for one-way and round-trip flights
- Create comprehensive travel plans based on trip parameters
- Get airport code information
- Use templates for common travel queries

## Installation

1. Make sure you have Python 3.10 or higher installed
2. Install the required packages:

```bash
pip install mcp fast-flights
```

## Usage

### Running the Server

You can run the server directly:

```bash
python flight_planner_server.py
```

### Integrating with Claude Desktop

1. Install [Claude Desktop](https://claude.ai/download)
2. Create or edit your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

3. Add the flight-planner server configuration:

```json
{
  "mcpServers": {
    "flight-planner": {
      "command": "python",
      "args": [
        "/PATH/TO/flight_planner_server.py"
      ],
      "env": {
        "PYTHONPATH": "/PATH/TO/PROJECT"
      }
    }
  }
}
```

4. Replace `/PATH/TO/` with the actual path to your server file
5. Restart Claude Desktop

### Using the MCP Inspector

For testing and development, you can use the MCP Inspector:

```bash
# Install the inspector
npm install -g @modelcontextprotocol/inspector

# Run the inspector with your server
npx @modelcontextprotocol/inspector python flight_planner_server.py
```

## Available Tools

- `search_one_way_flights`: Search for one-way flights between airports
- `search_round_trip_flights`: Search for round-trip flights between airports  
- `create_travel_plan`: Generate a comprehensive travel plan

## Available Resources

- `airport_codes://{query}`: Get airport code information based on a search query

## Available Prompts

- `flight_search_prompt`: Template for searching flights
- `travel_plan_prompt`: Template for creating a comprehensive travel plan

## Example Queries for Claude

Once integrated with Claude Desktop, you can ask things like:

- "What flights are available from NYC to SFO on 2025-04-15?"
- "Can you create a travel plan for my business trip from LAX to TPE from 2025-05-01 to 2025-05-08?"
- "Help me find airport codes for Tokyo."
- "What's the best time to book flights from Boston to London for a summer vacation?"

## License

MIT
