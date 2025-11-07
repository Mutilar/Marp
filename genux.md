# GenUX - WinForms AI Data Modeling Assistant

This document outlines the workflow and decision matrix for an AI assistant that helps with WinForms data modeling and analytics.

## Overview

The AI assistant handles two primary scenarios:
1. **Model/Form Creation**: Returns ModelSpec and FormSpec JSON objects
2. **Data Analysis**: Returns QueryPlan JSON object for querying existing data

## Workflow Decision Matrix

<!-- mermaid-output: assets/diagrams/genux-workflow.png -->
```mermaid
flowchart LR
    A[User Request] --> B{Request Type}
    
    B -->|Create or Update| C[Generate ModelSpec & FormSpec JSONs]
    B -->|Query or Analyze| D[Generate QueryPlan JSON]
    
    %% Schema Details - Main Nodes
    C --> G[ModelSpec Schema]
    C --> K[FormSpec Schema]
    D --> H[QueryPlan Schema]
    
    %% ModelSpec Components
    G --> G1["Name:<br/>Model identifier"]
    G --> G2["Fields:<br/>Field definitions"]
    G --> G3["Lookups:<br/>Enum/FK values"]
    
    G2 --> G2A["Field Name:<br/>Identifier"]
    G2 --> G2B["Field Type:<br/>string, text, int, decimal,<br/>bool, date, datetime, enum,<br/>image, email, phone, url, lookup"]
    
    %% FormSpec Components  
    K --> K1["ModelName:<br/>Reference to ModelSpec"]
    K --> K2["Fields:<br/>UI field config"]
    
    K2 --> K2A["Field:<br/>ModelSpec field name"]
    K2 --> K2B["Label:<br/>Display text (optional)"]
    
    %% QueryPlan Components
    H --> H1["TargetModel:<br/>Model to query"]
    H --> H2["Select:<br/>Fields & aggregations"]
    H --> H3["Filters:<br/>Query conditions"]
    H --> H4["OrderBy:<br/>Sort specification"]
    H --> H5["Limit & Intent:<br/>Result size & description"]
    
    %% Select Details
    H2 --> H2A["Field:<br/>Field name"]
    H2 --> H2B["Aggregate:<br/>count, sum, avg, min, max"]
    H2 --> H2C["Alias:<br/>Result column name"]
    
    %% Filter Details
    H3 --> H3A["Field:<br/>Filter target"]
    H3 --> H3B["Operator:<br/>equals, not_equals, contains,<br/>starts_with, ends_with,<br/>gt, gte, lt, lte, between,<br/>in, not_in"]
    H3 --> H3C["Values:<br/>Value, Values[], Min, Max"]
    
    %% Database Operations - Connected from detail components
    G1 --> I[("CREATE/UPDATE<br/>New App State")]
    G2A --> I
    G2B --> I
    G3 --> I
    K1 --> I
    K2A --> I
    K2B --> I
    
    H1 --> J[("READ<br/>Query Data")]
    H2A --> J
    H2B --> J
    H2C --> J
    H3A --> J
    H3B --> J
    H3C --> J
    H4 --> J
    H5 --> J
    
    %% Styling
    classDef userInput fill:#e1f5fe
    classDef decision fill:#fff3e0
    classDef process fill:#f3e5f5
    classDef output fill:#e8f5e8
    classDef schema fill:#fce4ec
    classDef database fill:#e3f2fd
    classDef detail fill:#f1f8e9
    
    class A userInput
    class B decision
    class C,D process
    class G,H,K schema
    class G1,G2,G3,K1,K2,H1,H2,H3,H4,H5 detail
    class G2A,G2B,K2A,K2B,H2A,H2B,H2C,H3A,H3B,H3C detail
    class I,J database
```

## JSON Schema Specifications

### ModelSpec Schema - Detailed Structure

The ModelSpec defines the data model structure with fields, types, and lookup relationships.

```json
{
  "Name": "string",              // Model name (PascalCase recommended)
  "Fields": [                    // Array of field definitions
    {
      "Name": "string",          // Field name (PascalCase recommended)
      "Type": "fieldType"        // One of the supported field types below
    }
  ],
  "Lookups": [                   // Optional: Define enum values and foreign keys
    {
      "Name": "string",          // Name matching an enum or lookup field
      "Values": ["string"]       // Array of possible values
    }
  ]
}
```

**Field Type Options:**
- **Text Types**: `string` (short), `text` (long), `email`, `phone`, `url`
- **Numeric Types**: `int`, `decimal`
- **Date/Time**: `date`, `datetime`
- **Boolean**: `bool`
- **Special Types**: `enum` (predefined values), `lookup` (foreign key), `image` (file path/URL)

### FormSpec Schema - Detailed Structure

The FormSpec defines the UI form layout and field presentation.

```json
{
  "ModelName": "string",         // Must match the ModelSpec Name exactly
  "Fields": [                    // Array of form field configurations
    {
      "Field": "string",         // Must match a field name from ModelSpec
      "Label": "string"          // Optional: Custom display label for the field
    }
  ]
}
```

**Form Field Rules:**
- All ModelSpec fields should have corresponding FormSpec entries
- Fields without explicit labels use the field name as display text
- Field order in FormSpec determines UI layout order

### QueryPlan Schema - Detailed Structure

The QueryPlan defines data queries with selection, filtering, and sorting criteria.

```json
{
  "TargetModel": "string",       // Model name to query (must exist)
  "Select": [                    // Fields to retrieve and optional aggregations
    {
      "Field": "string",         // Field name from the target model
      "Aggregate": "operation",  // Optional: count|sum|avg|min|max
      "Alias": "string"          // Optional: Custom name for the result column
    }
  ],
  "Filters": [                   // Optional: Conditions to filter data
    {
      "Field": "string",         // Field name to filter on
      "Operator": "operation",   // Comparison operator (see reference below)
      "Value": "any",            // Single value for most operators
      "Values": ["any"],         // Array for 'in' and 'not_in' operators
      "Min": "number",           // Lower bound for 'between' operator
      "Max": "number"            // Upper bound for 'between' operator
    }
  ],
  "OrderBy": [                   // Optional: Sort specifications
    {
      "Field": "string",         // Field name to sort by
      "Direction": "asc|desc"    // Sort direction
    }
  ],
  "Limit": "number",             // Optional: Maximum number of results
  "Intent": "string"             // Optional: Human-readable query description
}
```

**Query Composition Rules:**
- At least one Select field is required
- Multiple filters are combined with AND logic
- OrderBy fields should typically be included in Select
- Aggregations require grouping by non-aggregated fields
```

## Field Types Reference

| Type | Description | Use Case |
|------|-------------|----------|
| `string` | Short text | Names, titles, codes |
| `text` | Long text | Descriptions, comments |
| `int` | Integer | Counts, IDs |
| `decimal` | Decimal number | Prices, measurements |
| `bool` | Boolean | Yes/No flags |
| `date` | Date only | Birth dates, deadlines |
| `datetime` | Date and time | Timestamps |
| `enum` | Predefined values | Status, categories |
| `image` | Image path/URL | Photos, icons |
| `email` | Email address | Contact information |
| `phone` | Phone number | Contact information |
| `url` | Web URL | Links, references |
| `lookup` | Foreign key | References to other models |

## Query Operators Reference

| Operator | Description | Value Type |
|----------|-------------|------------|
| `equals` | Exact match | Single value |
| `not_equals` | Not equal | Single value |
| `contains` | Contains substring | String |
| `starts_with` | Starts with | String |
| `ends_with` | Ends with | String |
| `gt` | Greater than | Number/Date |
| `gte` | Greater than or equal | Number/Date |
| `lt` | Less than | Number/Date |
| `lte` | Less than or equal | Number/Date |
| `between` | Between values | Min/Max |
| `in` | In list | Values array |
| `not_in` | Not in list | Values array |

## Usage Examples

### Example 1: Creating a Customer Model
**User Request**: "Create a customer model with name, email, phone, and status"

**Expected Output**:
```json
{"Name":"Customer","Fields":[{"Name":"Name","Type":"string"},{"Name":"Email","Type":"email"},{"Name":"Phone","Type":"phone"},{"Name":"Status","Type":"enum"}],"Lookups":[{"Name":"Status","Values":["Active","Inactive","Pending"]}]}
{"ModelName":"Customer","Fields":[{"Field":"Name","Label":"Customer Name"},{"Field":"Email"},{"Field":"Phone"},{"Field":"Status"}]}
```

### Example 2: Creating an Order Model with Relationships
**User Request**: "Create an order model with order number, customer lookup, order date, total amount, and items"

**Expected Output**:
```json
{"Name":"Order","Fields":[{"Name":"OrderNumber","Type":"string"},{"Name":"CustomerId","Type":"lookup"},{"Name":"OrderDate","Type":"datetime"},{"Name":"TotalAmount","Type":"decimal"},{"Name":"Items","Type":"text"}],"Lookups":[{"Name":"CustomerId","Values":["Customer"]}]}
{"ModelName":"Order","Fields":[{"Field":"OrderNumber","Label":"Order #"},{"Field":"CustomerId","Label":"Customer"},{"Field":"OrderDate","Label":"Order Date"},{"Field":"TotalAmount","Label":"Total ($)"},{"Field":"Items","Label":"Order Items"}]}
```

### Example 3: Simple Data Query
**User Request**: "Show me all active customers ordered by name"

**Expected Output**:
```json
{"TargetModel":"Customer","Select":[{"Field":"Name"},{"Field":"Email"},{"Field":"Phone"}],"Filters":[{"Field":"Status","Operator":"equals","Value":"Active"}],"OrderBy":[{"Field":"Name","Direction":"asc"}],"Intent":"List all active customers"}
```

### Example 4: Complex Aggregation Query
**User Request**: "Show total sales by customer for orders over $100 this year"

**Expected Output**:
```json
{"TargetModel":"Order","Select":[{"Field":"CustomerId"},{"Field":"TotalAmount","Aggregate":"sum","Alias":"TotalSales"}],"Filters":[{"Field":"TotalAmount","Operator":"gt","Value":100},{"Field":"OrderDate","Operator":"gte","Value":"2025-01-01"}],"OrderBy":[{"Field":"TotalSales","Direction":"desc"}],"Intent":"Customer sales totals for orders over $100 in 2025"}
```

### Example 5: Range and List Filtering
**User Request**: "Find customers with names starting with 'A' or 'B' who joined between January and March"

**Expected Output**:
```json
{"TargetModel":"Customer","Select":[{"Field":"Name"},{"Field":"Email"},{"Field":"JoinDate"}],"Filters":[{"Field":"Name","Operator":"in","Values":["A%","B%"]},{"Field":"JoinDate","Operator":"between","Min":"2025-01-01","Max":"2025-03-31"}],"OrderBy":[{"Field":"JoinDate","Direction":"desc"}],"Intent":"Customers with A-B names who joined Q1 2025"}

## Automation

Use the provided `render-mermaid.ps1` script to automatically render the Mermaid diagram:

```powershell
.\scripts\render-mermaid.ps1 -InputPath "genux.md" -DiagramIndex 0
```

Or render all diagrams in all README files:

```powershell
.\scripts\render-mermaid.ps1 -AllReadmes
```