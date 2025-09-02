# Text-to-SQL System Architecture

## 1. Executive Summary

The Text-to-SQL system enables network operators to query infrastructure databases using natural language, eliminating the need for SQL expertise. It translates questions like "show me all routers with high CPU usage" into safe, optimized SQL queries while maintaining strict security controls.

**Core Value:** Transform complex SQL queries into simple English questions for network infrastructure management.

## 2. Problem & Solution

### 2.1 The Challenge
Network infrastructure databases contain dozens of interconnected tables with complex relationships. Network operators need quick data access but lack SQL expertise, making manual query writing error-prone and time-consuming.

### 2.2 Our Approach
A six-stage pipeline that safely converts natural language to SQL:

```mermaid
graph LR
    A[Natural Language] --> B[Schema Analysis]
    B --> C[Query Planning]
    C --> D[SQL Generation]
    D --> E[Safety Validation]
    E --> F[Execution]
    F --> G[Interpretation]
    
    style A fill:#e1f5fe
    style D fill:#f3e5f5
    style E fill:#ffebee
    style F fill:#e8f5e9
```

### 2.3 Target Domain
Built for network infrastructure management:
- **Devices**: Routers, switches, load balancers, firewalls
- **Topology**: VLANs, BGP peers, interface connections
- **Metrics**: Bandwidth, latency, packet loss, CPU usage
- **Security**: ACLs, certificates, compliance data

## 3. When to Use This System

### 3.1 Perfect Fit Scenarios
- **Analytical queries**: Aggregations (SUM, COUNT, AVG, GROUP BY)
- **10-50 interconnected tables** with clear relationships
- **Ad-hoc exploratory queries** without predefined reports
- **Direct database access** without API restrictions
- **Existing SQL infrastructure** (PostgreSQL, MySQL, Oracle)

### 3.2 Example Use Cases
**Analytics:**
- "What's the average CPU utilization by datacenter?"
- "Show monthly bandwidth growth trends"
- "Calculate 95th percentile latency this week"

**Operations:**
- "Find all routers with outdated firmware"
- "Show interfaces with >80% utilization"
- "List devices that failed in the last 24 hours"

### 3.3 Optimization Strategies
For schemas with many tables:
- **Schema filtering**: Only pass relevant tables to LLM
- **Semantic layer**: Create views to simplify complex joins
- **Progressive complexity**: Start simple, build up as needed

## 4. Architecture

### 4.1 System Overview

```mermaid
graph TD
    USER["User Query"] --> SYSTEM
    
    subgraph SYSTEM["Text-to-SQL Engine"]
        direction TB
        SA[Schema Analyzer]
        QP[Query Planner]
        SG[SQL Generator]
        SV[Safety Validator]
        QE[Query Executor]
        RI[Result Interpreter]
        
        SA --> QP --> SG --> SV --> QE --> RI
    end
    
    SYSTEM --> RESULT["Results"]
    
    DB[(Database)] -.-> SA
    DB -.-> QE
    LLM[Gemini API] -.-> SG
    
    style USER fill:#e1f5fe
    style RESULT fill:#e1f5fe
    style DB fill:#fff3e0
    style LLM fill:#f3e5f5
```

### 4.2 Safety Architecture

```mermaid
graph TB
    subgraph "Multi-Layer Safety"
        A[Query Input] --> B[Keyword Filter]
        B --> C[Table Access Control]
        C --> D[Resource Limits]
        D --> E[Audit Log]
        E --> F[Safe Execution]
    end
    
    B -.->|Block| X[Rejected]
    C -.->|Block| X
    D -.->|Block| X
    
    style X fill:#ffcdd2
    style F fill:#c8e6c9
```

**Security Controls:**
- Blocks destructive operations (DELETE, DROP, UPDATE)
- Prevents system table access
- Enforces query timeouts and result limits
- Maintains comprehensive audit trail

### 4.3 State Management

```mermaid
graph TD
    subgraph "Pipeline State"
        A[Input] --> B[Schema]
        B --> C[Planning]
        C --> D[Generation]
        D --> E[Validation]
        E --> F[Execution]
        
        A -.-> G[Error Recovery]
        B -.-> G
        C -.-> G
        D -.-> G
        E -.-> G
    end
    
    style G fill:#ffe0b2
```

**Benefits:** Error recovery, performance monitoring, audit logging, result caching

## 5. Implementation

### 5.1 Core Components
**Component Files:**
- **`schema_analyzer.py`** - Identifies relevant tables and relationships
- **`query_planner.py`** - Assesses complexity and creates execution strategy
- **`sql_generator.py`** - Converts natural language to SQL using Gemini API
- **`validator.py`** - Enforces security through keyword filtering and access controls
- **`executor.py`** - Executes SQL with timeout and resource monitoring
- **`interpreter.py`** - Formats results with natural language explanations

### 5.2 Error Handling

```mermaid
graph LR
    A[Error] --> B{Type?}
    B --> C[Schema → Fallback]
    B --> D[Planning → Simplify]
    B --> E[Generation → Help User]
    B --> F[Validation → Block]
    B --> G[Execution → Guide]
    
    C --> R1[Continue]
    D --> R1
    E --> R2[Stop]
    F --> R2
    G --> R2
    
    style A fill:#ffebee
    style R1 fill:#e8f5e9
    style R2 fill:#fff9c4
```

### 5.3 Integration Points

#### Database Abstraction
Supports any SQL-compliant database:
- PostgreSQL (recommended for production)
- MySQL/MariaDB
- Oracle/SQL Server
- Time-series databases (InfluxDB, TimescaleDB)

#### MCP Protocol
Exposes capabilities via Model Context Protocol for agent discovery, standardized request/response format, and integration with network management workflows.

#### Configuration
Pydantic-based configuration for database connections, LLM settings, security policies, and performance tuning.

## 6. Operations

**Safety:** Read-only access, resource limits, comprehensive audit trail

**Performance:** <30 second execution, schema caching, result limiting, connection pooling

**Reliability:** Graceful degradation, detailed error reporting, state preservation, multi-layer validation

## 7. Technology Stack

- **LangGraph** - Workflow orchestration and state management
- **Google Gemini API** - Natural language to SQL conversion
- **Database Agnostic** - Supports any SQL-compliant database
- **Model Context Protocol** - Multi-agent communication
- **Pydantic** - Type-safe configuration and validation